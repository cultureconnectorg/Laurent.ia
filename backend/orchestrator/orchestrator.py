"""
orchestrator.py — Chef d'orchestre Laurent.ia (Chantier 9).

Rôle :
  - Instancier les 20 agents WARM en RAM (zéro reload).
  - Câbler les handlers à l'EventBus.
  - Persister chaque signal Niveau ≥ 1 dans laurentia_guardrail_logs.
  - Pour SIGNAL_CRITICAL : enregistrer incident + déclencher SMS OVH (best-effort).
  - Exposer dispatch_*() : hooks NON-BLOQUANTS appelés par laurentia_gateway.

Mode SHADOW par défaut (ORCHESTRATOR_CIRCUIT_BREAKER=false) :
  - Les agents OBSERVENT et LOGGUENT, mais ne bloquent JAMAIS le flux SSE.
  - Si une dérive souveraine est détectée → incident enregistré + SMS envoyé.
  - Le pipeline /api/laurentia/query continue intact (zéro régression des 84 tests).

Mode ACTIVE (ORCHESTRATOR_CIRCUIT_BREAKER=true) :
  - Le breaker peut couper le flux pour un session_id.
  - laurentia_gateway interroge orchestrator.is_session_blocked() avant de pousser un chunk.
"""
from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from .agents import (
    AGENT_REGISTRY,
    Agent,
    detect_jailbreak,
    detect_souverainete_breach,
)
from .circuit_breaker import CircuitBreaker, is_active
from .event_bus import EventBus
from .signals import (
    LEVEL_CHECK,
    LEVEL_CRITICAL,
    LEVEL_LOG,
    Signal,
    CHANNEL_CRITICAL,
    CHANNEL_GUARDRAIL,
    CHANNEL_INTAKE,
    CHANNEL_MEMORY,
    CHANNEL_STREAM_CHUNK,
    CHANNEL_STREAM_DONE,
    SIGNAL_CHECK,
    SIGNAL_CRITICAL,
    SIGNAL_INFO,
    SIGNAL_UPDATE,
)
from . import sms_ovh

logger = logging.getLogger(__name__)


