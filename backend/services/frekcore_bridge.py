"""
frekcore_bridge.py — Bridge vers le service frekcore (identité racine de l'écosystème).

Architecture: SÉPARÉ de Laurent.ia, INTERCONNECTÉ via API.
En dev: utilise les mocks de kiltikonet_bridge.
En prod: API FREKCORE réelle via services/frekcore_client.py (OAuth client_credentials,
permissions explicites accordées par FREKCORE ; jamais d'accès à sa base).

Le swap se fait UNIQUEMENT via variables d'env, AUCUNE modification de code requise.
"""
from __future__ import annotations

import os

import httpx

from services import frekcore_client, kiltikonet_bridge

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
        if (os.environ.get("APP_ENV") or "production").strip().lower() not in ("development", "test"):
            return {"valid": False, "frek_id": key}  # demo identities never exist on a deployed instance
        meta = _DEV_VALID_FREK_IDS.get(key)
        if not meta:
            return {"valid": False, "frek_id": key}
        return {"valid": True, "frek_id": key, **meta}

    if not is_remote_configured():
        meta = _DEV_VALID_FREK_IDS.get(key)
        if not meta:
            return {"valid": False, "frek_id": key}
        return {"valid": True, "frek_id": key, **meta}

    # C1: real FREKCORE route, through the authenticated client (services/frekcore_client.py).
    try:
        st = await frekcore_client.identity_status(key)
    except frekcore_client.FrekcoreError as e:
        if e.status == 404:
            return {"valid": False, "frek_id": key}
        # FREKCORE down or refusing: never fall back to "valid" (security).
        return {"valid": False, "frek_id": key, "error": "frekcore unavailable"}
    except httpx.RequestError:
        return {"valid": False, "frek_id": key, "error": "frekcore unreachable"}
    valid = bool(st.get("active")) and not st.get("revoked") and not st.get("expired")
    return {"valid": valid, "frek_id": key, "revoked": bool(st.get("revoked"))}


async def get_profile(frek_id: str) -> dict:
    """Profil complet enrichi (cultural_profile, badges, wallet)."""
    key = (frek_id or "").strip().upper()
    if key.startswith("DEMO-") or not is_remote_configured():
        return await kiltikonet_bridge.get_frek_profile(frek_id)

    try:
        detail = await frekcore_client.identity_detail(key)
        return {"frek_id": key, "first_name": detail.get("display_name") or key.split("-")[-1].capitalize(),
                "role": detail.get("role") or "member", "cultural_profile": {}, "badges": [], "wallet": {}}
    except (frekcore_client.FrekcoreError, httpx.RequestError):
        # Fallback profil minimal
        return {"frek_id": frek_id, "first_name": frek_id.split("-")[-1].capitalize(), "role": "member", "cultural_profile": {}, "badges": [], "wallet": {}}
