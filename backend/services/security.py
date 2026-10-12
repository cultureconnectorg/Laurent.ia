"""Helpers sécurité — tenant_id hashing, drapeaux dev explicites, CORS."""
from __future__ import annotations

import hashlib
import os

SALT = os.environ.get("LAURENTIA_SECRET_SALT", "")

_TRUE = ("1", "true", "yes", "on")

# Rôles privilégiés : jamais accordés à une identité de démo / non vérifiée.
PRIVILEGED_ROLES = frozenset({"founder", "admin"})


def tenant_id_for(frek_id: str) -> str:
    """SHA-256(frek_id + SALT). Jamais de frek_id en clair dans les logs."""
    return hashlib.sha256(f"{frek_id}{SALT}".encode("utf-8")).hexdigest()


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE


def demo_ids_allowed() -> bool:
    """
    Mode démo / dev EXPLICITE (LAURENTIA_ALLOW_DEMO_IDS=true).
    Désactivé par défaut. Conditionne : FREK-IDs DEMO-*, acceptation des FREK-IDs
    quand les bridges d'identité ne sont pas configurés, et POST /api/auth/frek.
    Lu à chaque appel (pas de cache) pour rester pilotable par l'environnement.
    """
    return _env_flag("LAURENTIA_ALLOW_DEMO_IDS")


def ephemeral_key_allowed() -> bool:
    """Clé de chiffrement éphémère autorisée (dev uniquement, LAURENTIA_ALLOW_EPHEMERAL_KEY=true)."""
    return _env_flag("LAURENTIA_ALLOW_EPHEMERAL_KEY")


def demote_role(role: str | None) -> str:
    """Retire tout rôle privilégié (founder/admin) d'une identité non vérifiée."""
    r = (role or "").strip().lower()
    if not r or r in PRIVILEGED_ROLES:
        return "member"
    return r


def cors_middleware_kwargs(cors_env: str | None) -> dict:
    """
    Paramètres CORSMiddleware.
    - CORS_ORIGINS absent / vide / contenant '*' → toute origine MAIS sans credentials
      (jamais de combinaison '*' + cookies).
    - CORS_ORIGINS='https://a,https://b' → ces origines explicites, avec credentials.
    """
    origins = [o.strip() for o in (cors_env or "").split(",") if o.strip()]
    if not origins or "*" in origins:
        return {
            "allow_credentials": False,
            "allow_origins": ["*"],
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    return {
        "allow_credentials": True,
        "allow_origins": origins,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
