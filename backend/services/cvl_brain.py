"""
cvl_brain.py — Wrapper Claude pour Laurent.ia
Migré vers claude-sonnet-4-5-20250929 via emergentintegrations + EMERGENT_LLM_KEY.

Fournit:
- chat_enriched(...) → réponse complète (non-streaming)
- chat_stream(...)   → générateur asynchrone qui yield chunk-par-chunk (pseudo-stream)
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator

from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
DEFAULT_MODEL = os.environ.get("LAURENTIA_CLAUDE_MODEL", "claude-sonnet-4-5-20250929")


def _build_chat(session_id: str, system_message: str) -> LlmChat:
    """Crée une nouvelle instance LlmChat (anthropic / claude-sonnet-4.5)."""
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id or str(uuid.uuid4()),
        system_message=system_message,
    ).with_model("anthropic", DEFAULT_MODEL)


async def chat_enriched(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
) -> str:
    """Réponse complète, non streamée."""
    chat = _build_chat(session_id or str(uuid.uuid4()), system_message)
    msg = UserMessage(text=user_text)
    response = await chat.send_message(msg)
    return response if isinstance(response, str) else str(response)


async def chat_stream(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
    chunk_size: int = 6,
    chunk_delay: float = 0.018,
) -> AsyncGenerator[str, None]:
    """
    Pseudo-streaming SSE.
    `emergentintegrations.LlmChat.send_message()` retourne la réponse complète,
    on la débite en chunks de quelques caractères pour offrir un rendu fluide token-by-token.
    """
    full = await chat_enriched(user_text, system_message, session_id)
    # Découpe par mots, regroupés par paquet
    tokens = full.split(" ")
    buffer = []
    for i, tok in enumerate(tokens):
        buffer.append(tok)
        if len(buffer) >= chunk_size or i == len(tokens) - 1:
            chunk = " ".join(buffer)
            if i != len(tokens) - 1:
                chunk += " "
            yield chunk
            buffer = []
            await asyncio.sleep(chunk_delay)
