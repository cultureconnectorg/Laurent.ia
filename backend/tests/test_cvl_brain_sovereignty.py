"""Security tests for the Laurent.ia sovereign inference boundary."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import cvl_brain  # noqa: E402


@pytest.fixture
def clean_llm_env(monkeypatch):
    for key in (
        "LAURENTIA_LLM_BASE_URL",
        "LAURENTIA_LLM_MODEL",
        "LAURENTIA_LLM_API_KEY",
        "LAURENTIA_LLM_ALLOWED_HOSTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_missing_endpoint_fails_closed(clean_llm_env):
    with pytest.raises(RuntimeError, match="not configured"):
        cvl_brain._build_client()


@pytest.mark.parametrize("host", [
    "https://api.openai.com/v1",
    "https://api.anthropic.com/v1",
    "https://generativelanguage.googleapis.com/v1",
    "https://integrations.emergentagent.com/v1",
])
def test_hosted_provider_endpoints_are_rejected(clean_llm_env, monkeypatch, host):
    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", host)
    monkeypatch.setenv("LAURENTIA_LLM_ALLOWED_HOSTS", host.split("/")[2])
    monkeypatch.setenv("LAURENTIA_LLM_MODEL", "test-model")
    with pytest.raises(RuntimeError, match="forbidden"):
        cvl_brain._controlled_base_url()


def test_private_internal_endpoint_allowed_without_public_allowlist(clean_llm_env, monkeypatch):
    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", "http://llm.internal:8000/v1")
    monkeypatch.setenv("LAURENTIA_LLM_MODEL", "qwen-local")
    assert cvl_brain._controlled_base_url() == "http://llm.internal:8000/v1"


def test_public_host_requires_exact_allowlist(clean_llm_env, monkeypatch):
    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", "https://llm.example.org/v1")
    with pytest.raises(RuntimeError, match="Unapproved inference hostname"):
        cvl_brain._controlled_base_url()
    monkeypatch.setenv("LAURENTIA_LLM_ALLOWED_HOSTS", "llm.example.org")
    assert cvl_brain._controlled_base_url() == "https://llm.example.org/v1"


def test_public_http_and_url_credentials_are_rejected(clean_llm_env, monkeypatch):
    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", "http://llm.example.org/v1")
    monkeypatch.setenv("LAURENTIA_LLM_ALLOWED_HOSTS", "llm.example.org")
    with pytest.raises(RuntimeError, match="HTTPS"):
        cvl_brain._controlled_base_url()
    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", "https://user:secret@llm.internal/v1")
    with pytest.raises(RuntimeError, match="invalid"):
        cvl_brain._controlled_base_url()


def test_sdk_ignores_proxy_environment_and_disables_redirects(clean_llm_env, monkeypatch):
    captured = {}

    class FakeHttpClient:
        def __init__(self, **kwargs):
            captured["httpx"] = kwargs

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["openai"] = kwargs

    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", "http://llm.internal:8000/v1")
    monkeypatch.setenv("LAURENTIA_LLM_MODEL", "qwen-local")
    monkeypatch.setenv("HTTPS_PROXY", "http://untrusted-proxy.example")
    monkeypatch.setattr(cvl_brain.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(cvl_brain, "AsyncOpenAI", FakeOpenAI)

    cvl_brain._build_client()

    assert captured["httpx"]["trust_env"] is False
    assert captured["httpx"]["follow_redirects"] is False
    assert captured["openai"]["max_retries"] == 0
    assert captured["openai"]["base_url"] == "http://llm.internal:8000/v1"
