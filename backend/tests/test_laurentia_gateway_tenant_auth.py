"""Regression tests for tenant authorization in Laurentia gateway routes."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from routes import laurentia_gateway as gateway  # noqa: E402


MARKERS = (
    "LAURENTIA_ENV",
    "APP_ENV",
    "ENVIRONMENT",
    "NODE_ENV",
    "VERCEL_ENV",
    "RAILWAY_ENVIRONMENT",
)


def clear_markers(monkeypatch):
    for name in MARKERS:
        monkeypatch.delenv(name, raising=False)


def test_unauthenticated_request_fails_closed_without_explicit_development(monkeypatch):
    clear_markers(monkeypatch)

    async def no_user(_request):
        return None

    monkeypatch.setattr(gateway, "get_current_user", no_user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(gateway._authorize_tenant(SimpleNamespace(), "FREK-ALICE"))

    assert exc.value.status_code == 401


def test_unauthenticated_request_allowed_only_in_explicit_development(monkeypatch):
    clear_markers(monkeypatch)
    monkeypatch.setenv("LAURENTIA_ENV", "development")

    async def no_user(_request):
        return None

    monkeypatch.setattr(gateway, "get_current_user", no_user)

    assert asyncio.run(gateway._authorize_tenant(SimpleNamespace(), "DEMO-SAYD")) is None


def test_authenticated_user_cannot_select_another_tenant(monkeypatch):
    clear_markers(monkeypatch)

    async def alice(_request):
        return {"user_id": "user-alice", "frek_id": "FREK-ALICE"}

    monkeypatch.setattr(gateway, "get_current_user", alice)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(gateway._authorize_tenant(SimpleNamespace(), "FREK-BOB"))

    assert exc.value.status_code == 403


def test_authenticated_user_can_select_own_tenant_case_insensitively(monkeypatch):
    clear_markers(monkeypatch)

    async def alice(_request):
        return {"user_id": "user-alice", "frek_id": "FREK-ALICE"}

    monkeypatch.setattr(gateway, "get_current_user", alice)

    result = asyncio.run(gateway._authorize_tenant(SimpleNamespace(), "frek-alice"))

    assert result["frek_id"] == "FREK-ALICE"


def test_production_marker_overrides_development_marker(monkeypatch):
    clear_markers(monkeypatch)
    monkeypatch.setenv("LAURENTIA_ENV", "development")
    monkeypatch.setenv("VERCEL_ENV", "production")

    async def no_user(_request):
        return None

    monkeypatch.setattr(gateway, "get_current_user", no_user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(gateway._authorize_tenant(SimpleNamespace(), "FREK-ALICE"))

    assert exc.value.status_code == 401
