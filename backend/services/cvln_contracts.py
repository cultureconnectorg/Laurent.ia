"""
cvln_contracts.py — CVLN estate wire contracts, Laurentia-side implementation.

SOURCE OF TRUTH: these shapes are defined and owned by Meta CVLN
(`metacvln-spec/MetaCVLN`, `backend/contracts.py`, contracts v1.0 —
Event, Capability, RoutingDecision, SystemState, ExecutionPlan).

This module deliberately RE-IMPLEMENTS the wire shapes rather than importing
Meta CVLN's code: Laurentia stays an independent system and absorbs no code
from the authority layer. Only the *wire format* is shared. If Meta CVLN
versions a contract, this file follows by adding a new version — it never
redefines v1.0 unilaterally.

Ref: CVLN Intelligence OS baseline, api-contracts/EVENTS.md, PATCH-007.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ENTITY_ID = "laurentia"
SOURCE_SYSTEM = "laurentia"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_trace_id() -> str:
    """Trace id, `trc-` prefixed — matches Meta CVLN's own contract examples."""
    return f"trc-{uuid.uuid4().hex[:16]}"


def new_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:16]}"


def new_routing_id() -> str:
    return f"rd-{uuid.uuid4().hex[:16]}"


class Event(BaseModel):
    """Event v1.0 — wire-compatible with Meta CVLN `contracts.py::Event`."""

    contract: Literal["event"] = "event"
    version: Literal["1.0"] = "1.0"
    id: str = Field(default_factory=new_event_id)
    trace_id: str
    type: str = Field(..., description="dot.namespaced, e.g. laurentia.query.completed")
    source_system: str = SOURCE_SYSTEM
    subject_type: Optional[str] = None
    subject_id: Optional[str] = None
    actor: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(3, ge=1, le=5)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    signed: bool = False
    signature_b64: Optional[str] = None
    public_key_b64: Optional[str] = None
    timestamp: str = Field(default_factory=now_iso)


class Capability(BaseModel):
    """Capability v1.0 — wire-compatible with Meta CVLN `contracts.py::Capability`."""

    contract: Literal["capability"] = "capability"
    version: Literal["1.0"] = "1.0"
    id: str
    name: str
    entity_id: str = ENTITY_ID
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    allowed_actors: List[str] = Field(default_factory=list)
    prohibited_actors: List[str] = Field(default_factory=list)
    requires_approval_by: Optional[str] = None
    escalation_to: Optional[str] = None
    p95_latency_ms: Optional[int] = None
    cost_eur: Optional[float] = None
    idempotent: bool = True
    rollback_supported: bool = False
    health: Literal["green", "amber", "red"] = "green"


class RoutingDecision(BaseModel):
    """RoutingDecision v1.0 — wire-compatible with Meta CVLN `contracts.py`."""

    contract: Literal["routing_decision"] = "routing_decision"
    version: Literal["1.0"] = "1.0"
    id: str = Field(default_factory=new_routing_id)
    trace_id: str
    event_id: str
    strategy: Literal["direct", "parallel", "fallback", "degraded"] = "direct"
    selected_capability_id: str
    selected_entity_id: str
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    reason: str
    confidence: float = Field(0.9, ge=0.0, le=1.0)
    decided_at: str = Field(default_factory=now_iso)


class SystemState(BaseModel):
    """SystemState v1.0 — wire-compatible with Meta CVLN `contracts.py`."""

    contract: Literal["system_state"] = "system_state"
    version: Literal["1.0"] = "1.0"
    entity_id: str = ENTITY_ID
    mode: Literal["normal", "degraded", "critical", "offline"] = "normal"
    health: Literal["green", "amber", "red"] = "green"
    uptime_pct_7d: Optional[float] = None
    p95_latency_ms: Optional[int] = None
    error_rate: Optional[float] = None
    active_incidents: int = 0
    last_notarized_at: Optional[str] = None
    last_notarization_did: Optional[str] = None
    observed_at: str = Field(default_factory=now_iso)
