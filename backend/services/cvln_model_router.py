"""
cvln_model_router.py — Laurentia -> CVLN Agent Factory Model Router client.

WHY THIS EXISTS (PATCH-007, contradictions C-004 and C-006):
Agent Factory's doctrine article DOC-ARC-04 says no hardcoded provider
dependency may exist outside its provider layer, and `backend/provider_layer.py`
states the same rule ("Aucun appel direct provider hors de cette couche,
ADR-002"). Laurentia violated it: `services/cvl_brain.py` called
`.with_model("anthropic", <hardcoded model>)` directly. This client is the
compliant path — when the estate router is configured, Laurentia asks Agent
Factory to choose the provider instead of choosing one itself.

CONTRACT EXPECTED OF AGENT FACTORY
    POST {CVLN_MODEL_ROUTER_URL}/api/providers/route
    body : {"system": str, "prompt": str, "session_id": str, "trace_id": str}
    200  : {"text": str, "provider": str, "model": str,
            "strategy": str, "latency_ms": int}

That response shape is exactly what Agent Factory's own
`provider_layer.routed_generate()` already returns. What does NOT exist yet in
the audited Agent Factory repo is a *service-callable* HTTP route for it:
`routed_generate` is reachable only through `POST /api/providers/test`, which
is admin-gated and truncates output to 500 characters — a test affordance, not
a production entry point. Shipping `/api/providers/route` is Agent Factory-side
work and stays OPEN in the estate's connection registry until it lands.

Until then `is_configured()` is False and callers fall back to their local
path, with the reason recorded — never silently.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from services.cvln_contracts import RoutingDecision, new_event_id, new_trace_id

ROUTER_URL = os.environ.get("CVLN_MODEL_ROUTER_URL", "").rstrip("/")
ROUTER_TOKEN = os.environ.get("CVLN_MODEL_ROUTER_TOKEN", "")
ROUTER_TIMEOUT_S = float(os.environ.get("CVLN_MODEL_ROUTER_TIMEOUT_S", "45.0"))
ROUTE_PATH = "/api/providers/route"


def is_configured() -> bool:
    """True when Laurentia has an estate model router to defer to."""
    return bool(ROUTER_URL)


def status() -> Dict[str, Any]:
    return {
        "configured": is_configured(),
        "url": f"{ROUTER_URL}{ROUTE_PATH}" if ROUTER_URL else None,
        "authenticated": bool(ROUTER_TOKEN),
        "fallback": "local provider path in services/cvl_brain.py",
        "contradictions": ["C-004", "C-006"],
    }


async def route_generate(
    system: str,
    prompt: str,
    session_id: str,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ask Agent Factory's Model Router to generate. Never raises.

    Returns {"ok": bool, "text": str|None, "routing": dict|None, "reason": str|None}.
    """
    trace_id = trace_id or new_trace_id()

    if not is_configured():
        return {
            "ok": False,
            "text": None,
            "routing": None,
            "trace_id": trace_id,
            "reason": "not_configured:CVLN_MODEL_ROUTER_URL",
        }

    headers = {"Content-Type": "application/json", "X-CVLN-Trace-Id": trace_id}
    if ROUTER_TOKEN:
        headers["Authorization"] = f"Bearer {ROUTER_TOKEN}"

    body = {"system": system, "prompt": prompt, "session_id": session_id, "trace_id": trace_id}

    try:
        async with httpx.AsyncClient(timeout=ROUTER_TIMEOUT_S) as client:
            resp = await client.post(f"{ROUTER_URL}{ROUTE_PATH}", json=body, headers=headers)
    except Exception as exc:
        return {
            "ok": False,
            "text": None,
            "routing": None,
            "trace_id": trace_id,
            "reason": f"unreachable:{type(exc).__name__}",
        }

    if resp.status_code >= 400:
        return {
            "ok": False,
            "text": None,
            "routing": None,
            "trace_id": trace_id,
            "reason": f"http_{resp.status_code}",
        }

    try:
        data = resp.json()
    except Exception:
        return {"ok": False, "text": None, "routing": None, "trace_id": trace_id, "reason": "bad_json"}

    text = data.get("text")
    if not isinstance(text, str):
        return {"ok": False, "text": None, "routing": None, "trace_id": trace_id, "reason": "no_text_field"}

    decision = RoutingDecision(
        trace_id=trace_id,
        event_id=new_event_id(),
        strategy="direct",
        selected_capability_id="cap-agent-factory-model-route",
        selected_entity_id="cvln-agent-factory",
        reason=f"estate model router: strategy={data.get('strategy')} provider={data.get('provider')}",
        confidence=1.0,
        candidates=[{"provider": data.get("provider"), "model": data.get("model"),
                     "latency_ms": data.get("latency_ms")}],
    )

    return {
        "ok": True,
        "text": text,
        "routing": decision.model_dump(),
        "trace_id": trace_id,
        "reason": None,
        "provider": data.get("provider"),
        "model": data.get("model"),
        "strategy": data.get("strategy"),
        "latency_ms": data.get("latency_ms"),
    }
