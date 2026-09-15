"""
test_cvln_runtime.py — PATCH-007 estate runtime surface.

These tests execute the real production modules:
  * routes/cvln_runtime.py      (capabilities / identity / state / routing / events)
  * services/cvln_contracts.py  (Event, Capability, SystemState v1.0)
  * services/cvln_model_router.py  (Laurentia -> Agent Factory)
  * services/cvln_events.py        (Laurentia -> Meta CVLN)

The two cross-system clients are exercised over REAL HTTP against stub servers
that implement the contracts Agent Factory and Meta CVLN are expected to serve,
so the round trip is genuinely executed rather than mocked at the function
boundary.

They do not boot the full Laurentia app: that needs MongoDB and the proprietary
`emergentintegrations` wheel. The runtime surface itself has neither dependency,
which is why it can be proven here.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from routes.cvln_runtime import router as cvln_runtime_router
from services import cvln_events, cvln_model_router
from services.cvln_contracts import Capability, Event, SystemState, new_trace_id


# --------------------------------------------------------------------------
# App under test: the real router + the real trace_id middleware from server.py
# --------------------------------------------------------------------------
def _build_app() -> FastAPI:
    from services.cvln_contracts import new_trace_id as _new_trace_id

    app = FastAPI()

    @app.middleware("http")
    async def _trace(request: Request, call_next):
        trace_id = request.headers.get("X-CVLN-Trace-Id") or _new_trace_id()
        request.state.cvln_trace_id = trace_id
        response = await call_next(request)
        response.headers["X-CVLN-Trace-Id"] = trace_id
        return response

    app.include_router(cvln_runtime_router)
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_build_app())


# --------------------------------------------------------------------------
# Stub servers (real HTTP, ephemeral ports)
# --------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(app: FastAPI, port: int):
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            return server
        time.sleep(0.05)
    raise RuntimeError("stub server did not start")


@pytest.fixture(scope="module")
def agent_factory_stub():
    """Implements the contract Agent Factory must expose: POST /api/providers/route.

    The response shape mirrors what `provider_layer.routed_generate()` already
    returns in the audited Agent Factory repo.
    """
    app = FastAPI()
    seen = {}

    @app.post("/api/providers/route")
    async def route(body: dict, request: Request):
        seen["trace_header"] = request.headers.get("X-CVLN-Trace-Id")
        seen["authorization"] = request.headers.get("Authorization")
        seen["body"] = body
        return {
            "text": f"[sovereign] {body['prompt'][::-1]}",
            "provider": "sovereign",
            "model": "cvln-internal-deterministic",
            "strategy": "sovereign_only",
            "latency_ms": 7,
        }

    port = _free_port()
    server = _serve(app, port)
    yield {"url": f"http://127.0.0.1:{port}", "seen": seen}
    server.should_exit = True


@pytest.fixture(scope="module")
def meta_cvln_stub():
    """Implements Meta CVLN's signed bus contract: POST /api/events/emit."""
    app = FastAPI()
    received = []

    @app.post("/api/events/emit")
    async def emit(body: dict, request: Request):
        received.append({"body": body, "auth": request.headers.get("Authorization")})
        return {**body, "signed": True, "signature_b64": "stub", "public_key_b64": "stub"}

    port = _free_port()
    server = _serve(app, port)
    yield {"url": f"http://127.0.0.1:{port}", "received": received}
    server.should_exit = True


# --------------------------------------------------------------------------
# Capability discovery — the contract Meta CVLN's prober enforces
# --------------------------------------------------------------------------
def test_capabilities_returns_a_bare_json_array(client):
    """Meta CVLN marks a repo HEALTHY only when this is a list (discover_all)."""
    resp = client.get("/api/capabilities")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list), "must be a bare array, a dict is recorded DEGRADED"
    assert len(body) >= 1


def test_every_advertised_capability_validates_against_contract_v1_0(client):
    for raw in client.get("/api/capabilities").json():
        cap = Capability(**raw)
        assert cap.contract == "capability"
        assert cap.version == "1.0"
        assert cap.entity_id == "laurentia"
        assert cap.id.startswith("cap-laurentia-")


def test_capabilities_publish_their_http_binding(client):
    """CONN-001: the concrete route is published, not guessed by the caller."""
    caps = {c["name"]: c for c in client.get("/api/capabilities").json()}
    briefing = caps["laurentia.briefing"]
    assert briefing["input_schema"]["x-cvln-method"] == "POST"
    assert briefing["input_schema"]["x-cvln-path"] == "/api/laurentia/query"


def test_capabilities_is_public(client):
    """Baseline specs this route public (api-contracts/LAURENTIA-API.md)."""
    assert client.get("/api/capabilities").status_code == 200


# --------------------------------------------------------------------------
# System identity / state
# --------------------------------------------------------------------------
def test_system_identity_declares_entity_layer_and_authority(client):
    body = client.get("/api/system/identity").json()
    assert body["entity_id"] == "laurentia"
    assert body["layer"] == "Layer 3"
    assert body["authority"] == "meta-cvln-os"
    assert "event@1.0" in body["contracts"]
    assert body["authenticated"] is False


def test_system_identity_reports_authentication_when_presented(client):
    body = client.get("/api/system/identity", headers={"Authorization": "Bearer x"}).json()
    assert body["authenticated"] is True


def test_system_state_validates_against_contract_v1_0(client):
    state = SystemState(**client.get("/api/system/state").json())
    assert state.contract == "system_state"
    assert state.entity_id == "laurentia"
    assert state.mode in {"normal", "degraded", "critical", "offline"}


