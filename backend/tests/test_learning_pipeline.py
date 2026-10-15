from __future__ import annotations

import asyncio
import pytest

from services.learning_pipeline import (
    LearningCandidateRejected,
    build_learning_candidate,
    enqueue_learning_candidate,
)


def interaction(**overrides):
    value = {
        "_id_str": "interaction-123",
        "tenant_id": "tenant-hash",
        "timestamp": "2026-10-14T10:00:00+00:00",
        "input_text": "ciphertext-input",
        "output_text": "ciphertext-output",
        "user_rating": 1,
        "corpus_eligible": True,
    }
    value.update(overrides)
    return value


def test_candidate_requires_explicit_opt_in():
    with pytest.raises(LearningCandidateRejected, match="explicit_corpus_opt_in_required"):
        build_learning_candidate(interaction(corpus_eligible=False))


def test_candidate_requires_explicit_feedback():
    with pytest.raises(LearningCandidateRejected, match="explicit_feedback_required"):
        build_learning_candidate(interaction(user_rating=None))


def test_candidate_keeps_payload_encrypted_and_requires_review():
    candidate = build_learning_candidate(interaction())
    assert candidate["encrypted_input"] == "ciphertext-input"
    assert candidate["encrypted_output"] == "ciphertext-output"
    assert "input_text" not in candidate
    assert "output_text" not in candidate
    assert candidate["status"] == "pending_review"
    assert candidate["review_required"] is True
    assert candidate["training_eligible"] is False
    assert candidate["dataset_version"] is None
    assert candidate["model_version"] is None


def test_candidate_rejects_missing_encrypted_content():
    with pytest.raises(LearningCandidateRejected, match="encrypted_input_missing"):
        build_learning_candidate(interaction(input_text=""))


class FakeCollection:
    def __init__(self):
        self.calls = []

    async def update_one(self, query, update, upsert=False):
        self.calls.append((query, update, upsert))


class FakeDB:
    def __init__(self):
        self.laurentia_learning_candidates = FakeCollection()


def test_enqueue_is_idempotency_keyed_by_interaction_id():
    async def run():
        db = FakeDB()
        assert await enqueue_learning_candidate(db, interaction()) is True
        assert len(db.laurentia_learning_candidates.calls) == 1
        query, update, upsert = db.laurentia_learning_candidates.calls[0]
        assert query == {"interaction_id": "interaction-123"}
        assert upsert is True
        assert "$setOnInsert" in update
        assert update["$setOnInsert"]["training_eligible"] is False
    asyncio.run(run())


def test_enqueue_ignores_unconsented_interaction():
    async def run():
        db = FakeDB()
        assert await enqueue_learning_candidate(db, interaction(corpus_eligible=False)) is False
        assert db.laurentia_learning_candidates.calls == []
    asyncio.run(run())
