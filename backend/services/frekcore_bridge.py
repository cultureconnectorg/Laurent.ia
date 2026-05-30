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

    En dev (pas de FREKCORE_API_URL): liste blanche stricte _DEV_VALID_FREK_IDS.
    En prod: appel HTTP vers FREKCORE_API_URL.

    Retour: { valid: bool, frek_id, role, first_name? }
    """
    if not is_remote_configured():
        key = (frek_id or "").strip().upper()
        meta = _DEV_VALID_FREK_IDS.get(key)
        if not meta:
            return {"valid": False, "frek_id": key}
        return {"valid": True, "frek_id": key, **meta}

    async with httpx.AsyncClient(timeout=FREKCORE_TIMEOUT) as client:
        r = await client.get(
            f"{FREKCORE_API_URL.rstrip('/')}/api/frek/validate/{frek_id}",
            headers={"X-API-Key": FREKCORE_API_KEY},
        )
        if r.status_code == 404:
            return {"valid": False, "frek_id": frek_id}
        r.raise_for_status()
        return r.json()


async def get_profile(frek_id: str) -> dict:
    """Profil complet enrichi (cultural_profile, badges, wallet)."""
    if not is_remote_configured():
        # En dev on délègue à kiltikonet_bridge qui détient les profils 7D mockés
        return await kiltikonet_bridge.get_frek_profile(frek_id)

    async with httpx.AsyncClient(timeout=FREKCORE_TIMEOUT) as client:
        r = await client.get(
            f"{FREKCORE_API_URL.rstrip('/')}/api/frek/{frek_id}/profile",
            headers={"X-API-Key": FREKCORE_API_KEY},
        )
        r.raise_for_status()
        return r.json()