# --------------------------------------------------------------------------
# trace_id
# --------------------------------------------------------------------------
def test_trace_id_is_generated_and_echoed(client):
    resp = client.get("/api/system/identity")
    assert resp.headers["X-CVLN-Trace-Id"].startswith("trc-")
    assert resp.json()["trace_id"] == resp.headers["X-CVLN-Trace-Id"]


def test_caller_supplied_trace_id_is_honoured(client):
    trace = new_trace_id()
    resp = client.get("/api/system/identity", headers={"X-CVLN-Trace-Id": trace})
    assert resp.headers["X-CVLN-Trace-Id"] == trace
    assert resp.json()["trace_id"] == trace


# --------------------------------------------------------------------------
# Laurentia -> Agent Factory Model Router (real HTTP)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_model_router_round_trip_over_real_http(agent_factory_stub, monkeypatch):
    monkeypatch.setattr(cvln_model_router, "ROUTER_URL", agent_factory_stub["url"])
    monkeypatch.setattr(cvln_model_router, "ROUTER_TOKEN", "svc-token")

    trace = new_trace_id()
    result = await cvln_model_router.route_generate(
        system="Tu es CVLN.", prompt="bonjour", session_id="sess-1", trace_id=trace
    )

    assert result["ok"] is True
    assert result["text"] == "[sovereign] ruojnob"
    assert result["provider"] == "sovereign"
    assert result["trace_id"] == trace

    # trace_id and service auth actually crossed the wire
    assert agent_factory_stub["seen"]["trace_header"] == trace
    assert agent_factory_stub["seen"]["authorization"] == "Bearer svc-token"
    assert agent_factory_stub["seen"]["body"]["session_id"] == "sess-1"

    # a RoutingDecision v1.0 is produced for the estate
    routing = result["routing"]
    assert routing["contract"] == "routing_decision"
    assert routing["selected_entity_id"] == "cvln-agent-factory"
    assert routing["trace_id"] == trace


@pytest.mark.asyncio
async def test_model_router_reports_not_configured_instead_of_pretending(monkeypatch):
    monkeypatch.setattr(cvln_model_router, "ROUTER_URL", "")
    result = await cvln_model_router.route_generate("s", "p", "sess")
    assert result["ok"] is False
    assert result["reason"] == "not_configured:CVLN_MODEL_ROUTER_URL"
    assert result["text"] is None


@pytest.mark.asyncio
async def test_model_router_failure_is_recorded_not_raised(monkeypatch):
    monkeypatch.setattr(cvln_model_router, "ROUTER_URL", f"http://127.0.0.1:{_free_port()}")
    result = await cvln_model_router.route_generate("s", "p", "sess")
    assert result["ok"] is False
    assert result["reason"].startswith("unreachable:")


# --------------------------------------------------------------------------
# Laurentia -> Meta CVLN events (real HTTP)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_event_delivered_to_meta_cvln_over_real_http(meta_cvln_stub, monkeypatch):
    cvln_events._reset_journal_for_tests()
    monkeypatch.setattr(cvln_events, "META_URL", meta_cvln_stub["url"])
    monkeypatch.setattr(cvln_events, "META_TOKEN", "svc-token")

    trace = new_trace_id()
    result = await cvln_events.emit_type(
        "laurentia.query.completed", {"chars": 42}, trace_id=trace, subject_type="session"
    )

    assert result["status"] == "delivered"
    assert result["http"] == 200

    delivered = meta_cvln_stub["received"][-1]
    assert delivered["auth"] == "Bearer svc-token"
    event = Event(**delivered["body"])
    assert event.contract == "event"
    assert event.version == "1.0"
    assert event.type == "laurentia.query.completed"
    assert event.source_system == "laurentia"
    assert event.trace_id == trace


@pytest.mark.asyncio
async def test_event_emission_is_skipped_not_faked_when_unconfigured(monkeypatch):
    cvln_events._reset_journal_for_tests()
    monkeypatch.setattr(cvln_events, "META_URL", "")
    result = await cvln_events.emit_type("laurentia.test", {})
    assert result["status"] == "skipped"
    assert cvln_events.journal_stats()["configured"] is False


@pytest.mark.asyncio
async def test_event_journal_gives_local_observability(meta_cvln_stub, monkeypatch):
    cvln_events._reset_journal_for_tests()
    monkeypatch.setattr(cvln_events, "META_URL", meta_cvln_stub["url"])
    trace = new_trace_id()
    await cvln_events.emit_type("laurentia.query.received", {}, trace_id=trace)
    await cvln_events.emit_type("laurentia.query.completed", {}, trace_id=trace)

    recent = cvln_events.recent_events()
    assert len(recent) == 2
    assert {e["type"] for e in recent} == {
        "laurentia.query.received",
        "laurentia.query.completed",
    }
    assert all(e["trace_id"] == trace for e in recent), "one trace spans the exchange"
    assert cvln_events.journal_stats()["by_status"]["delivered"] == 2


def test_recent_events_endpoint_exposes_the_journal(client):
    body = client.get("/api/system/events/recent").json()
    assert "stats" in body and "events" in body
    assert isinstance(body["events"], list)


def test_routing_endpoint_reports_wiring_and_fallback_reason(client):
    body = client.get("/api/system/routing").json()
    assert "configured" in body
    assert body["contradictions"] == ["C-004", "C-006"]
