"""
labelos_bridge.py — Interconnexion vers LabelOS
MVP: MOCKÉ.
"""
from __future__ import annotations

import os

LABELOS_API_URL = os.environ.get("LABELOS_API_URL", "")
LABELOS_API_KEY = os.environ.get("LABELOS_API_KEY", "")


async def get_artist_context(frek_id: str) -> dict:
    """MOCK: contexte artiste depuis LabelOS."""
    return {
        "frek_id": frek_id,
        "stage_name": "Artiste démo",
        "genres": ["zouk", "afro-house"],
        "next_release": "2026-09-01",
        "tour_status": "preparation",
        "team": ["manager", "producer"],
    }
