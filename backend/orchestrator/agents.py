"""
agents.py — Registre des 20 agents Laurent.ia (Chantier 9).

4 départements × 4-7 agents = 20 agents.

Architecture :
  - Chaque agent est un objet WARM persistant en RAM (app.state.agents[agent_id]).
  - Il s'abonne à un ou plusieurs canaux EventBus.
  - Son handler `handle(signal, ctx)` est NON-BLOQUANT et ne lève jamais.
  - État santé : green (OK), orange (doute), red (incident actif).

Tous les agents sont en mode SHADOW par défaut — ils LOGGUENT mais ne décident pas
de bloquer le flux. Le Circuit Breaker (services/circuit_breaker.py) seul peut couper.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from .signals import (
    LEVEL_CRITICAL,
    LEVEL_LOG,
    Signal,
    CHANNEL_CRITICAL,
    CHANNEL_GUARDRAIL,
    CHANNEL_INTAKE,
    CHANNEL_MEMORY,
    CHANNEL_STREAM_CHUNK,
    CHANNEL_STREAM_DONE,
    SIGNAL_CRITICAL,
    SIGNAL_INFO,
    SIGNAL_UPDATE,
)

logger = logging.getLogger(__name__)


# ---------- Référentiel des 20 agents ----------

AGENT_REGISTRY = [
    # ── 1. Pôle Stratégique (Le Cerveau, 3) ──
    {"id": "agent-souverainete",  "department": "strategie",   "role": "Garde du Corpus — respect ADN Laurent.ia"},
    {"id": "agent-memoire",       "department": "strategie",   "role": "Mémorialiste — historique & apprentissage"},
    {"id": "agent-veille",        "department": "strategie",   "role": "Veille — tendances externes"},
    # ── 2. Pôle Opérationnel (L'Aigle, 7) ──
    {"id": "agent-guardrail-text",  "department": "operations", "role": "Guardrail Texte — filtrage entrée"},
    {"id": "agent-guardrail-image", "department": "operations", "role": "Guardrail Image — validation visuelle"},
    {"id": "agent-guardrail-code",  "department": "operations", "role": "Guardrail Code — anti-injection"},
    {"id": "agent-streaming",       "department": "operations", "role": "Streaming — flux SSE token-by-token"},
    {"id": "agent-latence",         "department": "operations", "role": "Aigle — monitoring latence"},
    {"id": "agent-securite",        "department": "operations", "role": "Sécurité — détection hack/injection"},
    {"id": "agent-sms-alert",       "department": "operations", "role": "Alerte SMS — canal Founder Niveau 3"},
    # ── 3. Pôle Créatif (L'Artiste, 6) ──
    {"id": "agent-redaction",   "department": "creation", "role": "Styliste — ton & voix Laurent.ia"},
    {"id": "agent-visuel",      "department": "creation", "role": "Iconographe — génération & validation visuels"},
    {"id": "agent-data",        "department": "creation", "role": "Data-Miner — chiffres & faits"},
    {"id": "agent-recherche",   "department": "creation", "role": "Fact-Checker — vérification sources"},
    {"id": "agent-traduction",  "department": "creation", "role": "Traducteur Culturel — multilinguisme & créole"},
    {"id": "agent-social",      "department": "creation", "role": "Social — adaptation réseaux"},
    # ── 4. Pôle Administration (L'Orchestre, 4) ──
    {"id": "agent-receptionniste", "department": "interface", "role": "Réceptionniste — qualification requête < 50ms"},
    {"id": "agent-arbitre",        "department": "interface", "role": "Arbitre — tranche conflits inter-agents"},
    {"id": "agent-rapporteur",     "department": "interface", "role": "Rapporteur — dashboard Founder quotidien"},
    {"id": "agent-auto-maintenance","department": "interface","role": "Auto-Guérisseur — redémarrage agents KO"},
]

assert len(AGENT_REGISTRY) == 20, "Chantier 9 exige exactement 20 agents"


# ---------- Patterns souverains (utilisés par agent-souverainete) ----------

# Mots/marqueurs qui ne doivent JAMAIS sortir publiquement (rupture branding)
_FORBIDDEN_PUBLIC_LEAKS = re.compile(
    r"\b(cvln|cvl\s*brain|kiltikonet|phases?\s+internes?|emergent\s+agent|"
    r"agent\s+(souverainet[eé]|m[eé]moire))\b",
    re.IGNORECASE,
)

# Anti-jailbreak — instructions visant à faire sortir Laurent.ia de sa persona
_JAILBREAK_PATTERNS = re.compile(
    r"\b(ignore\s+(?:previous|all|prior)\s+instructions?|disregard\s+(?:the\s+)?system\s+prompt|"
    r"you\s+are\s+now\s+|act\s+as\s+(?:if|though)|pretend\s+to\s+be|"
    r"jailbreak|prompt\s+injection|sudo\s+mode)\b",
    re.IGNORECASE,
)


# ---------- Classe Agent ----------

class Agent:
    """Agent warm en RAM. Tient son état santé + dernier signal traité."""

    def __init__(self, spec: dict[str, str]) -> None:
        self.id: str = spec["id"]
        self.department: str = spec["department"]
        self.role: str = spec["role"]
        self.status: str = "green"          # green | orange | red
        self.last_seen: str | None = None
        self.total_signals: int = 0
        self.last_incident_id: str | None = None
        self.last_detail: str | None = None

    def touch(self, signal: Signal, status: str = "green", detail: str | None = None) -> None:
        self.status = status
        self.last_seen = datetime.now(timezone.utc).isoformat()
        self.total_signals += 1
        self.last_incident_id = signal.incident_id
        self.last_detail = detail

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "department": self.department,
            "role": self.role,
            "status": self.status,
            "last_seen": self.last_seen,
            "total_signals": self.total_signals,
            "last_incident_id": self.last_incident_id,
            "last_detail": self.last_detail,
        }


# ---------- Helpers analyse contenu ----------

def detect_souverainete_breach(text: str) -> str | None:
    """Retourne un motif si le texte trahit la souveraineté Laurent.ia."""
    if not text:
        return None
    m = _FORBIDDEN_PUBLIC_LEAKS.search(text)
    if m:
        return f"forbidden_leak:{m.group(0).lower()}"
    return None


def detect_jailbreak(text: str) -> str | None:
    if not text:
        return None
    m = _JAILBREAK_PATTERNS.search(text)
    if m:
        return f"jailbreak:{m.group(0).lower()}"
    return None
