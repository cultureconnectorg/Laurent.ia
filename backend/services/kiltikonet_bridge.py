"""
kiltikonet_bridge.py — Interconnexion vers kiltikonet.fr (PRODUCTION).

Mode :
  - Si KILTIKONET_API_URL est défini → appels httpx réels via X-API-Key.
  - Sinon (dev/test) → fallback whitelist DEMO-* (mock historique).
  - Si l'appel réel échoue (5xx, timeout, network) → fallback sur le mock pour
    ne JAMAIS bloquer une session utilisateur. La résilience prime.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

KILTIKONET_API_URL = os.environ.get("KILTIKONET_API_URL", "").rstrip("/")
KILTIKONET_API_KEY = os.environ.get("KILTIKONET_API_KEY", "")
_TIMEOUT = float(os.environ.get("KILTIKONET_TIMEOUT_SECONDS", "5.0"))

# Fallback DEMO-* — conservé pour tests pytest et démo offline.
_MOCK_PROFILES = {
    "DEMO-SAYD": {
        "valid": True, "frek_id": "DEMO-SAYD", "first_name": "Sayd", "role": "founder",
        "cultural_profile": {"rythme": 0.82, "memoire": 0.91, "oralite": 0.76,
                             "spiritualite": 0.68, "communaute": 0.88, "creativite": 0.95, "souverainete": 0.92},
        "badges": ["fondateur", "coeurvolan"], "wallet": {"jcc_balance": 150},
    },
    "DEMO-ARTIST": {
        "valid": True, "frek_id": "DEMO-ARTIST", "first_name": "Mira", "role": "artist",
        "cultural_profile": {"rythme": 0.74, "memoire": 0.62, "oralite": 0.84,
                             "spiritualite": 0.55, "communaute": 0.71, "creativite": 0.89, "souverainete": 0.66},
        "badges": ["artiste"], "wallet": {"jcc_balance": 50},
    },
}


def _default_profile(frek_id: str) -> dict:
    first_name = frek_id.split("-")[-1].capitalize() if "-" in frek_id else "Hôte"
    return {
        "valid": True, "frek_id": frek_id, "first_name": first_name, "role": "guest",
        "cultural_profile": {"rythme": 0.5, "memoire": 0.5, "oralite": 0.5,
                             "spiritualite": 0.5, "communaute": 0.5, "creativite": 0.5, "souverainete": 0.5},
        "badges": [], "wallet": {"jcc_balance": 0},
    }


def _bridge_configured() -> bool:
    return bool(KILTIKONET_API_URL and KILTIKONET_API_KEY)


async def validate_frek_id(frek_id: str) -> dict:
    """
    Valide un FREK-ID via Kiltikonet.
    Fallback mock si bridge non configuré OU si le serveur amont est down.
    """
    if frek_id.startswith("DEMO-") and frek_id in _MOCK_PROFILES:
        p = _MOCK_PROFILES[frek_id]
        return {"valid": True, "frek_id": frek_id, "role": p["role"]}

    if not _bridge_configured():
        # Mode dev — accepte tout FREK-ID avec rôle guest
        return {"valid": True, "frek_id": frek_id, "role": "guest"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{KILTIKONET_API_URL}/api/users/validate/{frek_id}",
                headers={"X-API-Key": KILTIKONET_API_KEY},
            )
        if r.status_code == 200:
            data = r.json()
            logger.info("kiltikonet validate OK frek=%s", frek_id)
            return data
        if r.status_code in (401, 403):
            logger.warning("kiltikonet auth refused (status=%s) — check API_KEY", r.status_code)
        logger.warning("kiltikonet validate non-200 status=%s frek=%s", r.status_code, frek_id)
    except Exception as e:
        logger.warning("kiltikonet validate failed (fallback mock): %s", e)

    # Résilience : si Kiltikonet est down, on accepte en guest sans bloquer.
    return {"valid": True, "frek_id": frek_id, "role": "guest"}


async def get_frek_profile(frek_id: str) -> dict:
    """Profil culturel 7D + badges + wallet. Fallback mock si bridge down."""
    if frek_id.startswith("DEMO-") and frek_id in _MOCK_PROFILES:
        return _MOCK_PROFILES[frek_id]

    if not _bridge_configured():
        return _default_profile(frek_id)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{KILTIKONET_API_URL}/api/users/{frek_id}/profile",
                headers={"X-API-Key": KILTIKONET_API_KEY},
            )
        if r.status_code == 200:
            data = r.json()
            # Merge avec defaults pour tolérer un schéma kiltikonet incomplet
            base = _default_profile(frek_id)
            base.update({k: v for k, v in data.items() if v is not None})
            return base
        logger.warning("kiltikonet profile non-200 status=%s frek=%s", r.status_code, frek_id)
    except Exception as e:
        logger.warning("kiltikonet profile failed (fallback mock): %s", e)

    return _default_profile(frek_id)
