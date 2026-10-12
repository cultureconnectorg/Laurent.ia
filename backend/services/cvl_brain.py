"""Sovereign-compatible LLM adapter for Laurent.ia.

Uses an explicitly configured OpenAI-compatible inference endpoint under the
operator's control. It deliberately has no external-provider fallback.
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

from openai import AsyncOpenAI

DEFAULT_MODEL = os.environ.get("LAURENTIA_LLM_MODEL", "local-model")


def _build_client() -> AsyncOpenAI:
    base_url = os.environ.get("LAURENTIA_LLM_BASE_URL", "").strip()
    if not base_url:
        raise RuntimeError(
            "Laurent.ia inference is not configured: set LAURENTIA_LLM_BASE_URL "
            "to the controlled OpenAI-compatible inference endpoint."
        )
    # Some self-hosted endpoints do not require a key. Never default to a
    # public provider URL; base_url must be explicitly configured by the operator.
    api_key = os.environ.get("LAURENTIA_LLM_API_KEY", "").strip() or "local-endpoint"
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


async def chat_enriched(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
) -> str:
    """Return a completion from the explicitly configured inference endpoint."""
    client = _build_client()
    try:
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_text},
            ],
            extra_headers={"X-Laurentia-Session-ID": session_id or ""},
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The configured inference endpoint returned an empty response.")
        return content
    finally:
        await client.close()


async def chat_stream(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
    chunk_size: int = 6,
    chunk_delay: float = 0.018,
) -> AsyncGenerator[str, None]:
    """Compatibility pseudo-stream over a complete response."""
    full = await chat_enriched(user_text, system_message, session_id)
    tokens = full.split(" ")
    buffer: list[str] = []
    for i, token in enumerate(tokens):
        buffer.append(token)
        if len(buffer) >= chunk_size or i == len(tokens) - 1:
            chunk = " ".join(buffer)
            if i != len(tokens) - 1:
                chunk += " "
            yield chunk
            buffer = []
            await asyncio.sleep(chunk_delay)
