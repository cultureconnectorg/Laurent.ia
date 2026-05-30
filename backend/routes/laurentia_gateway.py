"""
laurentia_gateway.py — Cœur du système.

POST /api/laurentia/query          → SSE stream tokens Claude
POST /api/laurentia/instances/init → crée une instance pour un FREK-ID
GET  /api/laurentia/instances/{frek_id} → renvoie l'état d'une instance
GET  /api/laurentia/memory/{frek_id}    → mémoire long-terme
POST /api/laurentia/feedback        → user_rating sur une interaction
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from services import cvl_brain, cvl_brain_knowledge, kiltikonet_bridge, labelos_bridge
from services.cvl_brain_agents import log_call, log_write
from services.security import tenant_id_for
from services.rate_limit import check_and_consume


router = APIRouter(prefix="/api/laurentia", tags=["laurentia"])


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
    # Init memory
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


# -------------------- Endpoints --------------------

@router.post("/instances/init")
async def init_instance(payload: InstanceInitRequest, request: Request):
    db = _get_db(request)
    # Valide via kiltikonet (mocké)
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
        # Lazy create
        inst = await _ensure_instance(db, frek_id)
    profile = await kiltikonet_bridge.get_frek_profile(frek_id)
    return {
        "instance": inst,
        "first_name": profile.get("first_name", "Hôte"),
        "jcc_balance_kiltikonet": profile.get("wallet", {}).get("jcc_balance", 0),
    }


@router.get("/memory/{frek_id}")
async def get_memory(frek_id: str, request: Request):
    db = _get_db(request)
    mem = await db.laurentia_memory.find_one({"frek_id": frek_id}, {"_id": 0})
    if not mem:
        return {"frek_id": frek_id, "sessions": [], "long_term": {}}
    # Ne pas exposer les sessions chiffrées en clair
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


@router.post("/query")
async def query(payload: QueryRequest, request: Request):
    """
    Point d'entrée principal — SSE streaming.
    Réponse text/event-stream avec événements:
      event: meta   data: {interaction_id, session_id, tenant_id}
      event: token  data: {text}
      event: done   data: {tokens_used, latency_ms}
      event: error  data: {message}
    """
    db = _get_db(request)
    started = time.perf_counter()

    # 1. validation FREK-ID via bridge kiltikonet (mocké)
    validation = await kiltikonet_bridge.validate_frek_id(payload.frek_id)
    if not validation.get("valid"):
        raise HTTPException(403, "FREK-ID non valide")

    # 2. instance (lazy create)
    instance = await _ensure_instance(db, payload.frek_id)

    # 2b. Rate limit per minute selon tier
    rate_per_min = int(instance.get("rate_per_min", 10))
    if not check_and_consume(payload.frek_id, rate_per_min):
        raise HTTPException(429, "Trop de requêtes. Patiente quelques secondes.")

    # 2c. Daily quota
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_used = await db.laurentia_usage.find_one(
        {"frek_id": payload.frek_id, "day": today}, {"_id": 0, "tokens_used": 1}
    )
    day_tokens = int((day_used or {}).get("tokens_used", 0))
    day_limit = int(instance.get("tokens_limit_day", 15_000))
    over_daily = day_tokens >= day_limit and instance.get("tier", "free") == "free"

    # 3. quota
    used = int(instance.get("tokens_used_month", 0))
    limit = int(instance.get("tokens_limit_month", 10000))
    over_quota = used >= limit and instance.get("version") == "free"

    # 4. mémoire & contexte
    profile = await kiltikonet_bridge.get_frek_profile(payload.frek_id)
    cultural_profile = profile.get("cultural_profile", {})

    if payload.context.app == "labelos":
        artist_ctx = await labelos_bridge.get_artist_context(payload.frek_id)
        cultural_profile = {**cultural_profile, "_artist": artist_ctx}

    system_prompt = cvl_brain_knowledge.build_system_prompt(
        app_context=payload.context.app,
        cultural_profile=cultural_profile,
    )

    session_id = payload.context.session_id or f"sess-{tenant_id_for(payload.frek_id)[:12]}-{int(time.time())}"
    interaction_id = f"int-{tenant_id_for(payload.frek_id)[:8]}-{int(time.time()*1000)}"
    t_id = tenant_id_for(payload.frek_id)

    async def event_stream():
        try:
            meta = {
                "interaction_id": interaction_id,
                "session_id": session_id,
                "tenant_id": t_id,
                "first_name": profile.get("first_name", "Hôte"),
                "version": instance.get("version", "free"),
                "tokens_remaining": max(0, limit - used),
                "quota_warning": over_quota,
            }
            yield f"event: meta\ndata: {json.dumps(meta)}\n\n"

            if over_quota:
                # Dégradation gracieuse — JAMAIS de 429 brutal
                degraded = _degraded_response_text()
                for word in degraded.split(" "):
                    yield f"event: token\ndata: {json.dumps({'text': word + ' '})}\n\n"
                yield f"event: done\ndata: {json.dumps({'quota_warning': True, 'tokens_used': 0, 'latency_ms': int((time.perf_counter()-started)*1000)})}\n\n"
                return

            # Charge contextuel: derniers messages selon memory_window du tier
            memory_window = int(instance.get("memory_window", 10))
            mem_doc = await db.laurentia_memory.find_one(
                {"frek_id": payload.frek_id}, {"_id": 0, "sessions": {"$slice": -memory_window}}
            )
            recent_sessions = (mem_doc or {}).get("sessions", []) if mem_doc else []
            enriched_prompt = system_prompt
            if recent_sessions:
                ctx_lines = []
                for s in recent_sessions[-memory_window:]:
                    ctx_lines.append(f"[Échange précédent] Utilisateur: {s.get('input','')[:300]}")
                    ctx_lines.append(f"[Échange précédent] Laurent.ia: {s.get('output','')[:300]}")
                enriched_prompt = system_prompt + "\n\n--- Mémoire récente ---\n" + "\n".join(ctx_lines[-memory_window*2:])
            full_response_parts: list[str] = []

            async for chunk in cvl_brain.chat_stream(
                user_text=payload.input,
                system_message=enriched_prompt,
                session_id=session_id,
            ):
                full_response_parts.append(chunk)
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"

            full_response = "".join(full_response_parts).strip()
            # Estimation tokens (approx: 4 chars / token)
            tokens_in = max(1, len(payload.input) // 4)
            tokens_out = max(1, len(full_response) // 4)

            # Log interaction (anonymisé via tenant_id)
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.laurentia_interactions.insert_one({
                "_id_str": interaction_id,
                "tenant_id": t_id,           # JAMAIS frek_id en clair
                "session_id": session_id,
                "timestamp": now_iso,
                "input_text": payload.input,
                "input_lang": "fr",
                "output_text": full_response,
                "agent_used": "laurentia-core",
                "context_app": payload.context.app,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "user_rating": None,
                "corpus_eligible": False,    # opt-in EXPLICITE uniquement
                "anonymized_at": now_iso,
            })

            # Update instance usage
            await db.laurentia_instances.update_one(
                {"frek_id": payload.frek_id},
                {
                    "$set": {"last_active": now_iso},
                    "$inc": {"tokens_used_month": tokens_in + tokens_out},
                },
            )
            # Update usage monthly bucket
            month = now_iso[:7]
            await db.laurentia_usage.update_one(
                {"frek_id": payload.frek_id, "month": month},
                {
                    "$inc": {"tokens_used": tokens_in + tokens_out, "requests_count": 1},
                    "$set": {"last_request": now_iso},
                },
                upsert=True,
            )
            # Update usage daily bucket
            today_key = now_iso[:10]
            await db.laurentia_usage.update_one(
                {"frek_id": payload.frek_id, "day": today_key},
                {"$inc": {"tokens_used": tokens_in + tokens_out, "requests_count": 1}},
                upsert=True,
            )
            # Append to memory (court terme: derniers échanges)
            await db.laurentia_memory.update_one(
                {"frek_id": payload.frek_id},
                {
                    "$push": {
                        "sessions": {
                            "$each": [{
                                "session_id": session_id,
                                "ts": now_iso,
                                "input": payload.input,
                                "output": full_response,
                            }],
                            "$slice": -50,  # garde 50 derniers échanges
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
