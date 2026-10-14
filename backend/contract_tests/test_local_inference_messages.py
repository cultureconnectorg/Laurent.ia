"""Offline contract tests for local multi-message agent turns."""
import asyncio
import threading

from services import local_inference


class FakeModel:
    def __init__(self):
        self.received = None

    def tokenize(self, value, add_bos=False, special=False):
        return list(value)

    def detokenize(self, tokens):
        return bytes(tokens)

    def create_chat_completion(self, *, messages, max_tokens, temperature):
        self.received = messages
        return {
            "choices": [{"message": {"content": "Réponse locale de test"}}],
            "usage": {"completion_tokens": 4},
        }


def test_local_chat_messages_preserves_roles_and_recent_context(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(local_inference, "_get_model", lambda: model)
    monkeypatch.setattr(local_inference, "_generation_lock", threading.Lock())
    messages = [
        {"role": "system", "content": "Instructions de sécurité du moteur."},
        {"role": "user", "content": "Demande initiale."},
        {"role": "assistant", "content": "Proposition outil."},
        {"role": "user", "content": "Résultat outil non fiable."},
        {"role": "user", "content": "Demande de suivi récente."},
    ]
    result = asyncio.run(local_inference.chat_messages(messages))
    assert result == "Réponse locale de test"
    assert model.received[0]["role"] == "system"
    assert model.received[-1]["role"] == "user"
    assert "Demande de suivi récente." in model.received[-1]["content"]
    assert local_inference.model_status()["generation_count"] >= 1
