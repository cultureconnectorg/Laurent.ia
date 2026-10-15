"""Route-level tests proving Agent Factory recommendations reach Laurentia briefing."""
import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routes import brain as brain_route


class FakeRequest:
    headers = {"X-API-Key": "test-service-key"}


def test_briefing_uses_factory_recommendation_when_enabled(monkeypatch):
    recommendation = {
        "contract": "cvln.agent_factory.recommendation",
        "version": "1.0",
        "source": "CVLN Agent Factory",
        "mutating": False,
        "intent": {"mission_type": "strategy", "keywords": ["kiltikonet"]},
        "recommended_agents": [{"agent_id": "AGT-STRAT", "score": 4}],
        "draft_mission": {"title": "Kiltikonet", "agent_ids": ["AGT-STRAT"]},
    }
    captured = {}

    async def fake_recommend_agents(request_text, *, entity=None):
        captured["request_text"] = request_text
        captured["entity"] = entity
        return recommendation

    async def fake_chat_enriched(prompt, system, session_id):
        captured["prompt"] = prompt
        return "Briefing avec recommandations."

    monkeypatch.setenv("LAURENTIA_CVLN_SERVICE_API_KEY", "test-service-key")
    monkeypatch.setenv("LAURENTIA_AGENT_FACTORY_ENABLED", "true")
    monkeypatch.setattr(brain_route.cvl_brain, "chat_enriched", fake_chat_enriched)
    monkeypatch.setattr(brain_route.cvl_brain_knowledge, "build_system_prompt", lambda: "system")
    monkeypatch.setattr(
        "services.agent_factory_bridge.recommend_agents",
        fake_recommend_agents,
    )

    payload = brain_route.BriefingRequest(
        request="Prépare la stratégie Kiltikonet",
        context={"entity": "Kiltikonet", "private_context": "must not be forwarded to Factory"},
        trace_id="trace-test",
    )
    result = asyncio.run(brain_route.briefing(payload, FakeRequest()))

    assert result["response"] == "Briefing avec recommandations."
    assert result["agent_factory"] == recommendation
    assert captured["request_text"] == "Prépare la stratégie Kiltikonet"
    assert captured["entity"] == "Kiltikonet"
    assert "AGT-STRAT" in captured["prompt"]
    assert "must not be forwarded to Factory" in captured["prompt"]
    assert "must not be forwarded to Factory" not in captured["request_text"]


def test_factory_disabled_keeps_legacy_briefing(monkeypatch):
    captured = {}

    async def fake_chat_enriched(prompt, system, session_id):
        captured["prompt"] = prompt
        return "Legacy briefing."

    monkeypatch.setenv("LAURENTIA_CVLN_SERVICE_API_KEY", "test-service-key")
    monkeypatch.setenv("LAURENTIA_AGENT_FACTORY_ENABLED", "false")
    monkeypatch.setattr(brain_route.cvl_brain, "chat_enriched", fake_chat_enriched)
    monkeypatch.setattr(brain_route.cvl_brain_knowledge, "build_system_prompt", lambda: "system")

    payload = brain_route.BriefingRequest(request="Fais un briefing", trace_id="trace-legacy")
    result = asyncio.run(brain_route.briefing(payload, FakeRequest()))

    assert result["response"] == "Legacy briefing."
    assert "agent_factory" not in result