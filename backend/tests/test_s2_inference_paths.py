"""S2.3 to S2.5 — every inference path goes to the sovereign engine, fails visibly
without it, and no provider SDK is reachable (T1, T3).

The engine is the deterministic local engine (a real HTTP server). The autouse
network guard (conftest.py) fails any test that tries to leave loopback.
"""
import ast
import asyncio
import os
import pathlib
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pymongo import MongoClient

from _harness.fake_engine import FIXED_ANSWER, FakeEngine
from services import cvl_brain

BACKEND = pathlib.Path(__file__).resolve().parents[1]
MARKER = "S2-PATH-MARKER"


@pytest.fixture
def client(app_client):
    return app_client


@pytest.fixture
def engine(monkeypatch):
    with FakeEngine() as e:
        monkeypatch.setenv("BRAIN_ENGINE_URL", e.url)
        monkeypatch.setenv("BRAIN_ENGINE_MODEL", "fake-deterministic")
        yield e


@pytest.fixture
def engine_down(monkeypatch):
    # Loopback port with nothing listening: the engine is unreachable.
    monkeypatch.setenv("BRAIN_ENGINE_URL", "http://127.0.0.1:9")


@pytest.fixture
def bearer():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    user_id, token = f"user-s2-{uuid.uuid4().hex[:8]}", f"sess_s2_{uuid.uuid4().hex}"
    db.users.insert_one({"user_id": user_id, "email": f"{user_id}@test.local"})
    db.user_sessions.insert_one({"session_token": token, "user_id": user_id,
                                 "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)})
    yield {"Authorization": f"Bearer {token}"}
    db.user_sessions.delete_one({"session_token": token})
    db.users.delete_one({"user_id": user_id})


@pytest.fixture
def service_key(monkeypatch):
    monkeypatch.setenv("LAURENTIA_CVLN_SERVICE_API_KEY", "s2-test-service-key")
    return {"X-API-Key": "s2-test-service-key"}


def _sse_events(text: str) -> list[str]:
    return [line[len("event: "):] for line in text.splitlines() if line.startswith("event: ")]


def _engine_saw_marker(engine) -> bool:
    return any(MARKER in m.get("content", "") for c in engine.calls for m in c["messages"])


# ---------- P1 to P6: each path reaches the sovereign engine ----------

def _fresh_instance(client) -> str:
    # Own identifier per test: the query route rate-limits per identity.
    frek_id = f"DEMO-S2-{uuid.uuid4().hex[:8].upper()}"
    assert client.post("/api/laurentia/instances/init", json={"frek_id": frek_id}).status_code == 200
    return frek_id


def test_p1_query_streams_from_the_sovereign_engine(client, engine):
    frek_id = _fresh_instance(client)
    r = client.post("/api/laurentia/query", json={"frek_id": frek_id, "input": f"Bonjour {MARKER}"})
    assert r.status_code == 200
    assert "done" in _sse_events(r.text) and "error" not in _sse_events(r.text)
    assert _engine_saw_marker(engine) and engine.calls[-1]["stream"] is True


def test_p2_briefing_uses_the_sovereign_engine(client, engine, service_key):
    r = client.post("/api/brain/briefing", json={"request": f"Briefing {MARKER}"}, headers=service_key)
    assert r.status_code == 200
    assert r.json()["response"] == FIXED_ANSWER
    assert _engine_saw_marker(engine)


def test_p3_chat_enriched_uses_the_sovereign_engine(client, engine, bearer):
    r = client.post("/api/brain/chat-enriched", json={"message": MARKER}, headers=bearer)
    assert r.status_code == 200 and r.json()["response"] == FIXED_ANSWER
    assert _engine_saw_marker(engine)


def test_p4_omega_streams_from_the_sovereign_engine(client, engine, bearer):
    r = client.post("/api/omega/chat-enriched", json={"message": MARKER}, headers=bearer)
    assert r.status_code == 200 and "done" in _sse_events(r.text)
    assert _engine_saw_marker(engine)


def test_p5_echo_uses_the_sovereign_engine(client, engine):
    r = client.post("/api/laurentia/echo", json={"session_id": f"s2-{uuid.uuid4().hex[:6]}",
                                                  "raw_text": f"Analyse {MARKER}"})
    assert r.status_code == 200, r.text
    assert _engine_saw_marker(engine)


def test_p6_social_agent_uses_the_sovereign_engine(engine, monkeypatch):
    from jobs import social_agent

    async def no_wait(_):
        return None

    monkeypatch.setattr(social_agent.asyncio, "sleep", no_wait)
    asyncio.run(social_agent.generate_content("souveraineté", max_retries=1))
    assert len(engine.calls) == 1


# ---------- S2.4: no engine means a visible failure, never another provider ----------

def test_p1_fails_visibly_when_engine_is_down(client, engine_down):
    frek_id = _fresh_instance(client)
    r = client.post("/api/laurentia/query", json={"frek_id": frek_id, "input": "Bonjour"})
    assert "error" in _sse_events(r.text) and "done" not in _sse_events(r.text)


def test_p2_fails_visibly_when_engine_is_down(client, engine_down, service_key):
    # The route does not catch the error: the client gets a 500 (raised here by TestClient).
    with pytest.raises(cvl_brain.BrainEngineError):
        client.post("/api/brain/briefing", json={"request": "x"}, headers=service_key)


def test_p5_fails_visibly_when_engine_is_down(client, engine_down):
    r = client.post("/api/laurentia/echo", json={"session_id": "s2-down", "raw_text": "x"})
    assert r.status_code == 502


def test_unconfigured_engine_raises_without_trying_any_provider(monkeypatch):
    monkeypatch.delenv("BRAIN_ENGINE_URL", raising=False)
    monkeypatch.delenv("EMERGENT_LLM_KEY", raising=False)
    with pytest.raises(cvl_brain.BrainEngineError):
        asyncio.run(cvl_brain.chat_enriched("x", "y"))


def test_legacy_provider_path_is_refused_when_deployed(monkeypatch):
    monkeypatch.delenv("BRAIN_ENGINE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("EMERGENT_LLM_KEY", "must-not-be-used")
    with pytest.raises(cvl_brain.BrainEngineError):
        asyncio.run(cvl_brain.chat_enriched("x", "y"))
    assert "emergentintegrations.llm.chat" not in sys.modules


# ---------- S2.5: health tells which engine really answers ----------

@pytest.mark.parametrize("path", ["/api/health", "/api/brain/health"])
def test_health_reports_the_sovereign_engine(client, engine, path):
    data = client.get(path).json()
    assert data["engine"] == "sovereign" and data["model"] == "fake-deterministic"


# ---------- T1: no provider SDK is importable by production code ----------

FORBIDDEN = ("openai", "anthropic", "google.generativeai", "google.genai", "litellm",
             "cohere", "mistralai", "ollama", "emergentintegrations")
# Only these lazy imports are allowed, each inside the named function (LIA-D20 transition).
ALLOWED_LAZY = {
    ("services/cvl_brain.py", "_legacy_emergent_chat", "emergentintegrations.llm.chat"),
    ("routes/billing.py", "_checkout_client", "emergentintegrations.payments.stripe.checkout"),
    ("routes/billing.py", "create_checkout", "emergentintegrations.payments.stripe.checkout"),
}


def _imports(tree):
    """Yield (enclosing function or None, module) for every import in a module."""
    def visit(node, func):
        for child in ast.iter_child_nodes(node):
            f = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else func
            if isinstance(child, ast.Import):
                for a in child.names:
                    yield func, a.name
            elif isinstance(child, ast.ImportFrom) and child.module:
                yield func, child.module
            yield from visit(child, f)
    yield from visit(tree, None)


def test_t1_no_provider_sdk_import_in_production_code():
    offenders = []
    for path in BACKEND.rglob("*.py"):
        rel = path.relative_to(BACKEND).as_posix()
        if rel.startswith("tests/"):
            continue
        for func, module in _imports(ast.parse(path.read_text(encoding="utf-8"))):
            if any(module == f or module.startswith(f + ".") for f in FORBIDDEN):
                if (rel, func, module) not in ALLOWED_LAZY:
                    offenders.append(f"{rel}: {module} (in {func or 'module scope'})")
    assert offenders == [], offenders


def test_t1_starting_the_server_loads_no_provider_sdk():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("EMERGENT_",))}
    code = ("import sys, server; F=" + repr(FORBIDDEN) + "; "
            "bad=[m for m in sys.modules if any(m == f or m.startswith(f + '.') for f in F)]; "
            "print(bad); sys.exit(1 if bad else 0)")
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env={**env, "APP_ENV": "test"},
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr[-1500:]
