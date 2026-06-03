"""
orchestrator_admin.py — Dashboard Founder & Décisions Circuit Breaker.

Endpoints (role founder|admin requis) :
  GET  /api/admin/orchestrator/status     → état des 20 agents + bus stats
  GET  /api/admin/orchestrator/alerts     → incidents open + closed (laurentia_orchestrator_incidents)
  GET  /api/admin/orchestrator/signals    → derniers signaux guardrail
  POST /api/admin/orchestrator/decisions  → {incident_id, decision: validate|block|modify}

Webhook public (OVH SMS inbound — best-effort, sans auth admin) :
  POST /api/webhook/ovh-sms-reply         → traite "OK <incident_id>" ou "BLOCK <incident_id>"
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from routes.auth import require_user

router = APIRouter(prefix="/api/admin/orchestrator", tags=["orchestrator_admin"])
webhook_router = APIRouter(prefix="/api/webhook", tags=["orchestrator_webhook"])


async def _require_admin(request: Request) -> dict:
    user = await require_user(request)
    role = (user.get("role") or "").lower()
    if role not in ("founder", "admin"):
        raise HTTPException(403, "Accès admin requis")
    return user


def _get_orchestrator(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(503, "Orchestrator non initialisé")
    return orch


@router.get("/status")
async def status(request: Request):
    await _require_admin(request)
    orch = _get_orchestrator(request)
    return orch.stats()


@router.get("/alerts")
async def alerts(request: Request, status_filter: Optional[str] = None, limit: int = 50):
    await _require_admin(request)
    db = request.app.state.db
    query = {"status": status_filter} if status_filter else {}
    cursor = db.laurentia_orchestrator_incidents.find(query, {"_id": 0}).sort("created_at", -1).limit(max(1, min(limit, 200)))
    rows = await cursor.to_list(length=limit)
    return {"incidents": rows, "count": len(rows)}


@router.get("/signals")
async def signals(request: Request, level: Optional[int] = None, limit: int = 100):
    await _require_admin(request)
    db = request.app.state.db
    query = {"level": level} if level is not None else {}
    cursor = db.laurentia_guardrail_logs.find(query, {"_id": 0}).sort("ts", -1).limit(max(1, min(limit, 500)))
    rows = await cursor.to_list(length=limit)
    return {"signals": rows, "count": len(rows)}


class DecisionRequest(BaseModel):
    incident_id: str
    decision: str   # validate | block | modify


@router.post("/decisions")
async def submit_decision(payload: DecisionRequest, request: Request):
    admin = await _require_admin(request)
    if payload.decision not in ("validate", "block", "modify"):
        raise HTTPException(400, "decision invalide")
    orch = _get_orchestrator(request)
    rec = orch.breaker.decide(
        incident_id=payload.incident_id,
        decision=payload.decision,
        decided_by=admin.get("user_id") or admin.get("frek_id") or "admin",
    )
    if not rec:
        raise HTTPException(404, "incident inconnu")
    # Persistance de la décision
    db = request.app.state.db
    await db.laurentia_orchestrator_incidents.update_one(
        {"incident_id": payload.incident_id},
        {"$set": {
            "status": "closed",
            "decision": payload.decision,
            "decided_by": rec["decided_by"],
            "decided_at": rec["decided_at"],
        }},
    )
    return rec


@webhook_router.post("/ovh-sms-reply")
async def ovh_sms_reply(request: Request):
    """
    Webhook public — réception réponses SMS Founder via OVH (best-effort).
    Format attendu (configurable côté OVH) :
      JSON {"from": "+596...", "message": "OK inc-xxxxx"}
      ou form: from, message
    Sécurité minimale : on vérifie que `from` matche FOUNDER_PHONE_NUMBER.
    """
    import os
    founder = os.environ.get("FOUNDER_PHONE_NUMBER", "")
    try:
        body = await request.json()
    except Exception:
        form = await request.form()
        body = dict(form)
    sender = (body.get("from") or "").strip()
    message = (body.get("message") or "").strip()
    if founder and sender and sender != founder:
        return {"ok": False, "reason": "sender_mismatch"}

    parts = message.split()
    if len(parts) < 2:
        return {"ok": False, "reason": "format"}
    keyword, incident_id = parts[0].upper(), parts[1]
    mapping = {"OK": "validate", "VALIDATE": "validate", "BLOCK": "block",
               "MODIFY": "modify", "MODIFIER": "modify"}
    decision = mapping.get(keyword)
    if not decision:
        return {"ok": False, "reason": "keyword"}

    orch = getattr(request.app.state, "orchestrator", None)
    if not orch:
        return {"ok": False, "reason": "orchestrator_not_ready"}
    rec = orch.breaker.decide(incident_id=incident_id, decision=decision, decided_by=f"sms:{sender}")
    if not rec:
        return {"ok": False, "reason": "incident_unknown"}

    db = request.app.state.db
    await db.laurentia_orchestrator_incidents.update_one(
        {"incident_id": incident_id},
        {"$set": {
            "status": "closed",
            "decision": decision,
            "decided_by": f"sms:{sender}",
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "decision_source": "sms_inbound",
        }},
    )
    return {"ok": True, "incident_id": incident_id, "decision": decision}
