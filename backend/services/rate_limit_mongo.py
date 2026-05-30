"""
rate_limit_mongo.py — Sliding window distribuée sur MongoDB (TTL index).

Stratégie :
  - Une collection `laurentia_rate_limits` recevant un document par requête :
        { key: <device_id|fallback_hash>, ts: <datetime UTC>, tier: <str> }
  - Index TTL `expires_at` (champ datetime) configuré à `expireAfterSeconds=0` →
    MongoDB purge automatiquement les documents périmés. La fenêtre est obtenue
    par un `count_documents({key, ts >= now - window})`.
  - Index composé `(key, ts)` pour les counts rapides.

Pourquoi pas Redis ? Décision arch v0.9 : on évite la dette de maintenance
d'une nouvelle brique. Performance largement suffisante à notre échelle
(quelques centaines de requêtes/min globales).

Quotas (par tier, par window) :
  - free      : 10 / 60s, 60 / 3600s
  - creator   : 60 / 60s, 1200 / 3600s
  - infinite  : 240 / 60s, illimité horaire

Le message noble est exposé via :  exceptions.LucioleQuotaError
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

COLLECTION = "laurentia_rate_limits"

# Fenêtres et quotas par tier
LIMITS: dict[str, dict[str, int]] = {
    "free":     {"per_min": 10,  "per_hour": 60},
    "creator":  {"per_min": 60,  "per_hour": 1200},
    "infinite": {"per_min": 240, "per_hour": 0},  # 0 = illimité horaire
}

# Le document est supprimé par TTL au-delà de la plus grande fenêtre (1h).
DOC_TTL_SECONDS = 3700  # 1h + marge


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str | None       # "per_min" | "per_hour" | None
    retry_in_seconds: int    # approximation pour le frontend
    used_min: int
    used_hour: int


class LucioleQuotaError(Exception):
    """Levée pour rendre le message noble en HTTP 429."""
    def __init__(self, reason: str, retry_in_seconds: int):
        self.reason = reason
        self.retry_in_seconds = retry_in_seconds
        super().__init__(self.noble_message())

    def noble_message(self) -> str:
        if self.reason == "per_hour":
            return (
                "Votre Énergie Luciole est temporairement épuisée pour cette heure. "
                "Passez au tier Creator 🪙 pour libérer votre puissance."
            )
        return (
            "Souffle — quelques secondes encore. "
            "Votre flux Luciole se régénère. "
            "Creator 🪙 lève cette friction instantanément."
        )


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    À appeler au startup. Idempotent.
    """
    coll = db[COLLECTION]
    # TTL : MongoDB supprime les docs où `expires_at` <= now.
    await coll.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at")
    await coll.create_index([("key", 1), ("ts", -1)], name="key_ts")


async def check_and_consume(
    db: AsyncIOMotorDatabase,
    *,
    key: str,
    tier: str,
) -> RateLimitDecision:
    """
    1) Compte les hits dans la fenêtre 60s ET 3600s.
    2) Si limite atteinte → retourne allowed=False (et NE consomme PAS).
    3) Sinon → insert un doc + return allowed=True.
    """
    quotas = LIMITS.get(tier) or LIMITS["free"]
    coll = db[COLLECTION]
    now = datetime.now(timezone.utc)
    window_min = now - timedelta(seconds=60)
    window_hour = now - timedelta(seconds=3600)

    # Comptes concurrents — count_documents est cheap avec l'index (key, ts).
    used_min = await coll.count_documents({"key": key, "ts": {"$gte": window_min}})
    used_hour = await coll.count_documents({"key": key, "ts": {"$gte": window_hour}})

    # Limites
    lim_min = quotas["per_min"]
    lim_hour = quotas["per_hour"]

    if lim_min > 0 and used_min >= lim_min:
        return RateLimitDecision(
            allowed=False, reason="per_min",
            retry_in_seconds=10, used_min=used_min, used_hour=used_hour,
        )
    if lim_hour > 0 and used_hour >= lim_hour:
        return RateLimitDecision(
            allowed=False, reason="per_hour",
            retry_in_seconds=600, used_min=used_min, used_hour=used_hour,
        )

    # Consume
    await coll.insert_one({
        "key": key,
        "tier": tier,
        "ts": now,
        "expires_at": now + timedelta(seconds=DOC_TTL_SECONDS),
    })

    return RateLimitDecision(
        allowed=True, reason=None,
        retry_in_seconds=0, used_min=used_min + 1, used_hour=used_hour + 1,
    )
