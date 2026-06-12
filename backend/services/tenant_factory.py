"""
tenant_factory.py — Pyramide Laurent.ia : 1 tenant = 1 frek_id = 1 allocation d'agents.

Architecture VIRTUELLE (Q1a) :
  - L'Orchestrator garde UN seul set de 20 classes Agent en RAM.
  - Chaque Tenant porte une `allowed_agents: set[str]` selon son tier.
  - Les handlers de l'orchestrateur consultent `tenant_allows(agent_id, tier)`
    pour décider s'ils traitent ou ignorent un signal pour ce tenant.
  - `Tenant.log_activity()` persiste dans laurentia_activity_log avec
    estimation `value_estimator.estimate()`.

Tiers (alignés avec routes/billing.py PACKAGES) :
  - free      → 3 agents essentiels
  - creator   → 10 agents
  - pro       → 20 agents (alias commercial pour infinite)
  - infinite  → 20 agents (full pyramid)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

from motor.motor_asyncio import AsyncIOMotorDatabase

from services import value_estimator

logger = logging.getLogger(__name__)


# ---------- Allocation par tier ----------

ESSENTIALS_3 = {
    "agent-receptionniste",
    "agent-streaming",
    "agent-souverainete",
}

CREATOR_EXTRAS = {
    "agent-securite",
    "agent-guardrail-text",
    "agent-guardrail-code",
    "agent-memoire",
    "agent-rapporteur",
    "agent-latence",
    "agent-data",
}

ALL_20 = ESSENTIALS_3 | CREATOR_EXTRAS | {
    "agent-veille",
    "agent-guardrail-image",
    "agent-sms-alert",
    "agent-redaction",
    "agent-visuel",
    "agent-recherche",
    "agent-traduction",
    "agent-social",
    "agent-arbitre",
    "agent-auto-maintenance",
}

ALLOCATIONS: dict[str, frozenset[str]] = {
    "free":     frozenset(ESSENTIALS_3),
    "creator":  frozenset(ESSENTIALS_3 | CREATOR_EXTRAS),
    "pro":      frozenset(ALL_20),
    "infinite": frozenset(ALL_20),
}


def allocation_for(tier: str | None) -> frozenset[str]:
    return ALLOCATIONS.get((tier or "free").lower(), ALLOCATIONS["free"])


def tenant_allows(tier: str | None, agent_id: str) -> bool:
    """Le tier autorise-t-il cet agent à traiter le signal ?"""
    return agent_id in allocation_for(tier)


# ---------- Tenant ----------

class Tenant:
    """Vue logique d'un utilisateur Laurent.ia (1 frek_id)."""

    def __init__(self, *, frek_id: str, tier: str, db: AsyncIOMotorDatabase) -> None:
        self.frek_id = frek_id
        self.tier = (tier or "free").lower()
        self._db = db

    @property
    def allowed_agents(self) -> frozenset[str]:
        return allocation_for(self.tier)

    async def log_activity(self, action: str, *, time_saved: int | None = None,
                            is_alert: bool = False, metadata: dict | None = None) -> dict:
        """
        Logge une activité métier. `time_saved` override l'estimation par défaut si fourni.
        """
        minutes = time_saved if time_saved is not None else value_estimator.estimate(action)
        doc = {
            "frek_id": self.frek_id,
            "tier": self.tier,
            "action": action.upper(),
            "time_saved_min": int(minutes),
            "is_alert": bool(is_alert),
            "metadata": metadata or {},
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self._db.laurentia_activity_log.insert_one(dict(doc))
        except Exception as e:
            logger.warning("tenant.log_activity persist failed: %s", e)
        return doc

    def snapshot(self) -> dict:
        return {
            "frek_id": self.frek_id,
            "tier": self.tier,
            "allowed_agents": sorted(self.allowed_agents),
            "agent_count": len(self.allowed_agents),
        }


# ---------- TenantFactory ----------

class TenantFactory:
    """Hub résolution tenant par frek_id (auto-création si absent côté instances)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def get_tenant(self, frek_id: str, *, default_tier: str = "free") -> Tenant:
        inst = await self._db.laurentia_instances.find_one(
            {"frek_id": frek_id}, {"_id": 0, "tier": 1, "version": 1}
        )
        if inst:
            tier = (inst.get("tier") or inst.get("version") or default_tier).lower()
        else:
            tier = default_tier
        return Tenant(frek_id=frek_id, tier=tier, db=self._db)

    async def list_active(self, since_iso: str) -> list[dict]:
        """Liste les tenants actifs depuis `since_iso` (utilisé par reports)."""
        pipeline = [
            {"$match": {"ts": {"$gte": since_iso}}},
            {"$group": {
                "_id": "$frek_id",
                "tier": {"$last": "$tier"},
                "actions": {"$sum": 1},
                "time_saved_min": {"$sum": "$time_saved_min"},
                "alerts": {"$sum": {"$cond": ["$is_alert", 1, 0]}},
            }},
        ]
        rows = []
        async for r in self._db.laurentia_activity_log.aggregate(pipeline):
            rows.append({
                "frek_id": r["_id"],
                "tier": r.get("tier") or "free",
                "actions": r.get("actions", 0),
                "time_saved_min": r.get("time_saved_min", 0),
                "alerts": r.get("alerts", 0),
            })
        return rows


def make_tenant_factory(db: AsyncIOMotorDatabase) -> TenantFactory:
    return TenantFactory(db)


def iter_agents_allowed(tier: str | None, agent_ids: Iterable[str]) -> Iterable[str]:
    allowed = allocation_for(tier)
    return (a for a in agent_ids if a in allowed)
