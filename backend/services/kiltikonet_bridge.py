"""
kiltikonet_bridge.py — Interconnexion vers kiltikonet.fr (PRODUCTION v1.2-LIVE).

Mode :
  - DEMO-* whitelist  → toujours autorisé (démo/pytest offline).
  - Bridge non configuré (KILTIKONET_API_URL vide) → guest fallback (dev only).
  - Bridge configuré + 200                          → données amont.
  - Bridge configuré + 401/403/404                  → identité refusée (valid=False).
  - Bridge configuré + 5xx/timeout/network          → KiltikonetUnavailable
    (PROPAGÉ → HTTP 503 côté gateway). Pas de silent guest fallback en LIVE :
    Kiltikonet = validation identité FREK-ID, sa panne doit échouer fort.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

KILTIKONET_API_URL = os.environ.get("KILTIKONET_API_URL", "").rstrip("/")
KILTIKONET_API_KEY = os.environ.get("KILTIKONET_API_KEY", "")
_TIMEOUT = float(os.environ.get("KILTIKONET_TIMEOUT_SECONDS", "5.0"))


class KiltikonetUnavailable(RuntimeError):
    """Levée quand le bridge est configuré mais que l'amont est injoignable."""


# Whitelist DEMO-* — conservée pour pytest, démo offline et continuité.
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

    Comportement STRICT en mode LIVE :
      - DEMO-* whitelist → valid
      - bridge non configuré (dev) → valid guest
      - 200 amont → données réelles
      - 401/403/404 amont → {"valid": False, ...}
      - 5xx/timeout/network → KiltikonetUnavailable (→ HTTP 503)
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
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.error("kiltikonet validate unreachable frek=%s err=%s", frek_id, e)
        raise KiltikonetUnavailable(f"Kiltikonet unreachable: {e}") from e

    if r.status_code == 200:
        logger.info("kiltikonet validate OK frek=%s", frek_id)
        return r.json()
    if r.status_code in (401, 403, 404):
        logger.info("kiltikonet validate refused frek=%s status=%s", frek_id, r.status_code)
        return {"valid": False, "frek_id": frek_id}
    # 5xx ou tout autre code inattendu → panne amont
    logger.error("kiltikonet validate upstream error frek=%s status=%s", frek_id, r.status_code)
    raise KiltikonetUnavailable(f"Kiltikonet upstream status={r.status_code}")


async def get_frek_profile(frek_id: str) -> dict:
    """
    Profil culturel 7D + badges + wallet.

    Comportement :
      - DEMO-* → mock local
      - bridge non configuré → profil par défaut
      - 200 amont → merge avec defaults
      - 404 amont → profil par défaut (utilisateur sans profil enrichi)
      - 5xx/timeout/network → KiltikonetUnavailable (→ HTTP 503)
    """
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
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.error("kiltikonet profile unreachable frek=%s err=%s", frek_id, e)
        raise KiltikonetUnavailable(f"Kiltikonet unreachable: {e}") from e

    if r.status_code == 200:
        data = r.json()
        base = _default_profile(frek_id)
        base.update({k: v for k, v in data.items() if v is not None})
        return base
    if r.status_code == 404:
        # Utilisateur validé mais sans profil enrichi → defaults
        return _default_profile(frek_id)
    logger.error("kiltikonet profile upstream error frek=%s status=%s", frek_id, r.status_code)
    raise KiltikonetUnavailable(f"Kiltikonet upstream status={r.status_code}")
