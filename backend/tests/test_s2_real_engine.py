"""S2.6 — real inference with an open-weight model served locally (llama.cpp).

Runs only when REAL_ENGINE=1 and BRAIN_ENGINE_URL points to a real local engine
(CI job `real-inference`). In the default suite these tests are reported as
skipped: they need a real model, which the deterministic engine is not.
The autouse network guard still applies: the whole conversation must stay on
loopback.
"""
import asyncio
import json
import os
import uuid

import pytest
from pymongo import MongoClient

from _harness.fake_engine import FIXED_ANSWER
from services import cvl_brain

pytestmark = pytest.mark.skipif(os.environ.get("REAL_ENGINE") != "1",
                                reason="needs a real local open-weight engine (CI job real-inference)")


def test_real_engine_answers_directly():
    answer = asyncio.run(cvl_brain.chat_enriched(
        "Réponds en une courte phrase : quelle est la capitale de la France ?",
        "Tu es un assistant concis. Réponds en français."))
    assert answer.strip() and answer != FIXED_ANSWER
    assert "paris" in answer.lower(), answer


def test_real_engine_full_conversation_is_streamed_and_stored_encrypted(app_client):
    frek_id = f"DEMO-REAL-{uuid.uuid4().hex[:8].upper()}"
    assert app_client.post("/api/laurentia/instances/init", json={"frek_id": frek_id}).status_code == 200
    r = app_client.post("/api/laurentia/query", json={"frek_id": frek_id, "input": "Bonjour, présente-toi en une phrase."})
    events = [l[7:] for l in r.text.splitlines() if l.startswith("event: ")]
    assert "token" in events and "done" in events and "error" not in events, r.text[-500:]

    from services.crypto import decrypt_text
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    meta = next(json.loads(l[6:]) for l in r.text.splitlines() if l.startswith("data: ") and "tenant_id" in l)
    rec = db.laurentia_interactions.find_one({"tenant_id": meta["tenant_id"]})  # stored by hash, not frek_id
    assert rec is not None
    stored = rec.get("output_text")
    assert stored and "bonjour" not in str(stored).lower()  # not stored in clear
    assert decrypt_text(stored).strip()


def test_real_engine_briefing_contract(app_client, monkeypatch):
    monkeypatch.setenv("LAURENTIA_CVLN_SERVICE_API_KEY", "real-engine-test-key")
    r = app_client.post("/api/brain/briefing", json={"request": "Donne un briefing d'une phrase sur la souveraineté numérique."},
                        headers={"X-API-Key": "real-engine-test-key"})
    assert r.status_code == 200
    assert r.json()["contract"] == "laurentia.briefing" and r.json()["response"].strip()
