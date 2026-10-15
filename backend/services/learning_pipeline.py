"""Consent-gated, local-first learning candidate queue.

This module does not call a hosted model and never decrypts interaction content.
It copies the already-encrypted interaction payload into a review queue. Promotion
to a training dataset/model is a separate, explicitly reviewed step.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class LearningCandidateRejected(ValueError):
    """Raised when an interaction is not eligible for learning review."""


def build_learning_candidate(
    interaction: dict[str, Any],
    *,
    consent_recorded_at: str | None = None,
) -> dict[str, Any]:
    """Build a review-only candidate from an interaction with explicit opt-in.

    Only encrypted content fields are accepted. No raw prompts or responses are
    generated, inferred, decrypted, or sent to an external inference provider.
    """
    interaction_id = str(interaction.get("_id_str") or "").strip()
    if not interaction_id:
        raise LearningCandidateRejected("interaction_id_missing")
    if interaction.get("corpus_eligible") is not True:
        raise LearningCandidateRejected("explicit_corpus_opt_in_required")
    if interaction.get("user_rating") not in (-1, 1):
        raise LearningCandidateRejected("explicit_feedback_required")

    encrypted_input = interaction.get("input_text")
    encrypted_output = interaction.get("output_text")
    if not isinstance(encrypted_input, str) or not encrypted_input:
        raise LearningCandidateRejected("encrypted_input_missing")
    if not isinstance(encrypted_output, str) or not encrypted_output:
        raise LearningCandidateRejected("encrypted_output_missing")

    now = datetime.now(timezone.utc).isoformat()
    return {
        "interaction_id": interaction_id,
        "tenant_id": interaction.get("tenant_id"),
        "consent_recorded_at": consent_recorded_at or now,
        "source_timestamp": interaction.get("timestamp"),
        "rating": interaction["user_rating"],
        # These values remain ciphertext from the source interaction.
        "encrypted_input": encrypted_input,
        "encrypted_output": encrypted_output,
        "status": "pending_review",
        "review_required": True,
        "training_eligible": False,
        "created_at": now,
        "updated_at": now,
        "rejection_reason": None,
        "dataset_version": None,
        "model_version": None,
    }


async def enqueue_learning_candidate(
    db: Any,
    interaction: dict[str, Any],
    *,
    consent_recorded_at: str | None = None,
) -> bool:
    """Idempotently queue an opted-in interaction for human review.

    Returns True when a candidate is eligible and upserted; False for ineligible
    interactions. This function is intentionally not an HTTP authorization layer:
    callers must first prove ownership of the interaction and record consent.
    """
    try:
        candidate = build_learning_candidate(
            interaction, consent_recorded_at=consent_recorded_at
        )
    except LearningCandidateRejected:
        return False

    await db.laurentia_learning_candidates.update_one(
        {"interaction_id": candidate["interaction_id"]},
        {
            "$setOnInsert": candidate,
            "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True,
    )
    return True
