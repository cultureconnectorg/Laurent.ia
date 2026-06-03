"""
signals.py — Types de signaux échangés sur l'EventBus.

Hiérarchie (Niveau 0 → 3) :
  0 : auto-correction silencieuse (jamais logguée)
  1 : info → log dans laurentia_guardrail_logs
  2 : check → un agent demande validation par un autre
  3 : critical → Circuit Breaker + alerte SMS Founder
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# Niveaux d'alerte
LEVEL_AUTO = 0
LEVEL_LOG = 1
LEVEL_CHECK = 2
LEVEL_CRITICAL = 3

# Types de signaux
SIGNAL_INFO = "SIGNAL_INFO"
SIGNAL_CHECK = "SIGNAL_CHECK"
SIGNAL_CRITICAL = "SIGNAL_CRITICAL"
SIGNAL_UPDATE = "SIGNAL_UPDATE"

# Canaux principaux (un agent s'abonne à un ou plusieurs canaux)
CHANNEL_INTAKE = "intake"          # requête utilisateur entrante
CHANNEL_STREAM_CHUNK = "stream"    # chunk SSE en cours
CHANNEL_STREAM_DONE = "stream_done"
CHANNEL_GUARDRAIL = "guardrail"
CHANNEL_CRITICAL = "critical"
CHANNEL_MEMORY = "memory"


@dataclass
class Signal:
    """Message standard transitant sur l'EventBus."""
    type: str
    channel: str
    payload: dict[str, Any] = field(default_factory=dict)
    incident_id: str = field(default_factory=lambda: f"inc-{uuid.uuid4().hex[:10]}")
    session_id: str | None = None
    source_agent: str | None = None
    level: int = LEVEL_LOG
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "channel": self.channel,
            "payload": self.payload,
            "incident_id": self.incident_id,
            "session_id": self.session_id,
            "source_agent": self.source_agent,
            "level": self.level,
            "ts": self.ts,
        }
