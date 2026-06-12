"""
value_estimator.py — Estime la valeur business générée par chaque action utilisateur.

Mode "ROI Souverain" : chaque interaction sauvée en `laurentia_activity_log`
est convertie en minutes économisées (vs faire la même chose manuellement).
Ces ratios alimentent les rapports daily/weekly côté user ET founder.

Configurable via ENV : LAURENTIA_VALUE_<ACTION>=<minutes_int>
"""
from __future__ import annotations

import os

# Ratios par défaut (minutes économisées)
DEFAULT_RATIOS: dict[str, int] = {
    "QUERY_PROCESSED":  5,    # 1 chat = 5 min de recherche/rédaction épargnées
    "PDF_EXPORT":       15,   # Génération PDF signé
    "ECHO_SHARED":      20,   # Partage public formaté
    "FILE_PROCESSED":   8,    # Analyse PDF/DOCX
    "VOICE_TRANSCRIBED":3,
    "MEMORY_RECALLED":  2,
    "CORPUS_INGESTED":  4,
    "SOCIAL_POST":      30,   # Publication sociale autonome
}


def estimate(action: str, weight: float = 1.0) -> int:
    """Retourne les minutes économisées par une action, multipliées par `weight`."""
    base = int(os.environ.get(f"LAURENTIA_VALUE_{action.upper()}",
                              DEFAULT_RATIOS.get(action.upper(), 0)))
    return max(0, int(base * weight))


def all_ratios() -> dict[str, int]:
    """Snapshot des ratios actifs (utilisé par /api/me/report pour expliquer le calcul)."""
    return {k: estimate(k) for k in DEFAULT_RATIOS}
