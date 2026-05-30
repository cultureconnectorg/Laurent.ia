"""
kiltikonet_bridge.py — Interconnexion vers le serveur kiltikonet.fr
MVP: MOCKÉ. Renvoie des données stub valides pour permettre le test end-to-end.
En prod, ces fonctions feront des appels httpx vers KILTIKONET_API_URL.
"""
from __future__ import annotations

import os

KILTIKONET_API_URL = os.environ.get("KILTIKONET_API_URL", "")
KILTIKONET_API_KEY = os.environ.get("KILTIKONET_API_KEY", "")

# MOCK: profils culturels 7D fictifs pour quelques FREK-ID de démo.
_MOCK_PROFILES = {
    "DEMO-SAYD": {
        "valid": True,
        "frek_id": "DEMO-SAYD",
        "first_name": "Sayd",
        "role": "founder",
        "cultural_profile": {
            "rythme": 0.82, "memoire": 0.91, "oralite": 0.76,
            "spiritualite": 0.68, "communaute": 0.88, "creativite": 0.95, "souverainete": 0.92,
        },
        "badges": ["fondateur", "coeurvolan"],
        "wallet": {"jcc_balance": 150},
    },
    "DEMO-ARTIST": {
        "valid": True,
        "frek_id": "DEMO-ARTIST",
        "first_name": "Mira",
        "role": "artist",
        "cultural_profile": {
            "rythme": 0.74, "memoire": 0.62, "oralite": 0.84,
            "spiritualite": 0.55, "communaute": 0.71, "creativite": 0.89, "souverainete": 0.66,
        },
        "badges": ["artiste"],
        "wallet": {"jcc_balance": 50},
    },
}


async def validate_frek_id(frek_id: str) -> dict:
    """MOCK: valide un FREK-ID via kiltikonet."""
    if frek_id in _MOCK_PROFILES:
        p = _MOCK_PROFILES[frek_id]
        return {"valid": True, "frek_id": frek_id, "role": p["role"]}
    # FREK-ID inconnu: en mode demo, on l'accepte avec un profil par défaut
    return {"valid": True, "frek_id": frek_id, "role": "guest"}


async def get_frek_profile(frek_id: str) -> dict:
    """MOCK: profil culturel 7D + badges + wallet."""
    if frek_id in _MOCK_PROFILES:
        return _MOCK_PROFILES[frek_id]
    # Profil par défaut pour FREK-ID inconnu
    first_name = frek_id.split("-")[-1].capitalize() if "-" in frek_id else "Hôte"
    return {
        "valid": True,
        "frek_id": frek_id,
        "first_name": first_name,
        "role": "guest",
        "cultural_profile": {
            "rythme": 0.5, "memoire": 0.5, "oralite": 0.5,
            "spiritualite": 0.5, "communaute": 0.5, "creativite": 0.5, "souverainete": 0.5,
        },
        "badges": [],
        "wallet": {"jcc_balance": 0},
    }
