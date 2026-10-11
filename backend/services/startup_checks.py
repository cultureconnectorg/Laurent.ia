"""
startup_checks.py — refuse to start a deployed instance with an unsafe configuration (S1.4).

Runs before anything else in server.py. Only variable names are reported,
never their values.

APP_ENV: "development" and "test" skip the checks. Any other value, and a
missing APP_ENV, is treated as a deployed environment (fail closed).

Checks for a deployed environment:
  - no key for an external LLM provider (LIA-D8: sovereign inference only);
  - a sovereign inference engine is configured (BRAIN_ENGINE_URL);
  - every configured model endpoint points to an allowed host
    (LAURENTIA_ALLOWED_MODEL_HOSTS, comma-separated);
  - CORS origins are an explicit list (no "*");
  - memory encryption key and secret salt are set and are not the public defaults.
"""
from __future__ import annotations

import os
from typing import Mapping
from urllib.parse import urlparse

NON_DEPLOYED_ENVIRONMENTS = {"development", "test"}
SUPPORTED_ENVIRONMENTS = NON_DEPLOYED_ENVIRONMENTS | {"staging", "production"}

# Keys that would route cognitive data to an external provider.
EXTERNAL_LLM_KEYS = (
    "EMERGENT_LLM_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)
# Endpoints that receive prompts or generated content.
MODEL_ENDPOINT_VARS = ("BRAIN_ENGINE_URL", "SD_API_URL", "CVLN_MODEL_ROUTER_URL")

# Public defaults still present in services/crypto.py and services/fingerprint.py.
DEFAULT_ENCRYPTION_KEY = "mvp-encryption-placeholder-change-in-prod"
DEFAULT_SECRET_SALT = "laurentia-mvp-salt-change-in-prod-7d3a9c"


class UnsafeConfigurationError(RuntimeError):
    pass


def app_env(env: Mapping[str, str]) -> str:
    return (env.get("APP_ENV") or "production").strip().lower()


def find_problems(env: Mapping[str, str]) -> list[str]:
    """Return the configuration problems for a deployed environment (empty list if none)."""
    current = app_env(env)
    if current not in SUPPORTED_ENVIRONMENTS:
        return [f"APP_ENV must be one of {sorted(SUPPORTED_ENVIRONMENTS)}"]
    if current in NON_DEPLOYED_ENVIRONMENTS:
        return []

    problems: list[str] = []
    for name in EXTERNAL_LLM_KEYS:
        if env.get(name, "").strip():
            problems.append(f"{name} is set: external LLM providers are forbidden (LIA-D8)")

    if not env.get("BRAIN_ENGINE_URL", "").strip():
        problems.append("BRAIN_ENGINE_URL is required: the sovereign inference engine is not configured")

    allowed = {h.strip().lower() for h in env.get("LAURENTIA_ALLOWED_MODEL_HOSTS", "").split(",") if h.strip()}
    for name in MODEL_ENDPOINT_VARS:
        url = env.get(name, "").strip()
        if not url:
            continue
        host = (urlparse(url).hostname or "").lower()
        if host not in allowed:
            problems.append(f"{name} points to a host outside LAURENTIA_ALLOWED_MODEL_HOSTS")

    origins = [o.strip() for o in env.get("CORS_ORIGINS", "").split(",") if o.strip()]
    if not origins or "*" in origins:
        problems.append("CORS_ORIGINS must be an explicit list of origins")

    key = env.get("LAURENTIA_ENCRYPTION_KEY", "").strip()
    if not key or key == DEFAULT_ENCRYPTION_KEY:
        problems.append("LAURENTIA_ENCRYPTION_KEY is missing or is the public default")
    salt = env.get("LAURENTIA_SECRET_SALT", "").strip()
    if not salt or salt == DEFAULT_SECRET_SALT:
        problems.append("LAURENTIA_SECRET_SALT is missing or is the public default")
    return problems


def enforce(env: Mapping[str, str] | None = None) -> None:
    env = os.environ if env is None else env
    problems = find_problems(env)
    if problems:
        raise UnsafeConfigurationError(
            f"Refusing to start (APP_ENV={app_env(env)}): " + "; ".join(problems)
        )
