"""
frekcore_bridge.py — Bridge vers le service frekcore (identité racine de l'écosystème).

Architecture: SÉPARÉ de Laurent.ia, INTERCONNECTÉ via API.
En dev: utilise les mocks de kiltikonet_bridge.
En prod: bascule en mode HTTP via FREKCORE_API_URL + FREKCORE_API_KEY.

Le swap se fait UNIQUEMENT via variables d'env, AUCUNE modification de code requise.
"""
from __future__ import annotations

import os

import httpx

from services import kiltikonet_bridge

FREKCORE_API_URL = os.environ.get("FREKCORE_API_URL", "").strip()
FREKCORE_API_KEY = os.environ.get("FREKCORE_API_KEY", "").strip()
FREKCORE_TIMEOUT = float(os.environ.get("FREKCORE_TIMEOUT", "10"))

# Mock dev — liste stricte des FREK-IDs valides en absence de frekcore remote.
# En prod (FREKCORE_API_URL configuré), cette liste est ignorée.
_DEV_VALID_FREK_IDS = {
    "DEMO-SAYD":   {"role": "founder", "first_name": "Sayd"},
    "DEMO-ARTIST": {"role": "artist",  "first_name": "Mira"},
    "DEMO-PRO":    {"role": "pro",     "first_name": "Lina"},
}


def is_remote_configured() -> bool:
    return bool(FREKCORE_API_URL and FREKCORE_API_KEY)


async def validate_frek_id(frek_id: str) -> dict:
    """
    Valide un FREK-ID auprès du service frekcore.

    Routage:
    - `DEMO-*` → toujours dev whitelist (utile pour démo/tests même en prod)
    - autres   → frekcore.com si configuré, sinon dev whitelist
    """
    key = (frek_id or "").strip().upper()

    # Dev / demo IDs — toujours validés via whitelist locale
    if key.startswith("DEMO-"):
        meta = _DEV_VALID_FREK_IDS.get(key)
        if not meta:
            return {"valid": False, "frek_id": key}
        return {"valid": True, "frek_id": key, **meta}

    if not is_remote_configured():
        meta = _DEV_VALID_FREK_IDS.get(key)
        if not meta:
            return {"valid": False, "frek_id": key}
        return {"valid": True, "frek_id": key, **meta}

    try:
        async with httpx.AsyncClient(timeout=FREKCORE_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(
                f"{FREKCORE_API_URL.rstrip('/')}/api/frek/validate/{frek_id}",
                headers={"X-API-Key": FREKCORE_API_KEY, "X-Client-ID": "cvl-brain"},
            )
            if r.status_code == 404:
                return {"valid": False, "frek_id": frek_id}
            if r.status_code >= 500:
                # Frekcore down → ne fallback pas (sécurité), refuse
                return {"valid": False, "frek_id": frek_id, "error": "frekcore unavailable"}
            r.raise_for_status()
            return r.json()
    except (httpx.RequestError, httpx.HTTPStatusError):
        return {"valid": False, "frek_id": frek_id, "error": "frekcore unreachable"}


async def get_profile(frek_id: str) -> dict:
    """Profil complet enrichi (cultural_profile, badges, wallet)."""
    key = (frek_id or "").strip().upper()
    if key.startswith("DEMO-") or not is_remote_configured():
        return await kiltikonet_bridge.get_frek_profile(frek_id)

    try:
        async with httpx.AsyncClient(timeout=FREKCORE_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(
                f"{FREKCORE_API_URL.rstrip('/')}/api/frek/{frek_id}/profile",
                headers={"X-API-Key": FREKCORE_API_KEY, "X-Client-ID": "cvl-brain"},
            )
            r.raise_for_status()
            return r.json()
    except (httpx.RequestError, httpx.HTTPStatusError):
        # Fallback profil minimal
        return {"frek_id": frek_id, "first_name": frek_id.split("-")[-1].capitalize(), "role": "member", "cultural_profile": {}, "badges": [], "wallet": {}}
