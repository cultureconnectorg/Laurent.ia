"""
circuit_breaker.py — Couche d'arrêt actif.

Mode SHADOW (défaut) :
  - Le breaker ne bloque PAS le flux SSE. Il logge l'incident dans laurentia_guardrail_logs
    et envoie l'alerte SMS Niveau 3 si configurée.
  - Active : ORCHESTRATOR_CIRCUIT_BREAKER=false (défaut).

Mode ACTIVE :
  - ORCHESTRATOR_CIRCUIT_BREAKER=true → le breaker peut couper le flux pour un session_id.
  - L'état de blocage est persisté en mémoire (app.state.cb_blocked_sessions : set[str]).

La décision Founder (Valider/Bloquer/Modifier) arrive via :
  - POST /api/admin/orchestrator/decisions
  - ou réponse SMS inbound → POST /api/webhook/ovh-sms-reply (best-effort).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def is_active() -> bool:
    """Le Circuit Breaker coupe-t-il vraiment le flux (mode ACTIVE) ?"""
    return os.environ.get("ORCHESTRATOR_CIRCUIT_BREAKER", "false").strip().lower() in ("1", "true", "yes")


class CircuitBreaker:
    """Gestionnaire d'état des incidents critiques par session."""

    def __init__(self) -> None:
        self._blocked_sessions: set[str] = set()
        self._open_incidents: dict[str, dict[str, Any]] = {}  # incident_id → {…}

    # ---- API consultative ----

    def session_blocked(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        if not is_active():
            return False
        return session_id in self._blocked_sessions

    def open_incidents(self) -> list[dict[str, Any]]:
        return list(self._open_incidents.values())

    # ---- API actions ----

    def register_incident(self, *, incident_id: str, agent: str, session_id: str | None,
                          reason: str, summary: str = "") -> dict[str, Any]:
        rec = {
            "incident_id": incident_id,
            "agent": agent,
            "session_id": session_id,
            "reason": reason,
            "summary": summary,
            "status": "open",
            "decision": None,
            "decided_by": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decided_at": None,
            "active_mode": is_active(),
        }
        self._open_incidents[incident_id] = rec
        if is_active() and session_id:
            self._blocked_sessions.add(session_id)
        logger.info("circuit_breaker: incident=%s agent=%s session=%s active=%s",
                    incident_id, agent, session_id, is_active())
        return rec

    def decide(self, *, incident_id: str, decision: str, decided_by: str) -> dict[str, Any] | None:
        """
        decision ∈ {"validate", "block", "modify"}.
        - validate : on lève le blocage (utilisateur reçoit la réponse).
        - block    : on confirme le blocage (mode ACTIVE), le user reçoit une réponse de repli.
        - modify   : marqué pour révision, blocage maintenu.
        """
        rec = self._open_incidents.get(incident_id)
        if not rec:
            return None
        rec["status"] = "closed"
        rec["decision"] = decision
        rec["decided_by"] = decided_by
        rec["decided_at"] = datetime.now(timezone.utc).isoformat()
        session_id = rec.get("session_id")
        if decision == "validate" and session_id:
            self._blocked_sessions.discard(session_id)
        elif decision == "block" and session_id and is_active():
            self._blocked_sessions.add(session_id)
        return rec
