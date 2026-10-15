"""Regression tests: a FREK-ID alone must not authenticate a production user."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from routes import auth  # noqa: E402


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


@pytest.mark.parametrize("marker,value", [
    ("APP_ENV", "production"),
    ("VERCEL_ENV", "production"),
    (None, None),
])
def test_frek_id_only_login_is_refused_outside_explicit_development(monkeypatch, marker, value):
    clear_markers(monkeypatch)
    if marker:
        monkeypatch.setenv(marker, value)

    payload = auth.FrekLoginRequest(frek_id="FREK-EXAMPLE-123")
    request = SimpleNamespace()  # guard must reject before accessing DB/session state
    response = SimpleNamespace()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.login_with_frek_id(payload, request, response))

    assert exc.value.status_code == 403
    assert "preuve de possession" in exc.value.detail


def test_explicit_development_mode_is_recognized(monkeypatch):
    clear_markers(monkeypatch)
    monkeypatch.setenv("LAURENTIA_ENV", "development")

    assert auth._is_explicit_development() is True


def test_production_marker_overrides_development_marker(monkeypatch):
    clear_markers(monkeypatch)
    monkeypatch.setenv("LAURENTIA_ENV", "development")
    monkeypatch.setenv("VERCEL_ENV", "production")

    assert auth._is_explicit_development() is False
