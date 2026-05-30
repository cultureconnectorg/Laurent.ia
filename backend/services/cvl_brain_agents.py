"""
cvl_brain_agents.py — Registre des 10 agents (hérité kiltikonet).
Bug fix #2: log_write() activé, écrit dans la collection `agent_logs`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

AGENT_REGISTRY = [
    {"agent_id": "smart-engine-cvln",  "role": "Alertes intelligentes (scan continu)"},
    {"agent_id": "alert-engine",       "role": "Notifications alertes critiques"},
    {"agent_id": "badge-generator",    "role": "Génération badges NFC + PDF"},
    {"agent_id": "analytics-tracker",  "role": "Tracking visiteurs"},
    {"agent_id": "stripe-webhook",     "role": "Réception webhooks Stripe"},
    {"agent_id": "email-service",      "role": "Envoi emails (Brevo + SES)"},
    {"agent_id": "social-feed-engine", "role": "Génération feed Pro"},
    {"agent_id": "hcaptcha-guard",     "role": "Validation captcha"},
    {"agent_id": "cms-sanitizer",      "role": "Nettoyage HTML anti-XSS"},
    {"agent_id": "batch-processor",    "role": "Jobs batch (exports, syncs)"},
]


async def ensure_registry(db: AsyncIOMotorDatabase) -> None:
    """Initialise la collection cvl_brain_agent_status si vide (idempotent)."""
    coll = db.cvl_brain_agent_status
    for agent in AGENT_REGISTRY:
        await coll.update_one(
            {"agent_id": agent["agent_id"]},
            {
                "$setOnInsert": {
                    "agent_id": agent["agent_id"],
                    "role": agent["role"],
                    "connected": True,
                    "last_call": None,
                    "last_detail": None,
                    "total_calls": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )


async def update_status(db: AsyncIOMotorDatabase, agent_id: str, detail: str | None = None) -> None:
    await db.cvl_brain_agent_status.update_one(
        {"agent_id": agent_id},
        {
            "$set": {
                "connected": True,
                "last_call": datetime.now(timezone.utc).isoformat(),
                "last_detail": detail,
            },
            "$inc": {"total_calls": 1},
        },
        upsert=True,
    )


async def log_write(
    db: AsyncIOMotorDatabase,
    agent_id: str,
    level: str,
    message: str,
    detail: Any | None = None,
) -> None:
    """Bug fix #2: écrit dans agent_logs (était manquant dans le code hérité)."""
    await db.agent_logs.insert_one(
        {
            "agent_id": agent_id,
            "level": level,
            "message": message,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def log_call(
    db: AsyncIOMotorDatabase, agent_id: str, message: str, detail: Any | None = None
) -> None:
    """Combo: update_status + log_write."""
    await update_status(db, agent_id, detail=message)
    await log_write(db, agent_id, "info", message, detail)
