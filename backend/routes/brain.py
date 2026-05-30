"""
brain.py — Endpoints /api/brain/* hérités de kiltikonet.
MVP: implémentation minimale ADDITIVE (compat).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from services import cvl_brain, cvl_brain_knowledge
from services.cvl_brain_agents import AGENT_REGISTRY


router = APIRouter(prefix="/api/brain", tags=["brain"])


class ChatEnrichedRequest(BaseModel):
    message: str
    session_id: str | None = None
    frek_id: str | None = None


@router.get("/health")
async def brain_health():
    return {"ok": True, "service": "cvl-brain", "model": "claude-sonnet-4-5-20250929"}


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
