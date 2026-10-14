"""Runtime integration tests; run with the backend test dependencies installed."""
import asyncio
from routes import brain as brain_route

class FakeRequest:
    headers = {"X-API-Key": "test-service-key"}

def test_factory_disabled_keeps_legacy_briefing(monkeypatch):
    async def fake_chat_enriched(prompt, system, session_id):
        return "Legacy briefing."
    monkeypatch.setenv("LAURENTIA_CVLN_SERVICE_API_KEY", "test-service-key")
    monkeypatch.setenv("LAURENTIA_AGENT_FACTORY_ENABLED", "false")
    monkeypatch.setattr(brain_route.cvl_brain, "chat_enriched", fake_chat_enriched)
    monkeypatch.setattr(brain_route.cvl_brain_knowledge, "build_system_prompt", lambda: "system")
    payload = brain_route.BriefingRequest(request="Fais un briefing", trace_id="trace-legacy")
    result = asyncio.run(brain_route.briefing(payload, FakeRequest()))
    assert result["response"] == "Legacy briefing."
    assert "agent_factory" not in result
