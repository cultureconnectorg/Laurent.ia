"""
omega.py — Chat enrichi SSE (bug fix #3).
Alias technique pour compat héritée: /api/omega/chat-enriched (stream).
"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import cvl_brain, cvl_brain_knowledge


router = APIRouter(prefix="/api/omega", tags=["omega"])


class OmegaRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/chat-enriched")
async def chat_enriched_stream(payload: OmegaRequest, request: Request):
    system = cvl_brain_knowledge.build_system_prompt()
    started = time.perf_counter()

    async def stream():
        yield f"event: meta\ndata: {json.dumps({'session_id': payload.session_id or 'omega'})}\n\n"
        async for chunk in cvl_brain.chat_stream(payload.message, system, payload.session_id):
            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
        yield f"event: done\ndata: {json.dumps({'latency_ms': int((time.perf_counter()-started)*1000)})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
