"""Sovereign bridge to CVLN Agent Factory.

This module only requests a non-mutating orchestration recommendation. It never
creates missions or executes agents; those actions require a separate explicit
authorization path. No provider fallback is permitted.
"""
from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

import httpx


def _factory_url() -> str:
    base = os.environ.get("CVLN_AGENT_FACTORY_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise RuntimeError("CVLN_AGENT_FACTORY_BASE_URL is not configured")

    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("CVLN Agent Factory URL is invalid")

    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https":
        try:
            addr = ipaddress.ip_address(host)
            internal = addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            internal = host == "localhost" or host.endswith((".internal", ".local", ".localhost"))
        if not internal:
            raise RuntimeError("HTTPS is required for non-local Agent Factory endpoints")

    forbidden = {
        "api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com",
        "api.groq.com", "api.mistral.ai", "integrations.emergentagent.com",
    }
    if host in forbidden:
        raise RuntimeError("External AI-provider endpoints are forbidden")
    return base


async def recommend_agents(request_text: str, *, entity: str | None = None) -> dict:
    """Return a validated recommendation from Agent Factory; never execute it."""
    if not isinstance(request_text, str) or len(request_text.strip()) < 5:
        raise ValueError("request_text must contain at least five non-whitespace characters")

    token = os.environ.get("CVLN_AGENT_FACTORY_SERVICE_TOKEN", "").strip()
    if not token.startswith("svc_"):
        raise RuntimeError("A scoped CVLN Agent Factory service token is required")

    payload = {"request_text": request_text.strip()}
    if entity:
        payload["entity"] = entity

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        trust_env=False,
        follow_redirects=False,
    ) as client:
        response = await client.post(
            f"{_factory_url()}/missions/orchestrate",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        result = response.json()

    if not isinstance(result, dict):
        raise RuntimeError("Agent Factory returned a non-object response")
    if not isinstance(result.get("recommended_agents"), list):
        raise RuntimeError("Agent Factory response is missing recommended_agents")
    if not isinstance(result.get("draft_mission"), dict):
        raise RuntimeError("Agent Factory response is missing draft_mission")
    return {
        "contract": "cvln.agent_factory.recommendation",
        "version": "1.0",
        "source": "CVLN Agent Factory",
        "mutating": False,
        "intent": result.get("intent", {}),
        "recommended_agents": result["recommended_agents"],
        "draft_mission": result["draft_mission"],
    }
