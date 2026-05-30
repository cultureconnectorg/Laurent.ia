"""
laurentia_sessions.py — Endpoints liés à l'historique des conversations
(pour le menu drawer ☰).

GET    /api/laurentia/sessions/list     — liste des sessions de l'utilisateur courant
GET    /api/laurentia/sessions/{sid}    — messages d'une session
DELETE /api/laurentia/sessions/{sid}    — supprime une session (RGPD)
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from routes.auth import get_current_user
from services.security import tenant_id_for


router = APIRouter(prefix="/api/laurentia/sessions", tags=["laurentia-sessions"])


def _title_from_input(text: str, max_len: int = 56) -> str:
    t = (text or "").strip().split("\n")[0]
    return t if len(t) <= max_len else t[: max_len - 1] + "…"


@router.get("/list")
async def list_sessions(request: Request):
    """Retourne toutes les sessions de l'utilisateur courant (ordre récent → ancien)."""
    db = request.app.state.db
    user = await get_current_user(request)
    if not user:
        # Mode démo : utilise le FREK-ID de la query ?frek_id=
        frek_id = request.query_params.get("frek_id")
        if not frek_id:
            raise HTTPException(401, "Non authentifié")
    else:
        frek_id = user["frek_id"]

    t_id = tenant_id_for(frek_id)
    # Agrège par session_id
    pipeline = [
        {"$match": {"tenant_id": t_id}},
        {"$sort": {"timestamp": 1}},
        {
            "$group": {
                "_id": "$session_id",
                "first_input": {"$first": "$input_text"},
                "first_ts": {"$first": "$timestamp"},
                "last_ts": {"$last": "$timestamp"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"last_ts": -1}},
        {"$limit": 50},
    ]
    rows = await db.laurentia_interactions.aggregate(pipeline).to_list(100)
    return {
        "sessions": [
            {
                "session_id": r["_id"],
                "title": _title_from_input(r["first_input"]),
                "first_ts": r["first_ts"],
                "last_ts": r["last_ts"],
                "message_count": r["count"],
            }
            for r in rows
        ]
    }


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    """Retourne la liste ordonnée des messages d'une session (pour reprendre)."""
    db = request.app.state.db
    user = await get_current_user(request)
    frek_id = user["frek_id"] if user else request.query_params.get("frek_id")
    if not frek_id:
        raise HTTPException(401, "Non authentifié")

    t_id = tenant_id_for(frek_id)
    rows = await db.laurentia_interactions.find(
        {"tenant_id": t_id, "session_id": session_id},
        {"_id": 0, "input_text": 1, "output_text": 1, "timestamp": 1},
    ).sort("timestamp", 1).to_list(500)

    messages = []
    for r in rows:
        messages.append({"role": "user", "text": r["input_text"], "ts": r["timestamp"]})
        messages.append({"role": "assistant", "text": r["output_text"], "ts": r["timestamp"]})
    return {"session_id": session_id, "messages": messages}


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Supprime tous les messages d'une session (RGPD)."""
    db = request.app.state.db
    user = await get_current_user(request)
    frek_id = user["frek_id"] if user else request.query_params.get("frek_id")
    if not frek_id:
        raise HTTPException(401, "Non authentifié")

    t_id = tenant_id_for(frek_id)
    res = await db.laurentia_interactions.delete_many(
        {"tenant_id": t_id, "session_id": session_id}
    )
    # Purge memory thread
    await db.laurentia_memory.update_one(
        {"frek_id": frek_id},
        {"$pull": {"sessions": {"session_id": session_id}}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "deleted": res.deleted_count}
