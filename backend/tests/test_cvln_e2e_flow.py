"""
test_cvln_e2e_flow.py — PATCH-007 end-to-end runtime flow.

Executes the full exchange the estate is meant to perform, with ONE trace_id
followed from end to end:

    Laurentia  (services/cvl_brain.chat_enriched_traced)
      -> CVLN Agent Factory  (Model Router: provider selection + sovereign result)
      -> back to Laurentia   (text + RoutingDecision v1.0)
      -> Event v1.0 emitted  (laurentia.query.completed, same trace_id)
      -> Meta CVLN           (signed bus /api/events/emit)
      -> supervision         (the authority layer can read the flow back)

WHAT IS REAL HERE
  * Every Laurentia-side module is the production module, executed for real:
    cvl_brain, cvln_model_router, cvln_events, cvln_contracts.
  * The calls are real HTTP over ephemeral ports, not patched functions.
  * The trace_id continuity is asserted, not assumed.

WHAT IS A STUB, AND WHY
  * Agent Factory's `POST /api/providers/route` and Meta CVLN's service-callable
    `/api/events/emit` do not exist yet in their audited repositories — shipping
    them is the work of the Agent Factory and Meta CVLN sessions. The stubs here
    implement exactly the contracts those sessions must satisfy, so the day they
    land, this same test points at the real services by changing two env vars.
  * No LLM provider is called: the Model Router's deterministic `sovereign`
    provider needs no API key, which is what makes this flow reproducible.

This test therefore proves the Laurentia side of the chain, and specifies the
other two. It does not claim the estate flow is live end to end.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI, Request

from services import cvl_brain, cvln_events, cvln_model_router
from services.cvln_contracts import Event, new_trace_id


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(app: FastAPI, port: int):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            return server
        time.sleep(0.05)
    raise RuntimeError("stub did not start")


@pytest.fixture(scope="module")
def estate():
    """Agent Factory + Meta CVLN, serving the contracts PATCH-007 defines."""
    # --- CVLN Agent Factory: Model Router -------------------------------
    af = FastAPI()
    af_calls = []

    @af.post("/api/providers/route")
    async def route(body: dict, request: Request):
        af_calls.append({"body": body, "trace": request.headers.get("X-CVLN-Trace-Id")})
        # Mirrors provider_layer.routed_generate()'s real return shape.
        # 'sovereign' is Agent Factory's deterministic, keyless terminal provider.
        return {
            "text": f"Briefing: {body['prompt'].upper()}",
            "provider": "sovereign",
            "model": "cvln-internal-deterministic",
            "strategy": "sovereign_only",
            "latency_ms": 5,
        }

    # --- Meta CVLN: signed event bus + supervision read -----------------
    meta = FastAPI()
    meta_bus = []

    @meta.post("/api/events/emit")
    async def emit(body: dict, request: Request):
        stored = {**body, "signed": True, "signature_b64": "stub-sig", "key_id": "did:cvln:notary#1"}
        meta_bus.append(stored)
        return stored

    @meta.get("/api/events")
    async def events(trace_id: str | None = None):
        """Supervision surface: the authority layer reads the flow back."""
        if trace_id:
            return [e for e in meta_bus if e.get("trace_id") == trace_id]
        return meta_bus

    af_port, meta_port = _free_port(), _free_port()
    af_server, meta_server = _serve(af, af_port), _serve(meta, meta_port)
    yield {
        "af_url": f"http://127.0.0.1:{af_port}",
        "meta_url": f"http://127.0.0.1:{meta_port}",
        "af_calls": af_calls,
        "meta_bus": meta_bus,
    }
    af_server.should_exit = True
    meta_server.should_exit = True


@pytest.mark.asyncio
async def test_end_to_end_flow_carries_one_trace_across_the_estate(estate, monkeypatch):
    import httpx

    cvln_events._reset_journal_for_tests()
    monkeypatch.setattr(cvln_model_router, "ROUTER_URL", estate["af_url"])
    monkeypatch.setattr(cvln_model_router, "ROUTER_TOKEN", "svc-laurentia")
    monkeypatch.setattr(cvln_events, "META_URL", estate["meta_url"])
    monkeypatch.setattr(cvln_events, "META_TOKEN", "svc-laurentia")

    trace = new_trace_id()

    # 1) Laurentia receives the request and announces it on the estate bus.
    await cvln_events.emit_type(
        "laurentia.query.received", {"topic": "Q1 review"}, trace_id=trace, subject_type="session"
    )

    # 2) Laurentia asks Agent Factory's Model Router to generate — it does NOT
    #    pick a provider itself (contradictions C-004 / C-006).
    result = await cvl_brain.chat_enriched_traced(
        user_text="Q1 review", system_message="Tu es CVLN.", session_id="sess-e2e", trace_id=trace
    )

    assert result["routed"] is True, "must go through the estate router, not the local path"
    assert result["text"] == "Briefing: Q1 REVIEW"
    assert result["trace_id"] == trace
    assert cvl_brain.last_fallback_reason() is None

    # The routing decision is a RoutingDecision v1.0 naming Agent Factory.
    routing = result["routing"]
    assert routing["contract"] == "routing_decision"
    assert routing["selected_entity_id"] == "cvln-agent-factory"
    assert routing["trace_id"] == trace

    # Agent Factory really was called, with the trace and service credential.
    assert len(estate["af_calls"]) == 1
    assert estate["af_calls"][0]["trace"] == trace

    # 3) Laurentia reports completion on the estate bus, same trace.
    emitted = await cvln_events.emit_type(
        "laurentia.query.completed",
        {"provider": routing["candidates"][0]["provider"], "chars": len(result["text"])},
        trace_id=trace,
        subject_type="session",
        subject_id="sess-e2e",
    )
    assert emitted["status"] == "delivered"

    # 4) Meta CVLN can supervise the whole exchange from its own surface.
    async with httpx.AsyncClient(timeout=5.0) as http:
        seen = (await http.get(f"{estate['meta_url']}/api/events", params={"trace_id": trace})).json()

    assert len(seen) == 2, "both ends of the exchange reached the authority layer"
    types = [e["type"] for e in seen]
    assert types == ["laurentia.query.received", "laurentia.query.completed"]
    for raw in seen:
        event = Event(**{k: v for k, v in raw.items() if k != "key_id"})
        assert event.trace_id == trace
        assert event.source_system == "laurentia"
        assert event.version == "1.0"

    # 5) Laurentia's own observability journal agrees with what the estate saw.
    journal = cvln_events.recent_events()
    assert len(journal) == 2
    assert all(entry["trace_id"] == trace for entry in journal)
    assert cvln_events.journal_stats()["by_status"]["delivered"] == 2


@pytest.mark.asyncio
async def test_flow_degrades_honestly_when_agent_factory_is_absent(estate, monkeypatch):
    """With no Model Router configured, Laurentia records why it fell back —
    it never silently pretends the estate path was used."""
    cvln_events._reset_journal_for_tests()
    monkeypatch.setattr(cvln_model_router, "ROUTER_URL", "")
    monkeypatch.setattr(cvln_events, "META_URL", estate["meta_url"])

    trace = new_trace_id()
    routed = await cvln_model_router.route_generate("s", "p", "sess-x", trace_id=trace)

    assert routed["ok"] is False
    assert routed["reason"] == "not_configured:CVLN_MODEL_ROUTER_URL"

    # The degradation itself is observable on the estate bus.
    emitted = await cvln_events.emit_type(
        "laurentia.routing.degraded", {"reason": routed["reason"]}, trace_id=trace, priority=2
    )
    assert emitted["status"] == "delivered"
    assert emitted["trace_id"] == trace
