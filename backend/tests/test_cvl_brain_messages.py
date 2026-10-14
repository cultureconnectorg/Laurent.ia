"""Validation tests for the controlled multi-message inference adapter."""
import asyncio
from types import SimpleNamespace

import pytest

from services import cvl_brain


def test_chat_messages_rejects_empty_transcript_before_network(monkeypatch):
    monkeypatch.setattr(cvl_brain, "_build_client", lambda: pytest.fail("network client must not be built"))
    with pytest.raises(ValueError, match="between 1 and 24"):
        asyncio.run(cvl_brain.chat_messages([]))


@pytest.mark.parametrize("messages", [
    [{"role": "developer", "content": "no"}],
    [{"role": "user", "content": 7}],
    [{"role": "user", "content": "x", "extra": "no"}],
    [{"role": "user", "content": "x" * 40_001}],
    [{"role": "user", "content": "x" * 40_000}, {"role": "user", "content": "x" * 40_001}],
])
def test_chat_messages_rejects_invalid_transcripts_before_network(monkeypatch, messages):
    monkeypatch.setattr(cvl_brain, "_build_client", lambda: pytest.fail("network client must not be built"))
    with pytest.raises(ValueError):
        asyncio.run(cvl_brain.chat_messages(messages))


def test_chat_messages_uses_controlled_client_and_passes_session_header(monkeypatch):
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse locale"))])

    class FakeClient:
        chat = SimpleNamespace(completions=SimpleNamespace(create=create))

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(cvl_brain, "_build_client", lambda: FakeClient())
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "bonjour"},
        {"role": "assistant", "content": "outil"},
        {"role": "tool", "content": '{"ok":true}'},
    ]
    answer = asyncio.run(cvl_brain.chat_messages(messages, session_id="sess-test"))
    assert answer == "Réponse locale"
    assert captured["messages"] == messages
    assert captured["extra_headers"]["X-Laurentia-Session-ID"] == "sess-test"
    assert captured["closed"] is True
