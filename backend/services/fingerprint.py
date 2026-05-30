"""
fingerprint.py — Génère un `device_id` HMAC-SHA256 irréversible à partir d'une
empreinte matérielle envoyée par le frontend via le header `X-Device-Fingerprint`.

Sel : LAURENTIA_SECRET_SALT (le même qui sert à tenant_id_for, donc figé en .env).

Rule : la valeur en clair ne fuit jamais dans les logs ni en base. Seul le
device_id (64 hex chars) circule. C'est l'équivalent souverain de l'Apple ID
silencieux : reconnaissance sans mot de passe, anonymat préservé.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_SALT = "laurentia-mvp-salt-change-in-prod-7d3a9c"
_SALT_RAW = os.environ.get("LAURENTIA_SECRET_SALT", _DEFAULT_SALT).strip() or _DEFAULT_SALT
_SALT_BYTES = _SALT_RAW.encode("utf-8")

if _SALT_RAW == _DEFAULT_SALT:
    logger.warning("LAURENTIA_SECRET_SALT = valeur par défaut — change-la en prod.")


def device_id_from_fingerprint(fingerprint: str | None) -> str | None:
    """
    HMAC-SHA256(salt, fingerprint) → 64 hex.
    None / vide → None (le caller décide alors du fallback frek_id).
    """
    if not fingerprint:
        return None
    fp = fingerprint.strip()
    if len(fp) < 8 or len(fp) > 4096:
        return None
    return hmac.new(_SALT_BYTES, fp.encode("utf-8"), hashlib.sha256).hexdigest()


def resolve_limit_key(frek_id: str | None, device_id: str | None) -> str:
    """
    Clé de rate-limit prioritaire :
      1) device_id si fourni (cas par défaut — anonymes & connectés)
      2) sinon hash du frek_id (compat ancienne)
    Toujours retourne 64 hex.
    """
    if device_id:
        return device_id
    fallback = (frek_id or "anon").encode("utf-8")
    return hashlib.sha256(_SALT_BYTES + b":" + fallback).hexdigest()
