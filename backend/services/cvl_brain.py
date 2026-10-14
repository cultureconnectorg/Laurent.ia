"""Sovereign-compatible LLM adapter for Laurent.ia.

Uses an explicitly configured OpenAI-compatible inference endpoint under the
operator's control. It deliberately has no external-provider fallback. Network
proxy environment variables are ignored so prompts cannot be routed through an
unapproved proxy by the host environment.
"""
from __future__ import annotations

import ipaddress
import os
from typing import AsyncGenerator
from urllib.parse import urlsplit

import httpx
from openai import AsyncOpenAI

DEFAULT_MODEL = os.environ.get("LAURENTIA_LLM_MODEL", "local-model")
_FORBIDDEN_HOSTS = {
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "api.groq.com",
    "api.mistral.ai",
    "integrations.emergentagent.com",
}


def _controlled_base_url() -> str:
    base_url = os.environ.get("LAURENTIA_LLM_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError(
            "Laurent.ia inference is not configured: set LAURENTIA_LLM_BASE_URL "
            "to the CVLN-controlled OpenAI-compatible inference endpoint."
        )

    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("Laurent.ia inference endpoint URL is invalid.")

    host = (parsed.hostname or "").lower().rstrip(".")
    if host in _FORBIDDEN_HOSTS:
        raise RuntimeError("Hosted third-party inference endpoints are forbidden.")

    # Do not send prompts over cleartext to a public host. HTTP is only permitted
    # for loopback, private/link-local IPs, and explicitly internal service names.
    if parsed.scheme != "https":
        private_transport = False
        try:
            address = ipaddress.ip_address(host)
            private_transport = address.is_private or address.is_loopback or address.is_link_local
        except ValueError:
            private_transport = host == "localhost" or host.endswith(
                (".internal", ".local", ".localhost")
            )
        if not private_transport:
            raise RuntimeError("Use HTTPS for non-local Laurent.ia inference endpoints.")

    # Private/internal hosts are allowed by default. Any public DNS hostname must
    # be approved by exact hostname; a suffix or wildcard is never accepted.
    configured_hosts = {
        item.strip().lower().rstrip(".")
        for item in os.environ.get("LAURENTIA_LLM_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    }
    if configured_hosts:
        allowed = host in configured_hosts
    else:
        try:
            address = ipaddress.ip_address(host)
            allowed = address.is_private or address.is_loopback or address.is_link_local
        except ValueError:
            allowed = host == "localhost" or host.endswith(
                (".internal", ".local", ".localhost")
            )
    if not allowed:
        raise RuntimeError(
            "Unapproved inference hostname; set LAURENTIA_LLM_ALLOWED_HOSTS "
            "to the exact CVLN-controlled hostname."
        )
    return base_url


def _build_client() -> AsyncOpenAI:
    base_url = _controlled_base_url()
    api_key = os.environ.get("LAURENTIA_LLM_API_KEY", "").strip() or "local-endpoint"
    # Crucial sovereignty boundary: do not inherit HTTP_PROXY/HTTPS_PROXY/ALL_PROXY
    # from Render or another host, and do not follow redirects to a different host.
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(120.0, connect=10.0),
        trust_env=False,
        follow_redirects=False,
    )
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=http_client,
        max_retries=0,
    )


def _use_embedded_model() -> bool:
    """Embedded model is the default; remote inference is opt-in only."""
    mode = os.environ.get("LAURENTIA_INFERENCE_MODE", "embedded").strip().lower()
    if mode == "embedded":
        return True
    if mode == "controlled-endpoint":
        return False
    raise RuntimeError("LAURENTIA_INFERENCE_MODE must be embedded or controlled-endpoint.")


async def chat_enriched(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
) -> str:
    """Generate locally by default; only use a controlled endpoint when explicitly enabled."""
    if _use_embedded_model():
        from services.local_inference import chat_complete
        return await chat_complete(system_message, user_text)

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


async def chat_messages(
    messages: list[dict[str, str]],
    session_id: str | None = None,
) -> str:
    """Complete a bounded transcript using embedded inference by default."""
    if _use_embedded_model():
        from services.local_inference import chat_messages as local_chat_messages
        return await local_chat_messages(messages)
    if not isinstance(messages, list) or not 1 <= len(messages) <= 24:
        raise ValueError("Conversation must contain between 1 and 24 messages.")
    allowed_roles = {"system", "user", "assistant", "tool"}
    checked: list[dict[str, str]] = []
    total_chars = 0
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ValueError("Conversation message schema is invalid.")
        role, content = message["role"], message["content"]
        if role not in allowed_roles or not isinstance(content, str) or len(content) > 40_000:
            raise ValueError("Conversation message is invalid.")
        total_chars += len(content)
        checked.append({"role": role, "content": content})
    if total_chars > 80_000:
        raise ValueError("Conversation exceeds the configured context budget.")

    client = _build_client()
    try:
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=checked,
            extra_headers={"X-Laurentia-Session-ID": session_id or ""},
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
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
    """Stream actual generated deltas from the embedded model or controlled endpoint."""
    if _use_embedded_model():
        from services.local_inference import chat_stream as local_chat_stream
        async for delta in local_chat_stream(system_message, user_text):
            yield delta
        return

    client = _build_client()
    try:
        stream = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_text},
            ],
            extra_headers={"X-Laurentia-Session-ID": session_id or ""},
            stream=True,
        )
        async for event in stream:
            choices = getattr(event, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None) if delta else None
            if isinstance(content, str) and content:
                yield content
    finally:
        await client.close()
