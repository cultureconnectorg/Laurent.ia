"""Validation tests for the bounded local-only multi-message inference adapter."""
import asyncio

import pytest

from services import cvl_brain


def test_chat_messages_rejects_empty_transcript_before_endpoint_resolution(monkeypatch):
    monkeypatch.setattr(
        cvl_brain, "_local_endpoint", lambda: pytest.fail("endpoint must not be resolved")
    )
    with pytest.raises(ValueError, match="between 1 and 24"):
        asyncio.run(cvl_brain.chat_messages([]))


@pytest.mark.parametrize(
    "messages",
    [
        [{"role": "developer", "content": "no"}],
        [{"role": "user", "content": 7}],
        [{"role": "user", "content": "x", "extra": "no"}],
        [{"role": "user", "content": "x" * 40_001}],
        [{"role": "user", "content": "x" * 40_000}, {"role": "user", "content": "x" * 40_001}],
    ],
)
def test_chat_messages_rejects_invalid_transcripts_before_endpoint_resolution(
    monkeypatch, messages
):
    monkeypatch.setattr(
        cvl_brain, "_local_endpoint", lambda: pytest.fail("endpoint must not be resolved")
    )
    with pytest.raises(ValueError):
        asyncio.run(cvl_brain.chat_messages(messages))


def test_chat_messages_uses_local_http_client_and_passes_session_header(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Réponse locale"}}]}

    class FakeClient:
        def __init__(self, *, timeout, follow_redirects, trust_env):
            captured["timeout"] = timeout
            captured["follow_redirects"] = follow_redirects
            captured["trust_env"] = trust_env

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(
        cvl_brain,
        "_local_endpoint",
        lambda: ("http://127.0.0.1:11434/v1/chat/completions", "qwen-local", None, 5.0),
    )
    monkeypatch.setattr(cvl_brain.httpx, "AsyncClient", FakeClient)
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "bonjour"},
        {"role": "assistant", "content": "outil"},
        {"role": "tool", "content": '{"ok":true}'},
    ]

    answer = asyncio.run(cvl_brain.chat_messages(messages, session_id="sess-test"))

    assert answer == "Réponse locale"
    assert captured["payload"]["messages"] == messages
    assert captured["payload"]["model"] == "qwen-local"
    assert captured["headers"]["X-Laurentia-Session-ID"] == "sess-test"
    assert captured["follow_redirects"] is False
    assert captured["trust_env"] is False
