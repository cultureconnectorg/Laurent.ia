"""Regression tests for the Kiltikonet identity bridge's production fail-closed rules."""
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services import kiltikonet_bridge  # noqa: E402


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

    result = asyncio.run(kiltikonet_bridge.validate_frek_id("DEMO-SAYD"))

    assert result["valid"] is False


def test_missing_identity_authority_fails_closed_in_production(monkeypatch):
    clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(kiltikonet_bridge, "KILTIKONET_API_URL", "")
    monkeypatch.setattr(kiltikonet_bridge, "KILTIKONET_API_KEY", "")

    result = asyncio.run(kiltikonet_bridge.validate_frek_id("FREK-ANY-123"))

    assert result["valid"] is False
    assert result["error"] == "Kiltikonet identity authority not configured"


def test_unconfigured_bridge_keeps_development_guest_behavior(monkeypatch):
    clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("LAURENTIA_ENV", "development")
    monkeypatch.setattr(kiltikonet_bridge, "KILTIKONET_API_URL", "")
    monkeypatch.setattr(kiltikonet_bridge, "KILTIKONET_API_KEY", "")

    result = asyncio.run(kiltikonet_bridge.validate_frek_id("FREK-DEV-123"))

    assert result["valid"] is True
    assert result["role"] == "guest"


def test_demo_profile_is_not_returned_in_production(monkeypatch):
    clear_runtime_markers(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")

    try:
        asyncio.run(kiltikonet_bridge.get_frek_profile("DEMO-SAYD"))
    except kiltikonet_bridge.KiltikonetUnavailable:
        pass
    else:
        raise AssertionError("Production must not receive a local demo founder profile")
