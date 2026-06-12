"""
api_keys.py — Clés API scoped par tenant (X-API-Key parallèle au JWT).

Format clé : `lia_<tier>_<random32>` (32 chars URL-safe).
Stockage : SHA-256 hashé dans laurentia_api_keys.

Sécurité :
  - Au moins 32 octets d'entropie via secrets.token_urlsafe(32).
  - Chaque clé est révocable instantanément (status = "revoked").
  - Aucune clé en clair n'est jamais renvoyée après création initiale.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def create_key(db: AsyncIOMotorDatabase, *, frek_id: str, tier: str,
                     label: str = "default") -> dict:
    """Génère et persiste une nouvelle clé. Retourne {key_id, raw_key, …}.
    `raw_key` n'est JAMAIS reloggable — l'appelant doit la transmettre une seule fois."""
    key_id = f"key-{uuid.uuid4().hex[:12]}"
    raw_key = f"lia_{tier.lower()}_{secrets.token_urlsafe(32)}"
    doc = {
        "key_id": key_id,
        "frek_id": frek_id,
        "tier": tier.lower(),
        "label": label,
        "hash": _hash_key(raw_key),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "last_used_at": None,
        "use_count": 0,
    }
    await db.laurentia_api_keys.insert_one(dict(doc))
    return {"key_id": key_id, "raw_key": raw_key, "label": label,
            "created_at": doc["created_at"], "status": "active"}


async def revoke_key(db: AsyncIOMotorDatabase, *, frek_id: str, key_id: str) -> bool:
    """Révocation immédiate (status=revoked). Retourne True si la clé appartenait bien au frek_id."""
    res = await db.laurentia_api_keys.update_one(
        {"key_id": key_id, "frek_id": frek_id, "status": "active"},
        {"$set": {"status": "revoked",
                  "revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    return res.modified_count > 0


async def list_keys(db: AsyncIOMotorDatabase, *, frek_id: str) -> list[dict]:
    """Liste les clés actives (sans hash)."""
    cur = db.laurentia_api_keys.find(
        {"frek_id": frek_id},
        {"_id": 0, "hash": 0},
    ).sort("created_at", -1)
    return await cur.to_list(length=100)


async def validate_key(db: AsyncIOMotorDatabase, raw_key: str) -> dict | None:
    """Valide une clé brute. Retourne le doc (sans hash) si OK, None sinon.
    Met à jour last_used_at + use_count."""
    if not raw_key or not raw_key.startswith("lia_"):
        return None
    doc = await db.laurentia_api_keys.find_one(
        {"hash": _hash_key(raw_key), "status": "active"},
        {"_id": 0, "hash": 0},
    )
    if not doc:
        return None
    await db.laurentia_api_keys.update_one(
        {"key_id": doc["key_id"]},
        {"$set": {"last_used_at": datetime.now(timezone.utc).isoformat()},
         "$inc": {"use_count": 1}},
    )
    return doc
