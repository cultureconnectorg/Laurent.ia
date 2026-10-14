"""Contract tests for the non-mutating Agent Factory bridge."""
import asyncio
import json

import pytest

from services import agent_factory_bridge as bridge


def test_missing_factory_url_fails_closed(monkeypatch):
    monkeypatch.delenv("CVLN_AGENT_FACTORY_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        bridge._factory_url()


def test_public_http_factory_url_is_rejected(monkeypatch):
    monkeypatch.setenv("CVLN_AGENT_FACTORY_BASE_URL", "http://factory.example.com")
    with pytest.raises(RuntimeError, match="HTTPS is required"):
        bridge._factory_url()


def test_external_provider_url_is_rejected(monkeypatch):
    monkeypatch.setenv("CVLN_AGENT_FACTORY_BASE_URL", "https://api.openai.com")
    with pytest.raises(RuntimeError, match="forbidden"):
        bridge._factory_url()


def test_bad_service_token_fails_closed(monkeypatch):
    monkeypatch.setenv("CVLN_AGENT_FACTORY_BASE_URL", "https://factory.cvln.example")
    monkeypatch.setenv("CVLN_AGENT_FACTORY_SERVICE_TOKEN", "not-a-service-token")
    with pytest.raises(RuntimeError, match="service token"):
        asyncio.run(bridge.recommend_agents("Prépare le plan Kiltikonet"))


def test_short_request_is_rejected_before_network(monkeypatch):
    monkeypatch.setenv("CVLN_AGENT_FACTORY_SERVICE_TOKEN", "svc_test")
    with pytest.raises(ValueError, match="five"):
        asyncio.run(bridge.recommend_agents("  x "))