class Orchestrator:
    """Singleton attaché à app.state.orchestrator."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.agents: dict[str, Agent] = {spec["id"]: Agent(spec) for spec in AGENT_REGISTRY}
        self.bus = EventBus()
        self.breaker = CircuitBreaker()
        self._wire_agents()

    # ---------------- Câblage agents ----------------

    def _wire_agents(self) -> None:
        # --- Pôle Stratégique
        self.bus.subscribe(CHANNEL_STREAM_CHUNK, self._h_souverainete)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_memoire)
        self.bus.subscribe(CHANNEL_INTAKE,       self._h_veille)
        # --- Pôle Opérationnel
        self.bus.subscribe(CHANNEL_INTAKE,       self._h_guardrail_text)
        self.bus.subscribe(CHANNEL_STREAM_CHUNK, self._h_guardrail_text_chunk)
        self.bus.subscribe(CHANNEL_INTAKE,       self._h_guardrail_image)
        self.bus.subscribe(CHANNEL_INTAKE,       self._h_guardrail_code)
        self.bus.subscribe(CHANNEL_STREAM_CHUNK, self._h_streaming)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_latence)
        self.bus.subscribe(CHANNEL_INTAKE,       self._h_securite)
        self.bus.subscribe(CHANNEL_CRITICAL,     self._h_sms_alert)
        # --- Pôle Créatif (observateurs passifs en mode shadow)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_redaction)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_visuel)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_data)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_recherche)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_traduction)
        self.bus.subscribe(CHANNEL_STREAM_DONE,  self._h_social)
        # --- Pôle Interface
        self.bus.subscribe(CHANNEL_INTAKE,       self._h_receptionniste)
        self.bus.subscribe(CHANNEL_GUARDRAIL,    self._h_arbitre)
        self.bus.subscribe(CHANNEL_MEMORY,       self._h_rapporteur)
        self.bus.subscribe(CHANNEL_GUARDRAIL,    self._h_auto_maintenance)

    def start(self) -> None:
        self.bus.start()
        logger.info("orchestrator: started — 20 agents warm, mode=%s",
                    "ACTIVE" if is_active() else "SHADOW")

    def stop(self) -> None:
        self.bus.stop()

    # ---------------- API publique appelée par laurentia_gateway ----------------

    def dispatch_intake(self, *, session_id: str, frek_id_hash: str, user_input: str) -> None:
        """Hook NON-BLOQUANT appelé dès qu'une requête utilisateur arrive."""
        self.bus.publish(Signal(
            type=SIGNAL_INFO, channel=CHANNEL_INTAKE,
            session_id=session_id, level=LEVEL_LOG,
            payload={"frek_id_hash": frek_id_hash, "input": user_input},
        ))

    def dispatch_stream_chunk(self, *, session_id: str, chunk: str) -> None:
        """Hook NON-BLOQUANT — émis pour chaque token/groupe de tokens SSE."""
        self.bus.publish(Signal(
            type=SIGNAL_INFO, channel=CHANNEL_STREAM_CHUNK,
            session_id=session_id, level=LEVEL_LOG,
            payload={"chunk": chunk},
        ))

    def dispatch_stream_done(self, *, session_id: str, full_text: str,
                              latency_ms: int, tokens: int) -> None:
        self.bus.publish(Signal(
            type=SIGNAL_INFO, channel=CHANNEL_STREAM_DONE,
            session_id=session_id, level=LEVEL_LOG,
            payload={"full_text": full_text, "latency_ms": latency_ms, "tokens": tokens},
        ))
        self.bus.publish(Signal(
            type=SIGNAL_UPDATE, channel=CHANNEL_MEMORY,
            session_id=session_id, level=LEVEL_LOG,
            payload={"tokens": tokens, "latency_ms": latency_ms},
        ))

    def is_session_blocked(self, session_id: str | None) -> bool:
        """Consulté par le gateway en mode ACTIVE pour décider de couper le SSE."""
        return self.breaker.session_blocked(session_id)

    def snapshot_agents(self) -> list[dict[str, Any]]:
        return [a.snapshot() for a in self.agents.values()]

    def stats(self) -> dict[str, Any]:
        return {
            "agents": self.snapshot_agents(),
            "bus": self.bus.stats(),
            "breaker": {
                "active_mode": is_active(),
                "open_incidents": len(self.breaker.open_incidents()),
                "blocked_sessions": len(self.breaker._blocked_sessions),
            },
        }

    # ---------------- Persistence ----------------

    async def _log_guardrail(self, signal: Signal, *, agent_id: str,
                              level: int, detail: str | None) -> None:
        if level <= LEVEL_LOG and detail is None:
            return  # Niveau 0 silencieux
        try:
            await self.db.laurentia_guardrail_logs.insert_one({
                "incident_id": signal.incident_id,
                "session_id": signal.session_id,
                "agent_id": agent_id,
                "level": level,
                "channel": signal.channel,
                "detail": detail,
                "ts": signal.ts,
            })
        except Exception as e:
            logger.warning("orchestrator: guardrail_log persist failed: %s", e)

    async def _raise_critical(self, *, source_agent: str, signal: Signal,
                               reason: str, summary: str = "") -> None:
        """Enregistre l'incident, persiste, déclenche SMS, publie CHANNEL_CRITICAL."""
        rec = self.breaker.register_incident(
            incident_id=signal.incident_id,
            agent=source_agent,
            session_id=signal.session_id,
            reason=reason,
            summary=summary,
        )
        try:
            await self.db.laurentia_guardrail_logs.insert_one({
                "incident_id": signal.incident_id,
                "session_id": signal.session_id,
                "agent_id": source_agent,
                "level": LEVEL_CRITICAL,
                "channel": signal.channel,
                "detail": reason,
                "summary": summary,
                "circuit_breaker_active": is_active(),
                "ts": signal.ts,
            })
            await self.db.laurentia_orchestrator_incidents.insert_one(dict(rec))
        except Exception as e:
            logger.warning("orchestrator: critical persist failed: %s", e)
        # SMS asynchrone, best-effort
        self.bus.publish(Signal(
            type=SIGNAL_CRITICAL, channel=CHANNEL_CRITICAL,
            session_id=signal.session_id, source_agent=source_agent,
            incident_id=signal.incident_id, level=LEVEL_CRITICAL,
            payload={"reason": reason, "summary": summary},
        ))

    # ---------------- Handlers par agent (20) ----------------

    # ── Stratégique ──
    async def _h_souverainete(self, s: Signal) -> None:
        agent = self.agents["agent-souverainete"]
        text = s.payload.get("chunk") or s.payload.get("full_text") or ""
        breach = detect_souverainete_breach(text)
        if breach:
            agent.touch(s, status="red", detail=breach)
            await self._raise_critical(source_agent=agent.id, signal=s,
                                       reason="souverainete_breach", summary=breach)
        else:
            agent.touch(s, detail="ok")

    async def _h_memoire(self, s: Signal) -> None:
        agent = self.agents["agent-memoire"]
        agent.touch(s, detail=f"tokens={s.payload.get('tokens', 0)}")
        await self._log_guardrail(s, agent_id=agent.id, level=LEVEL_LOG, detail=None)

    async def _h_veille(self, s: Signal) -> None:
        self.agents["agent-veille"].touch(s, detail="intake")

    # ── Opérationnel ──
    async def _h_guardrail_text(self, s: Signal) -> None:
        agent = self.agents["agent-guardrail-text"]
        text = s.payload.get("input") or ""
        jb = detect_jailbreak(text)
        if jb:
            agent.touch(s, status="orange", detail=jb)
            await self._log_guardrail(s, agent_id=agent.id, level=LEVEL_CHECK, detail=jb)
        else:
            agent.touch(s, detail="ok")

    async def _h_guardrail_text_chunk(self, s: Signal) -> None:
        """Shadow validation côté flux — souverainete déjà couverte ; ici on flag jailbreak."""
        agent = self.agents["agent-guardrail-text"]
        chunk = s.payload.get("chunk") or ""
        jb = detect_jailbreak(chunk)
        if jb:
            agent.touch(s, status="orange", detail=jb)
            await self._log_guardrail(s, agent_id=agent.id, level=LEVEL_CHECK, detail=jb)

    async def _h_guardrail_image(self, s: Signal) -> None:
        self.agents["agent-guardrail-image"].touch(s, detail="passthrough")

    async def _h_guardrail_code(self, s: Signal) -> None:
        agent = self.agents["agent-guardrail-code"]
        text = (s.payload.get("input") or "").lower()
        if any(p in text for p in ("<script", "drop table", "; rm -rf", "os.system(", "subprocess.")):
            agent.touch(s, status="orange", detail="suspicious_pattern")
            await self._log_guardrail(s, agent_id=agent.id, level=LEVEL_CHECK, detail="suspicious_pattern")
        else:
            agent.touch(s, detail="ok")

    async def _h_streaming(self, s: Signal) -> None:
        self.agents["agent-streaming"].touch(s, detail=f"chunk_len={len(s.payload.get('chunk') or '')}")

    async def _h_latence(self, s: Signal) -> None:
        agent = self.agents["agent-latence"]
        lat = int(s.payload.get("latency_ms") or 0)
        status = "green" if lat < 3000 else ("orange" if lat < 8000 else "red")
        agent.touch(s, status=status, detail=f"latency={lat}ms")
        if status != "green":
            await self._log_guardrail(s, agent_id=agent.id, level=LEVEL_LOG, detail=f"latency_high:{lat}ms")

    async def _h_securite(self, s: Signal) -> None:
        self.agents["agent-securite"].touch(s, detail="intake")

    async def _h_sms_alert(self, s: Signal) -> None:
        """Émet le SMS OVH au Founder pour SIGNAL_CRITICAL."""
        agent = self.agents["agent-sms-alert"]
        source = s.source_agent or "unknown"
        summary = s.payload.get("summary") or s.payload.get("reason") or ""
        result = await sms_ovh.send_alert_sms(agent=source, incident_id=s.incident_id, summary=summary)
        agent.touch(s, status="green" if result.get("sent") else "orange",
                    detail=f"sms_sent={result.get('sent')}")
        try:
            await self.db.laurentia_guardrail_logs.insert_one({
                "incident_id": s.incident_id,
                "session_id": s.session_id,
                "agent_id": agent.id,
                "level": LEVEL_CRITICAL,
                "channel": s.channel,
                "detail": f"sms_dispatch:{result.get('reason') or 'sent'}",
                "sms_result": result,
                "ts": s.ts,
            })
        except Exception as e:
            logger.warning("orchestrator: sms log failed: %s", e)

    # ── Créatif (observateurs shadow, légers) ──
    async def _h_redaction(self, s: Signal) -> None:
        self.agents["agent-redaction"].touch(s, detail="observe")

    async def _h_visuel(self, s: Signal) -> None:
        self.agents["agent-visuel"].touch(s, detail="observe")

    async def _h_data(self, s: Signal) -> None:
        self.agents["agent-data"].touch(s, detail="observe")

    async def _h_recherche(self, s: Signal) -> None:
        self.agents["agent-recherche"].touch(s, detail="observe")

    async def _h_traduction(self, s: Signal) -> None:
        self.agents["agent-traduction"].touch(s, detail="observe")

    async def _h_social(self, s: Signal) -> None:
        self.agents["agent-social"].touch(s, detail="observe")

    # ── Interface ──
    async def _h_receptionniste(self, s: Signal) -> None:
        self.agents["agent-receptionniste"].touch(s, detail="qualified")

    async def _h_arbitre(self, s: Signal) -> None:
        self.agents["agent-arbitre"].touch(s, detail="arbitrage_observed")

    async def _h_rapporteur(self, s: Signal) -> None:
        self.agents["agent-rapporteur"].touch(s, detail="archived")

    async def _h_auto_maintenance(self, s: Signal) -> None:
        # Si un agent affiche red plus de N signaux → marquer pour intervention
        agent = self.agents["agent-auto-maintenance"]
        red_agents = [a.id for a in self.agents.values() if a.status == "red"]
        agent.touch(s, status="orange" if red_agents else "green",
                    detail=f"red_count={len(red_agents)}")


def make_orchestrator(db: AsyncIOMotorDatabase) -> Orchestrator:
    return Orchestrator(db)
