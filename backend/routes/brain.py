"""
brain.py — Endpoints /api/brain/* hérités de kiltikonet.
MVP: implémentation minimale ADDITIVE (compat).
"""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from services import cvl_brain, cvl_brain_knowledge
from services.cvl_brain_agents import AGENT_REGISTRY

import hmac
import os


router = APIRouter(prefix="/api/brain", tags=["brain"])


class ChatEnrichedRequest(BaseModel):
    message: str
    session_id: str | None = None
    frek_id: str | None = None


class BriefingRequest(BaseModel):
    topic: str | None = None
    request: str | None = None
    context: dict = Field(default_factory=dict)
    trace_id: str | None = None
    issuer: str | None = None


@router.get("/health")
async def brain_health():
    mode = os.environ.get("LAURENTIA_INFERENCE_MODE", "embedded").strip().lower()
    local_status = None
    if mode == "embedded":
        from services.local_inference import model_status
        local_status = model_status()
    configured = (
        mode == "embedded"
        or (
            mode == "controlled-endpoint"
            and bool(os.environ.get("LAURENTIA_LLM_BASE_URL", "").strip())
            and bool(os.environ.get("LAURENTIA_LLM_MODEL", "").strip())
        )
    )
    return {
        "ok": True,
        "service": "cvl-brain",
        "model": local_status["model"] if local_status else os.environ.get("LAURENTIA_LLM_MODEL", "local-model"),
        "inference_mode": mode,
        "inference_configured": configured,
        "inference_ready": bool(local_status and local_status["loaded"]) if local_status else configured,
        "agent_factory_enabled": os.environ.get("LAURENTIA_AGENT_FACTORY_ENABLED", "").lower() == "true",
    }


@router.get("/agents")
async def list_agents(request: Request):
    db = request.app.state.db
    statuses = await db.cvl_brain_agent_status.find({}, {"_id": 0}).to_list(50)
    return {"agents": statuses or AGENT_REGISTRY}


@router.post("/chat-enriched")
async def chat_enriched(payload: ChatEnrichedRequest):
    """Non-streaming legacy endpoint."""
    system = cvl_brain_knowledge.build_system_prompt()
    text = await cvl_brain.chat_enriched(payload.message, system, payload.session_id)
    return {"response": text}


@router.post("/briefing")
async def briefing(payload: BriefingRequest, request: Request):
    """Stable JSON facade for Meta CVLN and other trusted CVLN consumers."""
    raw_key = request.headers.get("X-API-Key", "")
    service_key = os.environ.get("LAURENTIA_CVLN_SERVICE_API_KEY", "").strip()
    if not service_key or not raw_key or not hmac.compare_digest(raw_key, service_key):
        raise HTTPException(403, "X-API-Key inter-service invalide")
    request_text = (payload.request or payload.topic or "").strip()
    prompt = request_text or "Fournis un briefing synthétique à partir du contexte transmis."
    if payload.context:
        prompt += "\n\n[CONTEXTE]\n" + str(payload.context)

    factory_recommendation = None
    if os.environ.get("LAURENTIA_AGENT_FACTORY_ENABLED", "").lower() == "true":
        # Only the task text and an explicit entity label cross the service boundary.
        # The private context stays in Laurent.ia and is never forwarded to the Factory.
        from services.agent_factory_bridge import recommend_agents

        entity = payload.context.get("entity") if isinstance(payload.context, dict) else None
        try:
            factory_recommendation = await recommend_agents(
                request_text or prompt,
                entity=entity if isinstance(entity, str) else None,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "agent_factory_unavailable",
                    "message": "Agent Factory activée mais recommandation indisponible.",
                    "trace_id": payload.trace_id,
                },
            ) from exc

        prompt += (
            "\n\n[RECOMMANDATIONS CVLN AGENT FACTORY — NON EXÉCUTÉES]"
            "\nAgents recommandés: " + str(factory_recommendation["recommended_agents"])
            + "\nBrouillon de mission: " + str(factory_recommendation["draft_mission"])
            + "\nConsigne: utilise ces éléments comme recommandations, vérifie leur pertinence, "
              "signale les manques et ne prétends pas que ces agents ont exécuté une tâche."
        )

    system = cvl_brain_knowledge.build_system_prompt()
    text = await cvl_brain.chat_enriched(prompt, system, payload.trace_id)
    response = {
        "contract": "laurentia.briefing",
        "version": "1.0",
        "trace_id": payload.trace_id,
        "issuer": payload.issuer,
        "response": text,
    }
    if factory_recommendation is not None:
        response["agent_factory"] = factory_recommendation
    return response
