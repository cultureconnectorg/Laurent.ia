"""
cvln_runtime.py — Laurentia's estate runtime surface (PATCH-007).

Four read-only routes that let the CVLN estate see and address Laurentia as a
system rather than as an opaque URL:

    GET /api/capabilities      -> JSON ARRAY of Capability v1.0  (discovery)
    GET /api/system/identity   -> who Laurentia is
    GET /api/system/state      -> SystemState v1.0
    GET /api/system/routing    -> model-router wiring + last fallback reason
    GET /api/system/events/recent -> local emission journal (observability)

`GET /api/capabilities` is deliberately PUBLIC and deliberately returns a bare
JSON array. Both are contract requirements, not style choices:
  * the CVLN Intelligence OS baseline specs it public
    (`api-contracts/LAURENTIA-API.md`, row `/api/capabilities`, gap G-002);
  * Meta CVLN's prober marks a repo HEALTHY only when the response is
    `< 400` and `isinstance(data, list)` — a dict would be recorded DEGRADED
    (`MetaCVLN backend/server.py::discover_all`).

Authorisation headers sent by the prober (`Authorization: Bearer ...` or
`X-API-Key: ...`) are accepted and echoed back as `authenticated` in the
identity route, but are not required to read capability metadata.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Request

from services import cvl_brain, cvln_events, cvln_identity, cvln_model_router

router = APIRouter(prefix="/api", tags=["cvln-runtime"])


@router.get("/capabilities")
async def list_capabilities() -> List[Dict[str, Any]]:
    """Capability advertisement — MUST stay a bare JSON array (see module docstring)."""
    return [cap.model_dump() for cap in cvln_identity.capability_catalogue()]


@router.get("/system/identity")
async def get_identity(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    identity = cvln_identity.system_identity()
    identity["authenticated"] = bool(authorization or x_api_key)
    identity["trace_id"] = getattr(request.state, "cvln_trace_id", None)
    return identity


@router.get("/system/state")
async def get_state() -> Dict[str, Any]:
    """SystemState v1.0 — Laurentia's own view of its health."""
    return cvln_identity.system_state().model_dump()


@router.get("/system/routing")
async def get_routing() -> Dict[str, Any]:
    """Is Laurentia deferring model choice to the estate router, or falling back?"""
    status = cvln_model_router.status()
    status["last_fallback_reason"] = cvl_brain.last_fallback_reason()
    return status


@router.get("/system/events/recent")
async def get_recent_events(limit: int = 50) -> Dict[str, Any]:
    """Local observability of estate event emission — what left, and did it land."""
    return {
        "stats": cvln_events.journal_stats(),
        "events": cvln_events.recent_events(limit=limit),
    }
