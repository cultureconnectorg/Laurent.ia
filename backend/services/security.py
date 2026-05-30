"""Helpers sécurité — tenant_id hashing."""
from __future__ import annotations

import hashlib
import os

SALT = os.environ.get("LAURENTIA_SECRET_SALT", "")


def tenant_id_for(frek_id: str) -> str:
    """SHA-256(frek_id + SALT). Jamais de frek_id en clair dans les logs."""
    return hashlib.sha256(f"{frek_id}{SALT}".encode("utf-8")).hexdigest()
