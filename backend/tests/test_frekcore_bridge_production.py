"""Regression tests for production identity fail-closed behavior.

Run from the repository root with:
    python -m pytest backend/tests/test_frekcore_bridge_production.py
"""
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services import frekcore_bridge  # noqa: E402


PRODUCTION_MARKERS = (
    "LAURENTIA_ENV",
    "APP_ENV",
    "ENVIRONMENT",
    "NODE_ENV",
    "VERCEL_ENV",
    "RAILWAY_ENVIRONMENT",
)


def clear_runtime_markers(monkeypatch):
    for name in PRODUCTION_MARKERS:
        monkeypatch.delenv(name, raising=False)


def test_demo_identity_is_rejected_in_production(monkeypatch):
    clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")

    result = asyncio.run(frekcore_bridge.validate_frek_id("DEMO-SAYD"))

    assert result["valid"] is False
    assert result["error"] == "demo identities disabled outside explicit development"


def test_demo_identity_remains_available_in_explicit_nonproduction(monkeypatch):
    clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("LAURENTIA_ENV", "development")

    result = asyncio.run(frekcore_bridge.validate_frek_id("DEMO-SAYD"))

    assert result["valid"] is True
    assert result["role"] == "founder"


def test_production_refuses_identity_when_remote_authority_is_missing(monkeypatch):
    clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(frekcore_bridge, "FREKCORE_API_URL", "")
    monkeypatch.setattr(frekcore_bridge, "FREKCORE_API_KEY", "")

    result = asyncio.run(frekcore_bridge.validate_frek_id("FREK-UNKNOWN-123"))

    assert result["valid"] is False
    assert result["error"] == "FREKCORE authority not configured"

def test_demo_identity_is_rejected_when_runtime_is_unmarked(monkeypatch):
    clear_runtime_markers(monkeypatch)

    result = asyncio.run(frekcore_bridge.validate_frek_id("DEMO-SAYD"))

    assert result["valid"] is False
