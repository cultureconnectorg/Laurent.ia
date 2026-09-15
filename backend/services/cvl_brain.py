"""
cvl_brain.py — Wrapper Claude pour Laurent.ia
Migré vers claude-sonnet-4-5-20250929 via emergentintegrations + EMERGENT_LLM_KEY.

Fournit:
- chat_enriched(...) → réponse complète (non-streaming)
- chat_stream(...)   → générateur asynchrone qui yield chunk-par-chunk (pseudo-stream)

PATCH-007 — passage par le Model Router de l'estate (contradictions C-004/C-006).
Quand `CVLN_MODEL_ROUTER_URL` est configuré, la génération passe par le Model
Router de CVLN Agent Factory (couche provider-agnostique, doctrine DOC-ARC-04 /
ADR-002) au lieu d'appeler un provider en dur depuis Laurentia. Sans cette
configuration, le chemin local historique est conservé à l'identique — le
comportement existant n'est jamais cassé, et la raison du repli est enregistrée.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from services import cvln_model_router

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
DEFAULT_MODEL = os.environ.get("LAURENTIA_CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

# Dernier repli observé, exposé pour l'observabilité (/api/system/routing).
_last_fallback_reason: Optional[str] = None


def last_fallback_reason() -> Optional[str]:
    return _last_fallback_reason


def _build_chat(session_id: str, system_message: str):
    """Crée une nouvelle instance LlmChat (chemin local historique).

    L'import est volontairement paresseux : le module reste importable (et donc
    testable) dans un environnement sans la roue propriétaire
    `emergentintegrations`, ce qui est le cas de tout consommateur qui passe
    désormais par le Model Router de l'estate.
    """
    from emergentintegrations.llm.chat import LlmChat  # noqa: WPS433 (lazy on purpose)

    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id or str(uuid.uuid4()),
        system_message=system_message,
    ).with_model("anthropic", DEFAULT_MODEL)


async def _chat_local(user_text: str, system_message: str, session_id: str) -> str:
    """Chemin local historique — appel provider direct depuis Laurentia."""
    from emergentintegrations.llm.chat import UserMessage  # noqa: WPS433 (lazy on purpose)

    chat = _build_chat(session_id, system_message)
    msg = UserMessage(text=user_text)
    response = await chat.send_message(msg)
    return response if isinstance(response, str) else str(response)


async def chat_enriched_traced(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
    trace_id: str | None = None,
) -> Dict[str, Any]:
    """Réponse complète + métadonnées de routage (trace_id, provider, repli).

    Retourne {"text", "routed", "trace_id", "routing", "reason"}.
    """
    global _last_fallback_reason
    sid = session_id or str(uuid.uuid4())

    routed = await cvln_model_router.route_generate(
        system=system_message, prompt=user_text, session_id=sid, trace_id=trace_id
    )
    if routed.get("ok"):
        _last_fallback_reason = None
        return {
            "text": routed["text"],
            "routed": True,
            "trace_id": routed["trace_id"],
            "routing": routed.get("routing"),
            "reason": None,
        }

    _last_fallback_reason = routed.get("reason")
    text = await _chat_local(user_text, system_message, sid)
    return {
        "text": text,
        "routed": False,
        "trace_id": routed["trace_id"],
        "routing": None,
        "reason": routed.get("reason"),
    }


async def chat_enriched(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
) -> str:
    """Réponse complète, non streamée. Signature historique préservée."""
    result = await chat_enriched_traced(user_text, system_message, session_id)
    return result["text"]


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
