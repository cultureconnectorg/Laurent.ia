"""
cvl_brain.py — moteur de Laurent.ia (nom technique historique « CVL Brain », conservé : LIA-D23).

S2 : l'inférence passe par un **moteur souverain** exposant l'API HTTP compatible
OpenAI (`/v1/chat/completions`) sur l'infrastructure de Laurent (llama.cpp, vLLM…).
Aucun SDK de fournisseur n'est utilisé : un simple client HTTP.

Configuration :
  BRAIN_ENGINE_URL      base du moteur (ex. http://brain.internal:8080) — requis hors dev/test
  BRAIN_ENGINE_MODEL    nom du modèle servi (défaut : "local")
  BRAIN_ENGINE_API_KEY  jeton optionnel du serveur d'inférence local
  BRAIN_ENGINE_TIMEOUT  délai en secondes (défaut : 120)

Chemin historique Emergent (LIA-D20 : conservé pendant la transition, pas supprimé) :
utilisé seulement si BRAIN_ENGINE_URL est absent, APP_ENV vaut development ou test,
et EMERGENT_LLM_KEY est défini. En environnement déployé il est refusé ici et au
démarrage (services/startup_checks.py). Sans moteur, chaque appel échoue de façon
visible : jamais de bascule silencieuse vers un fournisseur externe.

Fournit (signatures inchangées) :
- chat_enriched(...) → réponse complète
- chat_stream(...)   → générateur asynchrone de fragments (flux réel du moteur)
"""
from __future__ import annotations

import json
import os
import uuid
from typing import AsyncGenerator

import httpx

NON_DEPLOYED_ENVIRONMENTS = {"development", "test"}


class BrainEngineError(RuntimeError):
    """The inference engine is not configured, unreachable or returned an invalid answer."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _deployed() -> bool:
    return (_env("APP_ENV") or "production").lower() not in NON_DEPLOYED_ENVIRONMENTS


def _engine_url() -> str:
    return _env("BRAIN_ENGINE_URL").rstrip("/")


def _engine_model() -> str:
    return _env("BRAIN_ENGINE_MODEL", "local") or "local"


def _legacy_allowed() -> bool:
    return not _engine_url() and not _deployed() and bool(_env("EMERGENT_LLM_KEY"))


def engine_status() -> dict:
    """What actually answers: used by the health endpoints (no secret, no URL)."""
    if _engine_url():
        return {"engine": "sovereign", "model": _engine_model()}
    if _legacy_allowed():
        return {"engine": "legacy-emergent", "model": _env("LAURENTIA_CLAUDE_MODEL", "claude-sonnet-4-5-20250929")}
    return {"engine": "unconfigured", "model": None}


def _messages(user_text: str, system_message: str) -> list[dict]:
    msgs = []
    if system_message:
        msgs.append({"role": "system", "content": system_message})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def _headers() -> dict:
    key = _env("BRAIN_ENGINE_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def _timeout() -> float:
    try:
        return float(_env("BRAIN_ENGINE_TIMEOUT", "120"))
    except ValueError:
        return 120.0


def _unavailable() -> BrainEngineError:
    return BrainEngineError("moteur d'inférence souverain non configuré (BRAIN_ENGINE_URL)")


async def _legacy_emergent_chat(user_text: str, system_message: str, session_id: str) -> str:
    """Historical path, kept for the transition (LIA-D20). Never reachable when deployed."""
    if _deployed():
        raise BrainEngineError("chemin Emergent refusé en environnement déployé (LIA-D8)")
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # lazy: not needed by the sovereign path

    chat = LlmChat(
        api_key=_env("EMERGENT_LLM_KEY"),
        session_id=session_id,
        system_message=system_message,
    ).with_model("anthropic", _env("LAURENTIA_CLAUDE_MODEL", "claude-sonnet-4-5-20250929"))
    response = await chat.send_message(UserMessage(text=user_text))
    return response if isinstance(response, str) else str(response)


async def chat_enriched(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
) -> str:
    """Réponse complète, non streamée."""
    session_id = session_id or str(uuid.uuid4())
    url = _engine_url()
    if not url:
        if _legacy_allowed():
            return await _legacy_emergent_chat(user_text, system_message, session_id)
        raise _unavailable()
    payload = {"model": _engine_model(), "messages": _messages(user_text, system_message), "stream": False}
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            r = await client.post(f"{url}/v1/chat/completions", json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"] or ""
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise BrainEngineError(f"moteur d'inférence indisponible : {type(e).__name__}") from e


async def chat_stream(
    user_text: str,
    system_message: str,
    session_id: str | None = None,
    chunk_size: int = 6,
    chunk_delay: float = 0.018,
) -> AsyncGenerator[str, None]:
    """
    Flux réel du moteur (SSE `data:` du protocole compatible OpenAI).
    `chunk_size` et `chunk_delay` ne servent plus qu'au chemin historique (pseudo-flux).
    """
    session_id = session_id or str(uuid.uuid4())
    url = _engine_url()
    if not url:
        if not _legacy_allowed():
            raise _unavailable()
        full = await _legacy_emergent_chat(user_text, system_message, session_id)
        words = full.split(" ")
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            yield chunk + (" " if i + chunk_size < len(words) else "")
        return

    payload = {"model": _engine_model(), "messages": _messages(user_text, system_message), "stream": True}
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            async with client.stream("POST", f"{url}/v1/chat/completions", json=payload, headers=_headers()) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    delta = json.loads(data)["choices"][0].get("delta", {}).get("content")
                    if delta:
                        yield delta
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise BrainEngineError(f"moteur d'inférence indisponible : {type(e).__name__}") from e
