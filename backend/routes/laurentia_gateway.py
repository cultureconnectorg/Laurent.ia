"""
laurentia_gateway.py — Cœur du système.

POST /api/laurentia/query          → SSE stream tokens Claude
                                      Accepte JSON (`application/json`)
                                      OU multipart/form-data avec fichiers (Creator/Infinite).
POST /api/laurentia/instances/init → crée une instance pour un FREK-ID
GET  /api/laurentia/instances/{frek_id} → renvoie l'état d'une instance
GET  /api/laurentia/memory/{frek_id}    → mémoire long-terme
POST /api/laurentia/feedback        → user_rating sur une interaction
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from services import cvl_brain, cvl_brain_knowledge, kiltikonet_bridge, labelos_bridge
from services.cvl_brain_agents import log_call, log_write
from services.crypto import encrypt_text
from services.file_parser import (
    FileParseError,
    build_context_block,
    parse_many,
    SUPPORTED_EXTENSIONS,
    FILE_MAX_BYTES,
    TOTAL_MAX_BYTES,
)
from services.fingerprint import device_id_from_fingerprint, resolve_limit_key
from services.rate_limit_mongo import (
    LucioleQuotaError,
    check_and_consume as rl_check_and_consume,
)
from services.security import tenant_id_for


router = APIRouter(prefix="/api/laurentia", tags=["laurentia"])
logger = logging.getLogger(__name__)

# Tiers autorisés à uploader des pièces jointes
UPLOAD_ALLOWED_TIERS = {"creator", "infinite"}


# -------------------- Schémas --------------------

class QueryContext(BaseModel):
    app: str = "direct"  # "kiltikonet" | "labelos" | "direct" | "cc2026"
    session_id: str | None = None


class QueryRequest(BaseModel):
    frek_id: str
    input: str
    context: QueryContext = Field(default_factory=QueryContext)
    use_web_search: bool = False


class InstanceInitRequest(BaseModel):
    frek_id: str
    version: str = "free"


class FeedbackRequest(BaseModel):
    interaction_id: str
    rating: int  # 1 ou -1
    corpus_opt_in: bool = False


# -------------------- Helpers --------------------

def _get_db(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.db


async def _ensure_instance(db: AsyncIOMotorDatabase, frek_id: str) -> dict:
    inst = await db.laurentia_instances.find_one({"frek_id": frek_id}, {"_id": 0})
    if inst:
        return inst
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "frek_id": frek_id,
        "tenant_path": f"/users/{frek_id}",
        "version": "free",
        "tier": "free",
        "created_at": now,
        "last_active": now,
        "tokens_used_month": 0,
        "tokens_limit_month": 100_000,
        "tokens_limit_day": 15_000,
        "memory_window": 10,
        "rate_per_min": 10,
        "jcc_balance": 0,
        "stripe_customer_id": None,
        "status": "active",
        "encryption_key_ref": f"ref::{tenant_id_for(frek_id)[:16]}",
    }
    await db.laurentia_instances.insert_one(doc)
    doc.pop("_id", None)  # never return ObjectId — not JSON serializable
    await db.laurentia_memory.update_one(
        {"frek_id": frek_id},
        {
            "$setOnInsert": {
                "frek_id": frek_id,
                "sessions": [],
                "long_term": {"facts": [], "preferences": {}, "projects": [], "people": []},
                "cultural_profile": {},
                "updated_at": now,
            }
        },
        upsert=True,
    )
    return doc


def _degraded_response_text() -> str:
    return (
        "Tu approches de ta limite mensuelle. "
        "Activer Pro permet de continuer sans interruption — €15/mois ou 150 JCC."
    )


def _resolve_tier(instance: dict) -> str:
    """Tier effectif (tier prioritaire, fallback sur version)."""
    return (instance.get("tier") or instance.get("version") or "free").lower()


# -------------------- Endpoints --------------------

@router.post("/instances/init")
async def init_instance(payload: InstanceInitRequest, request: Request):
    db = _get_db(request)
    validation = await kiltikonet_bridge.validate_frek_id(payload.frek_id)
    if not validation.get("valid"):
        raise HTTPException(403, "FREK-ID invalide")

    inst = await _ensure_instance(db, payload.frek_id)
    await log_call(db, "smart-engine-cvln", "instance_init", {"frek_id_hash": tenant_id_for(payload.frek_id)})
    return {"ok": True, "instance": inst}


@router.get("/instances/{frek_id}")
async def get_instance(frek_id: str, request: Request):
    db = _get_db(request)
    inst = await db.laurentia_instances.find_one({"frek_id": frek_id}, {"_id": 0})
    if not inst:
        inst = await _ensure_instance(db, frek_id)
    profile = await kiltikonet_bridge.get_frek_profile(frek_id)
    return {
        "instance": inst,
        "first_name": profile.get("first_name", "Hôte"),
        "jcc_balance_kiltikonet": profile.get("wallet", {}).get("jcc_balance", 0),
    }


@router.get("/resolve")
async def resolve_by_device(request: Request):
    """
    Persistance Fantôme — Résout le frek_id le plus récent associé au device_id
    courant (via header X-Device-Fingerprint).

    Permet au frontend, dès le premier paint, de recharger l'instance et
    l'historique de l'utilisateur anonyme sans cookie ni mot de passe.

    Réponse :
      { "device_id": "<hex64>" | null,
        "frek_id":   "<id>"     | null,
        "instance":  {...}      | null,
        "session_count": <int>,
        "last_session_id": "<id>" | null }
    """
    db = _get_db(request)
    device_fp = request.headers.get("x-device-fingerprint") or request.headers.get("X-Device-Fingerprint")
    device_id = device_id_from_fingerprint(device_fp)
    if not device_id:
        return {"device_id": None, "frek_id": None, "instance": None, "session_count": 0, "last_session_id": None}

    inst = await db.laurentia_instances.find_one(
        {"device_ids": device_id},
        {"_id": 0},
        sort=[("last_active", -1)],
    )
    if not inst:
        return {"device_id": device_id, "frek_id": None, "instance": None, "session_count": 0, "last_session_id": None}

    mem = await db.laurentia_memory.find_one(
        {"frek_id": inst["frek_id"]},
        {"_id": 0, "sessions": {"$slice": -1}},
    )
    last_session_id = None
    session_count = 0
    if mem and mem.get("sessions"):
        last_session_id = mem["sessions"][-1].get("session_id")
        # count complet (sans projection) — petit doc, ok
        full = await db.laurentia_memory.find_one({"frek_id": inst["frek_id"]}, {"_id": 0, "sessions": 1})
        session_count = len((full or {}).get("sessions", []))

    return {
        "device_id": device_id,
        "frek_id": inst["frek_id"],
        "instance": inst,
        "session_count": session_count,
        "last_session_id": last_session_id,
    }


@router.get("/memory/{frek_id}")
async def get_memory(frek_id: str, request: Request):
    db = _get_db(request)
    mem = await db.laurentia_memory.find_one({"frek_id": frek_id}, {"_id": 0})
    if not mem:
        return {"frek_id": frek_id, "sessions": [], "long_term": {}}
    safe = {
        "frek_id": mem["frek_id"],
        "session_count": len(mem.get("sessions", [])),
        "long_term": mem.get("long_term", {}),
        "updated_at": mem.get("updated_at"),
    }
    return safe


@router.post("/feedback")
async def feedback(payload: FeedbackRequest, request: Request):
    db = _get_db(request)
    await db.laurentia_interactions.update_one(
        {"_id_str": payload.interaction_id},
        {
            "$set": {
                "user_rating": 1 if payload.rating > 0 else -1,
                "corpus_eligible": payload.corpus_opt_in,
            }
        },
    )
    return {"ok": True}


@router.get("/upload-limits")
async def upload_limits():
    """Limites publiques affichées dans la UI (Composer)."""
    return {
        "file_max_bytes": FILE_MAX_BYTES,
        "total_max_bytes": TOTAL_MAX_BYTES,
        "extensions": sorted(SUPPORTED_EXTENSIONS),
        "allowed_tiers": sorted(UPLOAD_ALLOWED_TIERS),
    }


async def _run_query(
    *,
    db: AsyncIOMotorDatabase,
    frek_id: str,
    user_input: str,
    context_app: str,
    session_id_in: str | None,
    files_context: str = "",
    files_summary: list[dict] | None = None,
    device_fp: str | None = None,
    orchestrator=None,
):
    """
    Cœur d'exécution — partagé entre route JSON et route multipart.
    Renvoie une StreamingResponse SSE.
    """
    started = time.perf_counter()

    # 1. validation FREK-ID via bridge kiltikonet (mocké)
    validation = await kiltikonet_bridge.validate_frek_id(frek_id)
    if not validation.get("valid"):
        raise HTTPException(403, "FREK-ID non valide")

    # 2. instance (lazy create)
    instance = await _ensure_instance(db, frek_id)
    tier = _resolve_tier(instance)

    # 2b. Rate limit Mongo sliding-window (par device_id, fallback frek_id hash)
    device_id = device_id_from_fingerprint(device_fp)
    limit_key = resolve_limit_key(frek_id, device_id)
    decision = await rl_check_and_consume(db, key=limit_key, tier=tier)
    if not decision.allowed:
        # Message noble selon raison
        err = LucioleQuotaError(decision.reason, decision.retry_in_seconds)
        raise HTTPException(
            status_code=429,
            detail=err.noble_message(),
            headers={"Retry-After": str(decision.retry_in_seconds)},
        )

    # 2b-bis. Persistance Fantôme : on lie le device_id à l'instance.
    # Permet à un user anonyme de retrouver son historique sur la même machine
    # même après vidage du localStorage, ET au PDF export de résoudre le tier.
    if device_id:
        await db.laurentia_instances.update_one(
            {"frek_id": frek_id},
            {"$addToSet": {"device_ids": device_id}},
        )

    # 2c. Daily quota
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_used = await db.laurentia_usage.find_one(
        {"frek_id": frek_id, "day": today}, {"_id": 0, "tokens_used": 1}
    )
    day_tokens = int((day_used or {}).get("tokens_used", 0))
    day_limit = int(instance.get("tokens_limit_day", 15_000))
    over_daily = day_tokens >= day_limit and tier == "free"

    # 3. quota mensuel
    used = int(instance.get("tokens_used_month", 0))
    limit = int(instance.get("tokens_limit_month", 10000))
    over_quota = (used >= limit and tier == "free") or over_daily

    # 4. mémoire & contexte
    profile = await kiltikonet_bridge.get_frek_profile(frek_id)
    cultural_profile = profile.get("cultural_profile", {})
    if context_app == "labelos":
        artist_ctx = await labelos_bridge.get_artist_context(frek_id)
        cultural_profile = {**cultural_profile, "_artist": artist_ctx}

    system_prompt = cvl_brain_knowledge.build_system_prompt(
        app_context=context_app,
        cultural_profile=cultural_profile,
    )

    session_id = session_id_in or f"sess-{tenant_id_for(frek_id)[:12]}-{int(time.time())}"
    interaction_id = f"int-{tenant_id_for(frek_id)[:8]}-{int(time.time()*1000)}"
    t_id = tenant_id_for(frek_id)

    # Compose le prompt final (input utilisateur + bloc fichiers)
    composed_input = user_input
    if files_context:
        composed_input = f"{user_input}\n\n{files_context}"

    async def event_stream():
        # Chantier 9 — hook orchestrator (NON-BLOQUANT, fire-and-forget)
        orch = orchestrator
        if orch is not None:
            try:
                orch.dispatch_intake(
                    session_id=session_id,
                    frek_id_hash=t_id,
                    user_input=composed_input,
                    tier=tier,
                )
            except Exception:
                pass
        try:
            meta = {
                "interaction_id": interaction_id,
                "session_id": session_id,
                "tenant_id": t_id,
                "first_name": profile.get("first_name", "Hôte"),
                "version": instance.get("version", "free"),
                "tier": _resolve_tier(instance),
                "tokens_remaining": max(0, limit - used),
                "quota_warning": over_quota,
                "files": files_summary or [],
            }
            yield f"event: meta\ndata: {json.dumps(meta)}\n\n"

            if over_quota:
                degraded = _degraded_response_text()
                for word in degraded.split(" "):
                    yield f"event: token\ndata: {json.dumps({'text': word + ' '})}\n\n"
                yield (
                    "event: done\n"
                    f"data: {json.dumps({'quota_warning': True, 'tokens_used': 0, 'latency_ms': int((time.perf_counter()-started)*1000)})}\n\n"
                )
                return

            # Charge contextuel : derniers messages selon memory_window du tier
            memory_window = int(instance.get("memory_window", 10))
            mem_doc = await db.laurentia_memory.find_one(
                {"frek_id": frek_id}, {"_id": 0, "sessions": {"$slice": -memory_window}}
            )
            recent_sessions = (mem_doc or {}).get("sessions", []) if mem_doc else []
            enriched_prompt = system_prompt
            if recent_sessions:
                from services.crypto import decrypt_text  # local import to avoid cycles
                ctx_lines = []
                for s in recent_sessions[-memory_window:]:
                    u_in = decrypt_text(s.get("input"))
                    u_out = decrypt_text(s.get("output"))
                    if u_in:
                        ctx_lines.append(f"[Échange précédent] Utilisateur: {u_in[:300]}")
                    if u_out:
                        ctx_lines.append(f"[Échange précédent] Laurent.ia: {u_out[:300]}")
                if ctx_lines:
                    enriched_prompt = system_prompt + "\n\n--- Mémoire récente ---\n" + "\n".join(ctx_lines[-memory_window*2:])

            full_response_parts: list[str] = []

            async for chunk in cvl_brain.chat_stream(
                user_text=composed_input,
                system_message=enriched_prompt,
                session_id=session_id,
            ):
                full_response_parts.append(chunk)
                # Chantier 9 — shadow dispatch chunk (NON-BLOQUANT)
                if orch is not None:
                    try:
                        orch.dispatch_stream_chunk(session_id=session_id, chunk=chunk, tier=tier)
                    except Exception:
                        pass
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"

            full_response = "".join(full_response_parts).strip()
            tokens_in = max(1, len(composed_input) // 4)
            tokens_out = max(1, len(full_response) // 4)
            # Chantier 9 — shadow dispatch fin de stream
            if orch is not None:
                try:
                    orch.dispatch_stream_done(
                        session_id=session_id,
                        full_text=full_response,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                        tokens=tokens_in + tokens_out,
                        tier=tier,
                    )
                except Exception:
                    pass
            # Chantier 10 — log activity métier (ROI souverain)
            try:
                from services.tenant_factory import Tenant
                tenant = Tenant(frek_id=frek_id, tier=tier, db=db)
                await tenant.log_activity("QUERY_PROCESSED",
                                          metadata={"session_id": session_id,
                                                    "tokens": tokens_in + tokens_out})
            except Exception:
                pass

            # Log interaction (anonymisé via tenant_id, contenu chiffré AES-256-GCM)
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.laurentia_interactions.insert_one({
                "_id_str": interaction_id,
                "tenant_id": t_id,
                "session_id": session_id,
                "timestamp": now_iso,
                "input_text": encrypt_text(composed_input),
                "input_lang": "fr",
                "output_text": encrypt_text(full_response),
                "agent_used": "laurentia-core",
                "context_app": context_app,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "user_rating": None,
                "corpus_eligible": False,
                "anonymized_at": now_iso,
                "files_attached": files_summary or [],
            })

            # Update instance usage
            await db.laurentia_instances.update_one(
                {"frek_id": frek_id},
                {
                    "$set": {"last_active": now_iso},
                    "$inc": {"tokens_used_month": tokens_in + tokens_out},
                },
            )
            # Update usage monthly bucket
            month = now_iso[:7]
            await db.laurentia_usage.update_one(
                {"frek_id": frek_id, "month": month},
                {
                    "$inc": {"tokens_used": tokens_in + tokens_out, "requests_count": 1},
                    "$set": {"last_request": now_iso},
                },
                upsert=True,
            )
            # Update usage daily bucket
            today_key = now_iso[:10]
            await db.laurentia_usage.update_one(
                {"frek_id": frek_id, "day": today_key},
                {"$inc": {"tokens_used": tokens_in + tokens_out, "requests_count": 1}},
                upsert=True,
            )
            # Append to memory — chiffré
            await db.laurentia_memory.update_one(
                {"frek_id": frek_id},
                {
                    "$push": {
                        "sessions": {
                            "$each": [{
                                "session_id": session_id,
                                "ts": now_iso,
                                "input": encrypt_text(composed_input),
                                "output": encrypt_text(full_response),
                            }],
                            "$slice": -50,
                        }
                    },
                    "$set": {"updated_at": now_iso},
                },
                upsert=True,
            )

            await log_call(db, "analytics-tracker", "query_completed", {
                "tenant_id": t_id, "tokens": tokens_in + tokens_out,
            })

            done = {
                "interaction_id": interaction_id,
                "tokens_used": tokens_in + tokens_out,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
            yield f"event: done\ndata: {json.dumps(done)}\n\n"

        except Exception as e:
            logger.exception("query_failed tenant=%s", t_id)
            await log_write(db, "smart-engine-cvln", "error", "query_failed", {"err": str(e), "tenant_id": t_id})
            err_payload = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/query")
async def query(request: Request):
    """
    Point d'entrée principal — SSE streaming.

    Deux modes d'entrée :
      - JSON (`application/json`) — texte uniquement.
      - multipart/form-data — `payload` (JSON string QueryRequest) + 1..N `files`.
        L'upload est réservé aux tiers Creator / Infinite.
    """
    db = _get_db(request)
    content_type = (request.headers.get("content-type") or "").lower()
    device_fp = request.headers.get("x-device-fingerprint") or request.headers.get("X-Device-Fingerprint")

    if content_type.startswith("multipart/"):
        form = await request.form()
        raw_payload = form.get("payload")
        if not raw_payload:
            raise HTTPException(422, "Champ 'payload' (JSON) manquant dans le multipart.")
        try:
            payload_dict = json.loads(raw_payload)
            payload = QueryRequest(**payload_dict)
        except Exception as e:
            raise HTTPException(422, f"Payload JSON invalide : {e}")

        # Récupère tous les UploadFile (clés "files" ou "files[]")
        # Duck-typing pour résister aux divergences d'imports après hot reload.
        upload_files: list = []
        for key in ("files", "files[]"):
            for v in form.getlist(key):
                if hasattr(v, "read") and hasattr(v, "filename"):
                    upload_files.append(v)

        # Gate tier : seuls Creator / Infinite peuvent uploader
        if upload_files:
            instance = await _ensure_instance(db, payload.frek_id)
            tier = _resolve_tier(instance)
            if tier not in UPLOAD_ALLOWED_TIERS:
                raise HTTPException(
                    403,
                    "Upload de fichiers réservé aux plans Creator (€15/mois) et Infinite (€39/mois).",
                )

        # Lit les bytes (limite stricte par fichier déjà gérée plus bas)
        files_in: list[tuple[str, str | None, bytes]] = []
        for uf in upload_files:
            data = await uf.read()
            files_in.append((uf.filename or "document", uf.content_type, data))

        try:
            parsed = parse_many(files_in)
        except FileParseError as e:
            raise HTTPException(413 if "trop" in str(e).lower() else 415, str(e))

        files_context = build_context_block(parsed)
        files_summary = [pf.as_summary() for pf in parsed]

        return await _run_query(
            db=db,
            frek_id=payload.frek_id,
            user_input=payload.input,
            context_app=payload.context.app,
            session_id_in=payload.context.session_id,
            files_context=files_context,
            files_summary=files_summary,
            device_fp=device_fp,
            orchestrator=getattr(request.app.state, "orchestrator", None),
        )

    # JSON path (legacy)
    try:
        body = await request.json()
        payload = QueryRequest(**body)
    except Exception as e:
        raise HTTPException(422, f"Body JSON invalide : {e}")
    return await _run_query(
        db=db,
        frek_id=payload.frek_id,
        user_input=payload.input,
        context_app=payload.context.app,
        session_id_in=payload.context.session_id,
        device_fp=device_fp,
        orchestrator=getattr(request.app.state, "orchestrator", None),
    )
