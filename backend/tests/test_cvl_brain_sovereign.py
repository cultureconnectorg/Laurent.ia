"""Tests that Laurentia never falls back to an external LLM provider."""
import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services import cvl_brain  # noqa: E402


def clear_llm_env(monkeypatch):
    for name in (
        "LAURENTIA_LOCAL_LLM_URL",
        "LAURENTIA_LOCAL_LLM_MODEL",
        "LAURENTIA_LOCAL_LLM_API_KEY",
        "LAURENTIA_LOCAL_LLM_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_missing_local_engine_fails_closed_without_external_fallback(monkeypatch):
    clear_llm_env(monkeypatch)
    with pytest.raises(RuntimeError, match="Moteur souverain non configuré"):
        asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia."))


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.example.com/v1/chat/completions",
        "http://169.254.169.254/v1/chat/completions",
        "http://169.254.10.20/v1/chat/completions",
        "http://224.0.0.1/v1/chat/completions",
        "http://0.0.0.0:11434/v1/chat/completions",
    ],
)
def test_public_metadata_link_local_and_non_routable_endpoints_are_rejected(monkeypatch, endpoint):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_URL", endpoint)
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "local-model")
    with pytest.raises(RuntimeError, match="Endpoint LLM refusé"):
        asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia."))


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "301", "not-a-number"])
def test_invalid_timeout_fails_closed(monkeypatch, timeout):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_URL", "http://192.168.10.20:11434/v1/chat/completions")
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_TIMEOUT_SECONDS", timeout)
    with pytest.raises(RuntimeError, match="TIMEOUT_SECONDS"):
        asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia."))


def test_private_local_endpoint_is_used_and_no_provider_sdk_is_required(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_URL", "http://192.168.10.20:11434/v1/chat/completions")
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_API_KEY", "local-test-key")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Réponse locale"}}]}

    class FakeClient:
        def __init__(self, timeout, follow_redirects, trust_env):
            captured["timeout"] = timeout
            captured["follow_redirects"] = follow_redirects
            captured["trust_env"] = trust_env

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(cvl_brain.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia.", "session-1"))

    assert result == "Réponse locale"
    assert captured["url"] == "http://192.168.10.20:11434/v1/chat/completions"
    assert captured["payload"]["model"] == "qwen-local"
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "Tu es Laurentia."}
    assert captured["payload"]["messages"][1] == {"role": "user", "content": "Bonjour"}
    assert captured["headers"]["Authorization"] == "Bearer local-test-key"
    assert captured["follow_redirects"] is False
    assert captured["trust_env"] is False


def test_url_query_and_fragment_are_rejected(monkeypatch):
    clear_llm_env(monkeypatch)
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_URL", "http://192.168.10.20:11434/v1/chat/completions?x=1")
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    with pytest.raises(RuntimeError, match="paramètres de requête"):
        asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia."))
