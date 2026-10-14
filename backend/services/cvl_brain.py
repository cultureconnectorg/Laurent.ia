"""
cvl_brain.py — Client strict d'un moteur LLM souverain auto-hébergé.

Aucun fournisseur LLM externe n'est appelé par ce module.
Le moteur doit exposer une API compatible OpenAI sur une adresse locale/privée,
configurée par LAURENTIA_LOCAL_LLM_URL, avec LAURENTIA_LOCAL_LLM_MODEL.
Si le moteur n'est pas configuré ou joignable, l'appel échoue sans fallback externe.
"""
from __future__ import annotations

import asyncio
import ipaddress
import math
import os
import uuid
from typing import AsyncGenerator
from urllib.parse import urlparse

import httpx


def _local_endpoint() -> tuple[str, str, str | None, float]:
    endpoint = os.environ.get("LAURENTIA_LOCAL_LLM_URL", "").strip()
    model = os.environ.get("LAURENTIA_LOCAL_LLM_MODEL", "").strip()
    api_key = os.environ.get("LAURENTIA_LOCAL_LLM_API_KEY", "").strip() or None
    try:
        timeout = float(os.environ.get("LAURENTIA_LOCAL_LLM_TIMEOUT_SECONDS", "60"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("LAURENTIA_LOCAL_LLM_TIMEOUT_SECONDS doit être un nombre entre 1 et 300.") from exc

    if not endpoint or not model:
        raise RuntimeError(
            "Moteur souverain non configuré : définir LAURENTIA_LOCAL_LLM_URL "
            "et LAURENTIA_LOCAL_LLM_MODEL. Aucun fournisseur externe ne sera utilisé."
        )

    parsed = urlparse(endpoint)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(
            "LAURENTIA_LOCAL_LLM_URL doit être une URL HTTP(S) valide sans identifiants, "
            "paramètres de requête ni fragment."
        )

    if not parsed.path.rstrip("/").endswith("/chat/completions"):
        raise RuntimeError(
            "LAURENTIA_LOCAL_LLM_URL doit cibler une route compatible /chat/completions."
        )

    hostname = parsed.hostname.lower().rstrip(".")
    local_host = hostname == "localhost"
    try:
        ip = ipaddress.ip_address(hostname)
        # Link-local includes cloud metadata addresses (for example 169.254.169.254).
        # Never permit these, multicast, unspecified, or reserved destinations.
        local_host = local_host or (
            (ip.is_loopback or ip.is_private)
            and not (ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved)
        )
    except ValueError:
        # DNS names are rejected except the explicit loopback name above.
        pass

    if not local_host:
        raise RuntimeError(
            "Endpoint LLM refusé : seuls localhost et les adresses IP privées/locales "
            "non link-local sont autorisés."
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("Port du moteur LLM local invalide.") from exc
    if port is not None and not (1 <= port <= 65535):
        raise RuntimeError("Port du moteur LLM local invalide.")
    if not math.isfinite(timeout) or not (1 <= timeout <= 300):
        raise RuntimeError("LAURENTIA_LOCAL_LLM_TIMEOUT_SECONDS doit être compris entre 1 et 300.")

    return endpoint, model, api_key, timeout


async def chat_enriched(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
) -> str:
    """Appelle exclusivement le moteur souverain auto-hébergé configuré."""
    endpoint, model, api_key, timeout = _local_endpoint()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
    }
    # session_id is accepted for API compatibility; the local endpoint does not
    # receive it as a provider-specific session identifier.
    _ = session_id or str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Réponse invalide du moteur LLM souverain (format chat-completions attendu).") from exc

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Some OpenAI-compatible local runtimes return typed content blocks.
        parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        return "".join(parts)
    raise RuntimeError("Contenu de réponse invalide du moteur LLM souverain.")


async def chat_stream(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
    chunk_size: int = 6,
    chunk_delay: float = 0.018,
) -> AsyncGenerator[str, None]:
    """Pseudo-streaming SSE sur la réponse du moteur souverain local."""
    if chunk_size < 1:
        raise ValueError("chunk_size doit être supérieur ou égal à 1.")
    if chunk_delay < 0:
        raise ValueError("chunk_delay ne peut pas être négatif.")
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
            if chunk_delay:
                await asyncio.sleep(chunk_delay)
