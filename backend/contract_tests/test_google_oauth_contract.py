"""Regression tests for the native Google OAuth contract.

These tests deliberately avoid live Google/Render/MongoDB calls. They cover the
local security gates that must reject invalid callbacks before issuing sessions.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException

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
