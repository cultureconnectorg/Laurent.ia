"""
cvln_identity.py — Laurentia's system identity and capability catalogue.

Answers two of the estate's runtime questions (PATCH-007):
  * WHO am I?   -> system_identity()   (entity_id, layer, contracts spoken)
  * WHAT can I do? -> capability_catalogue() -> list[Capability v1.0]

The catalogue is advertised at `GET /api/capabilities` as a JSON **array**,
which is exactly what Meta CVLN's prober requires: `registry/discover-all`
marks a repo HEALTHY only when that route returns `< 400` AND
`isinstance(data, list)` (see MetaCVLN `backend/server.py::discover_all`).
Anything else is recorded DEGRADED — the state all twelve estate repos were
in at the v1.0 audit (gap G-002, contradiction C-005).

Every capability below maps to a route that ALREADY EXISTS in this repo.
Nothing is advertised that Laurentia cannot serve.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from services.cvln_contracts import Capability, ENTITY_ID, SystemState, now_iso

# Laurentia's declared position in the estate. Layer 3 per the CVLN
# Intelligence OS baseline (registry/ECOSYSTEM-REGISTRY.md row "Laurentia").
LAYER = "Layer 3"
ROLE = "Cultural industry operator"
SERVICE_VERSION = os.environ.get("LAURENTIA_VERSION", "v1.2-PRODUCTION")

# Contracts this system speaks on the wire, owned by Meta CVLN.
CONTRACTS_SPOKEN = ["event@1.0", "capability@1.0", "routing_decision@1.0", "system_state@1.0"]


def _endpoint(method: str, path: str) -> Dict[str, str]:
    """HTTP binding published inside the JSON-schema block.

    The Capability contract carries no endpoint field, so the binding rides in
    `x-cvln-endpoint` — additive, and readable by any consumer that wants the
    concrete route instead of guessing it. This is the Laurentia-side answer to
    CONN-001 (Meta CVLN calls `/adapters/laurentia/briefing`; Laurentia's real
    surface is published here).
    """
    return {"x-cvln-method": method, "x-cvln-path": path}


def capability_catalogue() -> List[Capability]:
    """The capabilities Laurentia advertises to the estate."""
    return [
        Capability(
            id="cap-laurentia-query",
            name="laurentia.query",
            input_schema={
                "type": "object",
                "required": ["message"],
                "properties": {
                    "message": {"type": "string"},
                    "session_id": {"type": "string"},
                },
                **_endpoint("POST", "/api/laurentia/query"),
            },
            output_schema={
                "type": "object",
                "description": "SSE token stream; terminal frame carries session_id.",
                "properties": {"token": {"type": "string"}, "done": {"type": "boolean"}},
            },
            allowed_actors=["api_key", "admin", "ops_lead"],
            p95_latency_ms=None,
            idempotent=False,
            rollback_supported=False,
        ),
        Capability(
            id="cap-laurentia-briefing",
            name="laurentia.briefing",
            input_schema={
                "type": "object",
                "required": ["topic"],
                "properties": {
                    "topic": {"type": "string"},
                    "session_id": {"type": "string"},
                },
                **_endpoint("POST", "/api/laurentia/query"),
            },
            output_schema={
                "type": "object",
                "description": "Briefing text produced through the estate model router when configured.",
                "properties": {"text": {"type": "string"}, "trace_id": {"type": "string"}},
            },
            allowed_actors=["admin", "ops_lead", "cfo"],
            idempotent=False,
        ),
        Capability(
            id="cap-laurentia-report",
            name="laurentia.report",
            input_schema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                **_endpoint("POST", "/api/reports"),
            },
            output_schema={"type": "object", "properties": {"report_id": {"type": "string"}}},
            allowed_actors=["admin", "ops_lead"],
            idempotent=False,
        ),
        Capability(
            id="cap-laurentia-pdf-export",
            name="laurentia.pdf_export",
            input_schema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                **_endpoint("POST", "/api/pdf/export"),
            },
            output_schema={
                "type": "object",
                "description": "Signed PDF with QR; quota-tiered.",
                "properties": {"url": {"type": "string"}},
            },
            allowed_actors=["admin", "ops_lead"],
            idempotent=True,
            rollback_supported=False,
        ),
    ]


def system_identity() -> Dict[str, Any]:
    """WHO Laurentia is, for the estate's registry and supervision surfaces."""
    return {
        "contract": "system_identity",
        "version": "1.0",
        "entity_id": ENTITY_ID,
        "name": "Laurentia",
        "layer": LAYER,
        "role": ROLE,
        "service_version": SERVICE_VERSION,
        "repository": "cultureconnectorg/Laurent.ia",
        "contracts": CONTRACTS_SPOKEN,
        "capabilities_endpoint": "/api/capabilities",
        "health_endpoint": "/api/health",
        "state_endpoint": "/api/system/state",
        "authority": "meta-cvln-os",
        "observed_at": now_iso(),
    }


def system_state(mode: str = "normal", health: str = "green") -> SystemState:
    """Laurentia's own SystemState v1.0 report."""
    return SystemState(mode=mode, health=health, active_incidents=0)
