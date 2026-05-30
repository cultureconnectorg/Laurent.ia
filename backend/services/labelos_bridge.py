"""
labelos_bridge.py — Interconnexion vers LabelOS (PRODUCTION).

Mode :
  - Si LABELOS_API_URL configuré → appel httpx réel via X-API-Key.
  - Sinon → fallback stub neutre.
  - Si l'appel réel échoue → fallback stub. Le Gateway ne doit JAMAIS être bloqué
    par une indisponibilité LabelOS.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

LABELOS_API_URL = os.environ.get("LABELOS_API_URL", "").rstrip("/")
LABELOS_API_KEY = os.environ.get("LABELOS_API_KEY", "")
_TIMEOUT = float(os.environ.get("LABELOS_TIMEOUT_SECONDS", "5.0"))


def _bridge_configured() -> bool:
    return bool(LABELOS_API_URL and LABELOS_API_KEY)


def _stub(frek_id: str) -> dict:
    return {
        "frek_id": frek_id,
        "stage_name": None,
        "genres": [],
        "next_release": None,
        "tour_status": None,
        "team": [],
        "_source": "stub",
    }


async def get_artist_context(frek_id: str) -> dict:
    """Contexte artiste depuis LabelOS. Fallback stub si indisponible."""
    if not _bridge_configured():
        return _stub(frek_id)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{LABELOS_API_URL}/api/artists/{frek_id}/context",
                headers={"X-API-Key": LABELOS_API_KEY},
            )
        if r.status_code == 200:
            data = r.json()
            data["_source"] = "labelos"
            return data
        if r.status_code == 404:
            # FREK-ID non labellisé — comportement normal, on retourne le stub
            return _stub(frek_id)
        logger.warning("labelos context non-200 status=%s frek=%s", r.status_code, frek_id)
    except Exception as e:
        logger.warning("labelos context failed (fallback stub): %s", e)

    return _stub(frek_id)
