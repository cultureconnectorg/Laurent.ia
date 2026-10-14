"""Security regression tests for Laurent.ia's local-only inference adapter."""
import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services import cvl_brain  # noqa: E402


@pytest.fixture
def clean_llm_env(monkeypatch):
    for key in (
        "LAURENTIA_LLM_BASE_URL",
        "LAURENTIA_LLM_MODEL",
        "LAURENTIA_LLM_API_KEY",
        "LAURENTIA_LLM_ALLOWED_HOSTS",
        "LAURENTIA_LOCAL_LLM_URL",
        "LAURENTIA_LOCAL_LLM_MODEL",
        "LAURENTIA_LOCAL_LLM_API_KEY",
        "LAURENTIA_LOCAL_LLM_TIMEOUT_SECONDS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_missing_endpoint_fails_closed(clean_llm_env):
    with pytest.raises(RuntimeError, match="Moteur souverain non configuré"):
        asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia."))


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.openai.com/v1/chat/completions",
        "https://api.anthropic.com/v1/chat/completions",
        "https://generativelanguage.googleapis.com/v1/chat/completions",
        "https://integrations.emergentagent.com/v1/chat/completions",
        "http://llm.internal:8000/v1/chat/completions",
        "http://169.254.169.254/v1/chat/completions",
        "http://169.254.10.20/v1/chat/completions",
        "http://224.0.0.1/v1/chat/completions",
        "http://0.0.0.0:11434/v1/chat/completions",
    ],
)
def test_hosted_dns_metadata_and_non_routable_endpoints_are_rejected(
    clean_llm_env, monkeypatch, endpoint
):
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_URL", endpoint)
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    with pytest.raises(RuntimeError, match="Endpoint LLM refusé"):
        cvl_brain._local_endpoint()


def test_private_ip_endpoint_is_allowed_without_provider_sdk(clean_llm_env, monkeypatch):
    monkeypatch.setenv(
        "LAURENTIA_LOCAL_LLM_URL", "http://192.168.10.20:11434/v1/chat/completions"
    )
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    endpoint, model, api_key, timeout = cvl_brain._local_endpoint()
    assert endpoint == "http://192.168.10.20:11434/v1/chat/completions"
    assert model == "qwen-local"
    assert api_key is None
    assert timeout == 60.0


def test_public_cleartext_and_url_credentials_are_rejected(clean_llm_env, monkeypatch):
    monkeypatch.setenv(
        "LAURENTIA_LOCAL_LLM_URL", "http://192.168.10.20:11434/v1/chat/completions?x=1"
    )
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    with pytest.raises(RuntimeError, match="paramètres de requête"):
        cvl_brain._local_endpoint()
    monkeypatch.setenv(
        "LAURENTIA_LOCAL_LLM_URL",
        "http://user:secret@192.168.10.20:11434/v1/chat/completions",
    )
    with pytest.raises(RuntimeError, match="sans identifiants"):
        cvl_brain._local_endpoint()


def test_http_client_ignores_proxy_environment_and_disables_redirects(
    clean_llm_env, monkeypatch
):
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

    monkeypatch.setenv(
        "LAURENTIA_LOCAL_LLM_URL", "http://192.168.10.20:11434/v1/chat/completions"
    )
    monkeypatch.setenv("LAURENTIA_LOCAL_LLM_MODEL", "qwen-local")
    monkeypatch.setenv("HTTPS_PROXY", "http://untrusted-proxy.example")
    monkeypatch.setattr(cvl_brain.httpx, "AsyncClient", FakeClient)

    result = asyncio.run(cvl_brain.chat_enriched("Bonjour", "Tu es Laurentia."))

    assert result == "Réponse locale"
    assert captured["follow_redirects"] is False
    assert captured["trust_env"] is False
    assert captured["url"] == "http://192.168.10.20:11434/v1/chat/completions"
    assert captured["payload"]["model"] == "qwen-local"
    assert "Authorization" not in captured["headers"]
