"""Regression tests for the native Google OAuth contract.

These tests deliberately avoid live Google/Render/MongoDB calls. They cover the
local security gates that must reject invalid callbacks before issuing sessions.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException, Response

BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from routes import auth  # noqa: E402


def configure_oauth(monkeypatch):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(
        auth, "GOOGLE_REDIRECT_URI",
        "https://backend.example.test/api/auth/google/callback",
    )
    monkeypatch.setattr(auth, "FRONTEND_URL", "https://frontend.example.test")


def test_google_start_sets_short_lived_http_only_state_cookie(monkeypatch):
    configure_oauth(monkeypatch)

    response = asyncio.run(auth.google_oauth_start())

    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["client_id"] == ["test-client-id"]
    assert query["redirect_uri"] == [
        "https://backend.example.test/api/auth/google/callback"
    ]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    state = query["state"][0]
    assert len(state) >= 32

    cookie = response.headers["set-cookie"].lower()
    assert auth.GOOGLE_STATE_COOKIE in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=600" in cookie
    assert "path=/api/auth/google" in cookie


def test_callback_rejects_missing_or_mismatched_state_before_network_or_db(monkeypatch):
    configure_oauth(monkeypatch)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    response = asyncio.run(
        auth.google_oauth_callback(
            request=request,
            code="attacker-controlled-code",
            state="attacker-state",
            oauth_state="different-state",
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "https://frontend.example.test/#auth=error"
    cookie = response.headers.get("set-cookie", "").lower()
    assert auth.GOOGLE_STATE_COOKIE in cookie
    assert "max-age=0" in cookie


def test_callback_rejects_provider_error_without_creating_session(monkeypatch):
    configure_oauth(monkeypatch)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    response = asyncio.run(
        auth.google_oauth_callback(
            request=request,
            code=None,
            state=None,
            error="access_denied",
            oauth_state="some-state",
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "https://frontend.example.test/#auth=error"


def test_google_start_fails_closed_when_configuration_is_missing(monkeypatch):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(auth, "GOOGLE_REDIRECT_URI", "https://backend.example.test/callback")
    monkeypatch.setattr(auth, "FRONTEND_URL", "https://frontend.example.test")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.google_oauth_start())

    assert exc.value.status_code == 503


class FakeCollection:
    def __init__(self, documents=()):
        self.documents = list(documents)
        self.deleted = []

    async def find_one(self, query, projection=None):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return dict(document)
        return None

    async def delete_one(self, query):
        self.deleted.append(dict(query))
        self.documents = [
            document for document in self.documents
            if not all(document.get(key) == value for key, value in query.items())
        ]


class FakeDatabase:
    def __init__(self, **collections):
        self.__dict__.update(collections)


def test_expired_session_is_rejected():
    now = datetime.now(timezone.utc)
    db = FakeDatabase(
        user_sessions=FakeCollection([{
            "session_token": "expired-token",
            "user_id": "user-1",
            "expires_at": (now - timedelta(seconds=1)).isoformat(),
        }]),
        users=FakeCollection([{
            "user_id": "user-1",
            "email": "user@example.test",
        }]),
    )

    user = asyncio.run(auth._resolve_session(db, "expired-token"))

    assert user is None


def test_valid_session_resolves_only_the_session_owner():
    db = FakeDatabase(
        user_sessions=FakeCollection([{
            "session_token": "valid-token",
            "user_id": "user-1",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }]),
        users=FakeCollection([
            {"user_id": "user-1", "email": "owner@example.test"},
            {"user_id": "user-2", "email": "other@example.test"},
        ]),
    )

    user = asyncio.run(auth._resolve_session(db, "valid-token"))

    assert user == {"user_id": "user-1", "email": "owner@example.test"}


def test_logout_revokes_session_and_clears_cookie():
    sessions = FakeCollection([{"session_token": "session-to-revoke"}])
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db=FakeDatabase(user_sessions=sessions)
    )))
    response = Response()

    result = asyncio.run(auth.logout(
        request=request,
        response=response,
        session_token="session-to-revoke",
        authorization=None,
    ))

    assert result == {"ok": True}
    assert sessions.deleted == [{"session_token": "session-to-revoke"}]
    cookie = response.headers["set-cookie"].lower()
    assert auth.COOKIE_NAME in cookie
    assert "max-age=0" in cookie
    assert "httponly" in cookie



def test_callback_rejects_unverified_google_email_before_database_access(monkeypatch):
    configure_oauth(monkeypatch)

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse({"access_token": "test-access-token"})

        async def get(self, *args, **kwargs):
            return FakeResponse({
                "sub": "google-subject",
                "email": "unverified@example.test",
                "email_verified": False,
            })

    monkeypatch.setattr(auth.httpx, "AsyncClient", FakeAsyncClient)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    response = asyncio.run(auth.google_oauth_callback(
        request=request,
        code="valid-shaped-code",
        state="matching-state",
        oauth_state="matching-state",
    ))

    assert response.status_code == 303
    assert response.headers["location"] == "https://frontend.example.test/#auth=error"
    assert auth.COOKIE_NAME not in response.headers.get("set-cookie", "")


def test_verified_google_callback_creates_user_tenant_session_and_http_only_cookie(monkeypatch):
    configure_oauth(monkeypatch)

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, **kwargs):
            assert url == "https://oauth2.googleapis.com/token"
            assert kwargs["data"]["grant_type"] == "authorization_code"
            return FakeResponse({"access_token": "test-access-token"})

        async def get(self, url, **kwargs):
            assert url == "https://openidconnect.googleapis.com/v1/userinfo"
            assert kwargs["headers"]["Authorization"] == "Bearer test-access-token"
            return FakeResponse({
                "sub": "google-subject-verified",
                "email": "owner@example.test",
                "email_verified": True,
                "name": "Test Owner",
                "picture": "https://images.example.test/avatar.png",
            })

    class WritableCollection(FakeCollection):
        async def insert_one(self, document):
            self.documents.append(dict(document))

        async def update_one(self, query, update, upsert=False):
            for document in self.documents:
                if all(document.get(key) == value for key, value in query.items()):
                    document.update(update.get("$set", {}))
                    if "$setOnInsert" in update:
                        for key, value in update["$setOnInsert"].items():
                            document.setdefault(key, value)
                    return
            if upsert:
                document = dict(query)
                document.update(update.get("$set", {}))
                document.update(update.get("$setOnInsert", {}))
                self.documents.append(document)

    db = FakeDatabase(
        users=WritableCollection(),
        user_sessions=WritableCollection(),
        laurentia_instances=WritableCollection(),
        laurentia_memory=WritableCollection(),
    )
    monkeypatch.setattr(auth.httpx, "AsyncClient", FakeAsyncClient)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)))

    response = asyncio.run(auth.google_oauth_callback(
        request=request,
        code="valid-code",
        state="matching-state",
        oauth_state="matching-state",
    ))

    assert response.status_code == 303
    assert response.headers["location"] == "https://frontend.example.test/#auth=success"
    assert len(db.users.documents) == 1
    user = db.users.documents[0]
    assert user["email"] == "owner@example.test"
    assert user["auth_provider"] == "google"
    assert user["google_sub"] == "google-subject-verified"
    assert user["frek_id"] == auth._derive_frek_id("owner@example.test")
    assert len(db.laurentia_instances.documents) == 1
    assert db.laurentia_instances.documents[0]["frek_id"] == user["frek_id"]
    assert len(db.laurentia_memory.documents) == 1
    assert len(db.user_sessions.documents) == 1
    session = db.user_sessions.documents[0]
    assert session["user_id"] == user["user_id"]
    assert session["auth_method"] == "google"
    assert session["session_token"].startswith("google_")
    cookie = response.headers["set-cookie"].lower()
    assert auth.COOKIE_NAME in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=none" in cookie
    assert "max-age=604800" in cookie
