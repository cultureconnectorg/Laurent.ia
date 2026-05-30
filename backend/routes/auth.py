"""
auth.py — Emergent Managed Google Auth integration.

Endpoints (additif, /api/auth/*):
- POST /api/auth/session  body { session_id } — exchange with Emergent, set cookie, derive FREK-ID
- GET  /api/auth/me                          — return current user (cookie or Bearer)
- POST /api/auth/logout                      — clear cookie + delete DB session
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from pydantic import BaseModel

from services import frekcore_bridge

EMERGENT_OAUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_TTL_DAYS = 7
COOKIE_NAME = "session_token"

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------- Schemas ----------------

class SessionExchangeRequest(BaseModel):
    session_id: str


class FrekLoginRequest(BaseModel):
    frek_id: str


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str | None = None
    frek_id: str


# ---------------- Helpers ----------------

def _derive_frek_id(email: str) -> str:
    """FREK-G-{first 10 chars of sha256(email)}. Stable across logins."""
    h = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:10]
    return f"FREK-G-{h}"


async def _get_token(
    session_token_cookie: str | None,
    authorization: str | None,
) -> str | None:
    """Cookie first, then Authorization: Bearer."""
    if session_token_cookie:
        return session_token_cookie
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def _resolve_session(db, session_token: str) -> dict | None:
    """Returns user dict if session is valid, else None."""
    sess = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not sess:
        return None
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    return user


async def get_current_user(request: Request) -> dict | None:
    """Optional auth — returns user dict or None."""
    token = await _get_token(
        request.cookies.get(COOKIE_NAME),
        request.headers.get("authorization"),
    )
    if not token:
        return None
    return await _resolve_session(request.app.state.db, token)


async def require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Non authentifié")
    return user


# ---------------- Endpoints ----------------

@router.post("/session")
async def exchange_session(payload: SessionExchangeRequest, request: Request, response: Response):
    """Exchange Emergent session_id for our own session_token cookie."""
    db = request.app.state.db
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(EMERGENT_OAUTH_URL, headers={"X-Session-ID": payload.session_id})
        if r.status_code != 200:
            raise HTTPException(401, f"Échange auth Emergent échoué ({r.status_code})")
        data = r.json()

    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or email.split("@")[0] or "Hôte").strip()
    picture = data.get("picture")
    session_token = data.get("session_token") or f"sess_{uuid.uuid4().hex}"

    if not email:
        raise HTTPException(400, "Email manquant dans la réponse Emergent")

    frek_id = _derive_frek_id(email)

    # Upsert user
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    now_iso = datetime.now(timezone.utc).isoformat()
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture, "last_login": now_iso, "frek_id": frek_id}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "frek_id": frek_id,
            "created_at": now_iso,
            "last_login": now_iso,
        })

    # Upsert Laurent.ia instance (lazy)
    inst = await db.laurentia_instances.find_one({"frek_id": frek_id}, {"_id": 0})
    if not inst:
        await db.laurentia_instances.insert_one({
            "frek_id": frek_id,
            "tenant_path": f"/users/{frek_id}",
            "version": "free",
            "created_at": now_iso,
            "last_active": now_iso,
            "tokens_used_month": 0,
            "tokens_limit_month": 10000,
            "jcc_balance": 0,
            "stripe_customer_id": None,
            "status": "active",
            "encryption_key_ref": f"ref::{frek_id[-8:]}",
        })
        await db.laurentia_memory.insert_one({
            "frek_id": frek_id,
            "sessions": [],
            "long_term": {"facts": [], "preferences": {}, "projects": [], "people": []},
            "cultural_profile": {},
            "updated_at": now_iso,
        })

    # Store session
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {
            "$set": {
                "user_id": user_id,
                "session_token": session_token,
                "expires_at": expires_at.isoformat(),
                "created_at": now_iso,
            }
        },
        upsert=True,
    )

    # Set httpOnly cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    return {
        "ok": True,
        "user": {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "frek_id": frek_id,
        },
    }


@router.get("/me")
async def me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Non authentifié")
    # Enrichit avec l'état du tier depuis l'instance
    db = request.app.state.db
    inst = await db.laurentia_instances.find_one({"frek_id": user["frek_id"]}, {"_id": 0}) or {}
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "frek_id": user["frek_id"],
        "role": user.get("role"),
        "ecosystem_member": bool(user.get("ecosystem_member", False)),
        "tier": inst.get("tier") or inst.get("version") or "free",
        "tokens_used_month": int(inst.get("tokens_used_month", 0)),
        "tokens_limit_month": int(inst.get("tokens_limit_month", 100_000)),
    }


@router.post("/frek")
async def login_with_frek_id(payload: FrekLoginRequest, request: Request, response: Response):
    """
    Connexion directe via un FREK-ID existant (membre de l'écosystème).
    Valide auprès du service frekcore (mocké en dev, HTTP en prod).
    """
    db = request.app.state.db
    raw = (payload.frek_id or "").strip().upper()
    if not raw or len(raw) < 4:
        raise HTTPException(400, "FREK-ID invalide")

    validation = await frekcore_bridge.validate_frek_id(raw)
    if not validation.get("valid"):
        raise HTTPException(404, "FREK-ID non reconnu")

    profile = await frekcore_bridge.get_profile(raw)
    frek_id = validation.get("frek_id", raw)
    first_name = profile.get("first_name") or raw.split("-")[-1].capitalize()
    role = validation.get("role") or profile.get("role") or "member"
    picture = profile.get("picture")
    email = profile.get("email") or f"{frek_id.lower()}@frekcore.local"

    now_iso = datetime.now(timezone.utc).isoformat()

    # Upsert user (clé = frek_id pour les membres écosystème)
    existing = await db.users.find_one({"frek_id": frek_id}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"frek_id": frek_id},
            {"$set": {"name": first_name, "picture": picture, "role": role, "last_login": now_iso}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": first_name,
            "picture": picture,
            "frek_id": frek_id,
            "role": role,
            "ecosystem_member": True,  # flag pour réactiver la couche écosystème dans l'UI
            "created_at": now_iso,
            "last_login": now_iso,
        })

    # Upsert instance Laurent.ia
    inst = await db.laurentia_instances.find_one({"frek_id": frek_id}, {"_id": 0})
    if not inst:
        await db.laurentia_instances.insert_one({
            "frek_id": frek_id,
            "tenant_path": f"/users/{frek_id}",
            "version": "free",
            "created_at": now_iso,
            "last_active": now_iso,
            "tokens_used_month": 0,
            "tokens_limit_month": 10000,
            "jcc_balance": int((profile.get("wallet") or {}).get("jcc_balance", 0)),
            "status": "active",
            "encryption_key_ref": f"ref::{frek_id[-8:]}",
        })
        await db.laurentia_memory.insert_one({
            "frek_id": frek_id,
            "sessions": [],
            "long_term": {"facts": [], "preferences": {}, "projects": [], "people": []},
            "cultural_profile": profile.get("cultural_profile", {}),
            "updated_at": now_iso,
        })

    # Crée la session
    session_token = f"frek_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso,
        "auth_method": "frek",
    })

    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    return {
        "ok": True,
        "user": {
            "user_id": user_id,
            "email": email,
            "name": first_name,
            "picture": picture,
            "frek_id": frek_id,
            "role": role,
            "ecosystem_member": True,
        },
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    authorization: str | None = Header(default=None),
):
    token = await _get_token(session_token, authorization)
    if token:
        await request.app.state.db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie(COOKIE_NAME, path="/", samesite="none", secure=True)
    return {"ok": True}


class MigrateAnonRequest(BaseModel):
    anon_frek_id: str


@router.post("/migrate-anon")
async def migrate_anon(payload: MigrateAnonRequest, request: Request):
    """
    Migre les interactions anonymes (ANON-XXXX) vers le FREK-ID de l'utilisateur connecté.
    Idempotent. Évite que le visiteur perde ce qu'il a fait avant login.
    """
    from services.security import tenant_id_for
    db = request.app.state.db
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Non authentifié")
    anon = (payload.anon_frek_id or "").strip().upper()
    if not anon.startswith("ANON-"):
        return {"ok": True, "migrated": 0}

    src_tenant = tenant_id_for(anon)
    dst_tenant = tenant_id_for(user["frek_id"])
    if src_tenant == dst_tenant:
        return {"ok": True, "migrated": 0}

    res = await db.laurentia_interactions.update_many(
        {"tenant_id": src_tenant},
        {"$set": {"tenant_id": dst_tenant, "migrated_from_anon_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "migrated": res.modified_count}
