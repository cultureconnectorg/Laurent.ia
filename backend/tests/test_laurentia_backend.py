"""
Backend tests for Laurent.ia MVP — Core Gateway.
Tests health, instances, memory, SSE query streaming, multi-tenant isolation,
and MongoDB persistence with privacy assertions.
"""
import os
import json
import time
import hashlib
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://emergent-ai-238.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "laurentia")
SALT = os.environ.get("LAURENTIA_SECRET_SALT", "laurentia-mvp-salt-change-in-prod-7d3a9c")


def _tenant_id(frek_id: str) -> str:
    return hashlib.sha256(f"{frek_id}{SALT}".encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------------------- Health --------------------
class TestHealth:
    def test_root_health(self, api):
        r = api.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["model"] == "claude-sonnet-4-5-20250929"

    def test_brain_health(self, api):
        r = api.get(f"{BASE_URL}/api/brain/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["model"] == "claude-sonnet-4-5-20250929"


# -------------------- Instances --------------------
class TestInstances:
    def test_init_instance_sayd(self, api):
        r = api.post(f"{BASE_URL}/api/laurentia/instances/init",
                     json={"frek_id": "DEMO-SAYD"}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        inst = data["instance"]
        assert inst["frek_id"] == "DEMO-SAYD"
        assert inst["version"] == "free"
        assert inst["tokens_limit_month"] == 10000
        assert "_id" not in inst

    def test_get_instance_sayd(self, api):
        r = api.get(f"{BASE_URL}/api/laurentia/instances/DEMO-SAYD", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["first_name"] == "Sayd"
        assert data["instance"]["frek_id"] == "DEMO-SAYD"
        assert data["jcc_balance_kiltikonet"] == 150

    def test_get_instance_artist(self, api):
        r = api.get(f"{BASE_URL}/api/laurentia/instances/DEMO-ARTIST", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["first_name"] == "Mira"

    def test_get_memory_safe_shape(self, api):
        r = api.get(f"{BASE_URL}/api/laurentia/memory/DEMO-SAYD", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # safe shape: no raw "sessions" list, only counts
        assert "sessions" not in data or isinstance(data.get("sessions"), list) is False
        assert "session_count" in data or "long_term" in data


# -------------------- SSE Query --------------------
def _consume_sse(url: str, payload: dict, timeout: int = 60):
    events = []
    with requests.post(url, json=payload, stream=True, timeout=timeout,
                       headers={"Accept": "text/event-stream"}) as r:
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:300]}"
        content_type = r.headers.get("Content-Type", "")
        assert content_type.startswith("text/event-stream"), f"Bad Content-Type: {content_type}"
        buf = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                evt = {"event": "message", "data": ""}
                for line in raw.split("\n"):
                    if line.startswith("event:"):
                        evt["event"] = line[6:].strip()
                    elif line.startswith("data:"):
                        evt["data"] += line[5:].strip()
                if evt["data"]:
                    try:
                        evt["data"] = json.loads(evt["data"])
                    except Exception:
                        pass
                events.append(evt)
                if evt["event"] in ("done", "error"):
                    return events, content_type
    return events, content_type


class TestQuerySSE:
    def test_sse_query_sayd(self, api):
        events, ctype = _consume_sse(
            f"{BASE_URL}/api/laurentia/query",
            {"frek_id": "DEMO-SAYD", "input": "Salut, qui es-tu en une phrase?"},
            timeout=60,
        )
        assert ctype.startswith("text/event-stream")
        kinds = [e["event"] for e in events]
        assert "meta" in kinds, f"missing meta: {kinds}"
        assert "token" in kinds, f"missing token: {kinds}"
        assert "done" in kinds, f"missing done: {kinds}"
        # meta validations
        meta = next(e["data"] for e in events if e["event"] == "meta")
        assert meta["first_name"] == "Sayd"
        assert meta["tenant_id"] == _tenant_id("DEMO-SAYD")
        assert "session_id" in meta
        assert "tokens_remaining" in meta
        # token validations
        tokens = [e["data"] for e in events if e["event"] == "token"]
        assert len(tokens) >= 1
        for t in tokens:
            assert "text" in t
        # done payload
        done = next(e["data"] for e in events if e["event"] == "done")
        assert "tokens_used" in done
        assert "latency_ms" in done

    def test_multi_tenant_isolation(self, api):
        ev_s, _ = _consume_sse(
            f"{BASE_URL}/api/laurentia/query",
            {"frek_id": "DEMO-SAYD", "input": "Bonjour"},
            timeout=60,
        )
        ev_a, _ = _consume_sse(
            f"{BASE_URL}/api/laurentia/query",
            {"frek_id": "DEMO-ARTIST", "input": "Bonjour"},
            timeout=60,
        )
        meta_s = next(e["data"] for e in ev_s if e["event"] == "meta")
        meta_a = next(e["data"] for e in ev_a if e["event"] == "meta")
        assert meta_s["tenant_id"] != meta_a["tenant_id"]
        # SHA-256 hex = 64 chars
        assert len(meta_s["tenant_id"]) == 64
        assert len(meta_a["tenant_id"]) == 64
        assert meta_s["tenant_id"] == _tenant_id("DEMO-SAYD")
        assert meta_a["tenant_id"] == _tenant_id("DEMO-ARTIST")


# -------------------- Mongo persistence + privacy --------------------
class TestPersistencePrivacy:
    def test_query_persists_and_anonymizes(self, api, mongo_db):
        # Trigger a fresh query
        _consume_sse(
            f"{BASE_URL}/api/laurentia/query",
            {"frek_id": "DEMO-SAYD", "input": "Présente-toi brièvement."},
            timeout=60,
        )
        # Give a moment for fire-and-forget writes
        time.sleep(0.5)

        t_id = _tenant_id("DEMO-SAYD")
        inst = mongo_db.laurentia_instances.find_one({"frek_id": "DEMO-SAYD"})
        assert inst is not None
        interactions = list(mongo_db.laurentia_interactions.find({"tenant_id": t_id}).limit(5))
        assert len(interactions) >= 1, "no interactions persisted"
        usage = list(mongo_db.laurentia_usage.find({"frek_id": "DEMO-SAYD"}).limit(5))
        assert len(usage) >= 1
        mem = mongo_db.laurentia_memory.find_one({"frek_id": "DEMO-SAYD"})
        assert mem is not None

        # PRIVACY: interactions must store tenant_id (hash), not raw frek_id
        for it in interactions:
            assert "tenant_id" in it
            assert it["tenant_id"] == t_id
            assert it.get("frek_id") is None  # not present in clear
            # Stringified document should NOT contain raw FREK-ID literal
            serialized = json.dumps({k: str(v) for k, v in it.items() if k != "_id"})
            assert "DEMO-SAYD" not in serialized
