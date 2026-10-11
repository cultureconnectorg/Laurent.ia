"""C1 — access control of a deployed instance (APP_ENV=production at request time).

Deny by default: every /api route needs the principal's session, except an explicit
public list. Legacy sign-ins without proof of possession are closed. Demo identities
do not exist. Passkey routes accept only the configured principal.
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pymongo import MongoClient

from services import frekcore_bridge


@pytest.fixture
def deployed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")


@pytest.fixture
def db():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _session(db, user_id: str) -> str:
    token = f"sess_c1_{uuid.uuid4().hex}"
    db.users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id, "frek_id": "FREK-C1-TEST",
                                                         "email": "", "name": "x"}}, upsert=True)
    db.user_sessions.insert_one({"session_token": token, "user_id": user_id,
                                 "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)})
    return token


PROTECTED = [
    ("POST", "/api/laurentia/query", {"frek_id": "X", "input": "x"}),
    ("GET", "/api/laurentia/memory/FREK-C1-TEST", None),
    ("GET", "/api/laurentia/sessions/list", None),
    ("POST", "/api/laurentia/echo", {"session_id": "s", "raw_text": "x"}),
    ("POST", "/api/export/pdf", {"title": "t", "content_md": "c"}),
    ("GET", "/api/admin/orchestrator/status", None),
    ("POST", "/api/brain/chat-enriched", {"message": "x"}),
    ("GET", "/api/status", None),
]


@pytest.mark.parametrize("method, path, body", PROTECTED)
def test_protected_routes_refuse_anonymous_callers(app_client, deployed, method, path, body):
    r = app_client.request(method, path, json=body)
    assert r.status_code == 401, (path, r.status_code, r.text[:200])


@pytest.mark.parametrize("method, path, body", PROTECTED)
def test_protected_routes_refuse_a_non_principal_session(app_client, deployed, db, method, path, body):
    token = _session(db, f"user_other_{uuid.uuid4().hex[:6]}")
    r = app_client.request(method, path, json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, (path, r.status_code)


def test_principal_session_passes_the_gate(app_client, deployed, db):
    token = _session(db, "principal")
    r = app_client.get("/api/laurentia/sessions/list", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code != 401, r.text[:200]


@pytest.mark.parametrize("method, path", [("GET", "/api/health"), ("GET", "/api/brain/health"), ("GET", "/api/")])
def test_public_list_stays_reachable(app_client, deployed, method, path):
    assert app_client.request(method, path).status_code == 200


def test_frek_id_only_login_is_closed(app_client, deployed):
    r = app_client.post("/api/auth/frek", json={"frek_id": "DEMO-SAYD"})
    # Refused by the gate (401) or by the route itself (410); never a session.
    assert r.status_code in (401, 410) and "set-cookie" not in r.headers


def test_emergent_oauth_exchange_is_closed(app_client, deployed):
    r = app_client.post("/api/auth/session", json={"session_id": "anything"})
    assert r.status_code in (401, 410) and "set-cookie" not in r.headers


def test_demo_identities_do_not_exist_when_deployed(deployed):
    assert asyncio.run(frekcore_bridge.validate_frek_id("DEMO-SAYD"))["valid"] is False


def test_passkey_routes_need_a_configured_principal(app_client, deployed, monkeypatch):
    monkeypatch.delenv("LAURENTIA_PRINCIPAL_FREK_ID", raising=False)
    r = app_client.post("/api/auth/passkey/login/begin", json={"frek_id": "FREK-ANY"})
    assert r.status_code == 503


def test_passkey_routes_refuse_any_other_frek_id(app_client, deployed, monkeypatch):
    monkeypatch.setenv("LAURENTIA_PRINCIPAL_FREK_ID", "FREK-PRINCIPAL")
    monkeypatch.setenv("FREKCORE_API_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("FREKCORE_API_KEY", "x")
    for step in ("register/begin", "login/begin"):
        r = app_client.post(f"/api/auth/passkey/{step}", json={"frek_id": "FREK-INTRUDER"})
        assert r.status_code == 403, (step, r.text)


def test_dev_mode_is_unchanged(app_client):
    # Without APP_ENV=production (suite default "test"), existing behaviour is preserved.
    assert app_client.get("/api/status").status_code == 200


def test_passkey_session_is_refused_when_frekcore_cannot_confirm_the_frek_id(app_client, deployed, db, monkeypatch):
    # Fail closed: without FREKCORE's confirmation, a passkey session opens nothing.
    from services import principal_gate
    monkeypatch.setenv("FREKCORE_API_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("FREKCORE_API_KEY", "x")
    principal_gate._status_cache.clear()
    token = _session(db, "principal")
    db.users.update_one({"user_id": "principal"}, {"$set": {"auth_method": "passkey"}})
    try:
        r = app_client.get("/api/laurentia/sessions/list", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401 and "FREKCORE" in r.json()["detail"]
        assert db.user_sessions.count_documents({"session_token": token}) == 0  # session deleted
    finally:
        db.users.update_one({"user_id": "principal"}, {"$unset": {"auth_method": ""}})
        principal_gate._status_cache.clear()
