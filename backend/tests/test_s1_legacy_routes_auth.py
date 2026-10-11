"""S1.6 — legacy inference routes are internal-only: an anonymous call is
refused (401) and never reaches the model; an authenticated call does."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from server import app


class EngineSpy:
    def __init__(self):
        self.calls = 0

    async def chat_enriched(self, *a, **k):
        self.calls += 1
        return "ok"

    async def chat_stream(self, *a, **k):
        self.calls += 1
        yield "ok"


@pytest.fixture(scope="module")
def client():
    # One client (one event loop) for the module: the app's Motor client is loop-bound.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def spy(monkeypatch):
    s = EngineSpy()
    monkeypatch.setattr("routes.brain.cvl_brain.chat_enriched", s.chat_enriched)
    monkeypatch.setattr("routes.omega.cvl_brain.chat_stream", s.chat_stream)
    return s


@pytest.fixture
def session_token():
    """A real session in the application's MongoDB database."""
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    user_id, token = f"user-s1-{uuid.uuid4().hex[:8]}", f"sess_s1_{uuid.uuid4().hex}"
    db.users.insert_one({"user_id": user_id, "email": f"{user_id}@test.local"})
    db.user_sessions.insert_one({"session_token": token, "user_id": user_id,
                                 "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)})
    yield token
    db.user_sessions.delete_one({"session_token": token})
    db.users.delete_one({"user_id": user_id})


ROUTES = [("/api/brain/chat-enriched", {"message": "ping"}),
          ("/api/omega/chat-enriched", {"message": "ping"})]


@pytest.mark.parametrize("path, body", ROUTES)
def test_anonymous_call_is_refused_before_the_engine(client, spy, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 401
    assert spy.calls == 0


@pytest.mark.parametrize("path, body", ROUTES)
def test_unknown_token_is_refused_before_the_engine(client, spy, path, body):
    r = client.post(path, json=body, headers={"Authorization": "Bearer not-a-session"})
    assert r.status_code == 401
    assert spy.calls == 0


@pytest.mark.parametrize("path, body", ROUTES)
def test_authenticated_call_reaches_the_engine(client, spy, session_token, path, body):
    r = client.post(path, json=body, headers={"Authorization": f"Bearer {session_token}"})
    assert r.status_code == 200, r.text
    assert spy.calls == 1
