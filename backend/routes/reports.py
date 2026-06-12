"""
reports.py — Rapports daily/weekly (user self-service + founder admin).

Authentification souple :
  - JWT cookie (frontend web) via routes.auth.require_user
  - OU X-API-Key header (SDK programmatique) via services.api_keys.validate_key

Endpoints :
  GET    /api/me/report/daily          → mon rapport 24h
  GET    /api/me/report/weekly         → mon rapport 7j
  GET    /api/me/keys                  → liste mes clés API
  POST   /api/me/keys                  → crée une nouvelle clé (raw_key visible 1 seule fois)
  DELETE /api/me/keys/{key_id}         → révoque

  GET    /api/admin/reports/daily      → snapshot global 24h (founder)
  GET    /api/admin/reports/weekly     → snapshot global 7j (founder)
  POST   /api/admin/reports/snapshot   → déclenche manuellement le cron daily
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from routes.auth import get_current_user
from services import api_keys
from services.tenant_factory import make_tenant_factory
from jobs import reports as reports_job

router = APIRouter(prefix="/api", tags=["reports"])


async def _resolve_caller(request: Request) -> dict:
    """Auth souple : JWT cookie OU X-API-Key header. Retourne {frek_id, tier, role, source}."""
    # 1. JWT en priorité (frontend web)
    user = await get_current_user(request)
    if user:
        return {
            "frek_id": user.get("frek_id"),
            "tier": (user.get("tier") or user.get("version") or "free").lower(),
            "role": (user.get("role") or "").lower(),
            "source": "jwt",
        }
    # 2. Fallback X-API-Key
    raw = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if raw:
        db = request.app.state.db
        key_doc = await api_keys.validate_key(db, raw)
        if key_doc:
            inst = await db.laurentia_instances.find_one(
                {"frek_id": key_doc["frek_id"]}, {"_id": 0, "role": 1}
            )
            return {
                "frek_id": key_doc["frek_id"],
                "tier": key_doc.get("tier", "free"),
                "role": (inst or {}).get("role", "").lower(),
                "source": "api_key",
                "key_id": key_doc["key_id"],
            }
    raise HTTPException(401, "Authentification requise (JWT cookie ou X-API-Key)")


async def _require_admin(request: Request) -> dict:
    caller = await _resolve_caller(request)
    if caller["role"] not in ("founder", "admin"):
        raise HTTPException(403, "Accès admin requis")
    return caller


# ---------- User self-service ----------

@router.get("/me/report/daily")
async def my_daily_report(request: Request):
    caller = await _resolve_caller(request)
    db = request.app.state.db
    return await reports_job.compute_user_daily(db, caller["frek_id"], hours=24)


@router.get("/me/report/weekly")
async def my_weekly_report(request: Request):
    caller = await _resolve_caller(request)
    db = request.app.state.db
    return await reports_job.compute_user_daily(db, caller["frek_id"], hours=24 * 7)


@router.get("/me/tenant")
async def my_tenant_info(request: Request):
    """Renvoie l'allocation d'agents du tenant courant (debug + transparence)."""
    caller = await _resolve_caller(request)
    db = request.app.state.db
    factory = make_tenant_factory(db)
    tenant = await factory.get_tenant(caller["frek_id"])
    return tenant.snapshot()


# ---------- API Keys self-service ----------

@router.get("/me/keys")
async def list_my_keys(request: Request):
    caller = await _resolve_caller(request)
    if caller["source"] == "api_key":
        raise HTTPException(403, "Liste des clés accessible uniquement via session JWT")
    db = request.app.state.db
    keys = await api_keys.list_keys(db, frek_id=caller["frek_id"])
    return {"keys": keys, "count": len(keys)}


class CreateKeyRequest(BaseModel):
    label: str = "default"


@router.post("/me/keys")
async def create_my_key(payload: CreateKeyRequest, request: Request):
    caller = await _resolve_caller(request)
    if caller["source"] == "api_key":
        raise HTTPException(403, "Création de clé uniquement via session JWT")
    db = request.app.state.db
    created = await api_keys.create_key(
        db, frek_id=caller["frek_id"], tier=caller["tier"], label=payload.label,
    )
    # raw_key renvoyé UNE seule fois — l'utilisateur doit le stocker maintenant
    return created


@router.delete("/me/keys/{key_id}")
async def revoke_my_key(key_id: str, request: Request):
    caller = await _resolve_caller(request)
    if caller["source"] == "api_key":
        raise HTTPException(403, "Révocation uniquement via session JWT")
    db = request.app.state.db
    ok = await api_keys.revoke_key(db, frek_id=caller["frek_id"], key_id=key_id)
    if not ok:
        raise HTTPException(404, "Clé inconnue ou déjà révoquée")
    return {"revoked": True, "key_id": key_id}


# ---------- Founder Admin ----------

@router.get("/admin/reports/daily")
async def admin_daily(request: Request):
    await _require_admin(request)
    db = request.app.state.db
    return await reports_job.compute_founder_daily(db, hours=24)


@router.get("/admin/reports/weekly")
async def admin_weekly(request: Request):
    await _require_admin(request)
    db = request.app.state.db
    return await reports_job.compute_founder_weekly(db)


@router.post("/admin/reports/snapshot")
async def admin_snapshot(request: Request):
    await _require_admin(request)
    db = request.app.state.db
    return await reports_job.snapshot_daily(db)
