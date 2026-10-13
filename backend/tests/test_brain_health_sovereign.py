"""Health endpoint must not claim a retired hosted model is active."""
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from routes.brain import brain_health  # noqa: E402


def test_brain_health_reports_unconfigured_without_local_engine(monkeypatch):
    monkeypatch.delenv("LAURENTIA_LOCAL_LLM_URL", raising=False)
    monkeypatch.delenv("LAURENTIA_LOCAL_LLM_MODEL", raising=False)

    result = asyncio.run(brain_health())

    assert result["llm_provider"] == "unconfigured"
    assert result["llm_configured"] is False
    assert result["model"] is None


def test_brain_health_reports_only_configured_local_model(monkeypatch):
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")

    result = asyncio.run(brain_health())

    assert result["llm_provider"] == "self-hosted"
    assert result["llm_configured"] is True
    assert result["model"] == "qwen-local"
