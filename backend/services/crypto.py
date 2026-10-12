"""
crypto.py — Chiffrement symétrique AES-256-GCM pour la mémoire utilisateur.

Format de stockage (dict, sérialisable BSON) :
    {"v": 1, "n": <nonce_b64>, "c": <ciphertext_b64>}

Clé : SHA-256(LAURENTIA_ENCRYPTION_KEY) → 32 bytes (AES-256).
Le sel `LAURENTIA_SECRET_SALT` est figé en .env pour éviter les tokens orphelins
au reboot du pod (tenant_id stable). La clé de chiffrement doit elle aussi être
figée — sinon TOUTE la mémoire historique devient illisible.

Sécurité :
  - AES-GCM authentifié, nonce 96 bits aléatoire par chiffrement.
  - Rétro-compat : un champ stocké en str (legacy plaintext) est renvoyé tel quel
    par decrypt_text() — permet une migration progressive sans casser l'app.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class EncryptionKeyMissing(RuntimeError):
    """LAURENTIA_ENCRYPTION_KEY absente : refus de chiffrer/déchiffrer (fail closed)."""


# Ancienne valeur de repli codée en dur (publique) — refusée explicitement.
_FORBIDDEN_KEYS = {"mvp-encryption-placeholder-change-in-prod"}

_AES: AESGCM | None = None


def _load_aes() -> AESGCM:
    """
    Construit la clé AES-256 à la première utilisation.
    - LAURENTIA_ENCRYPTION_KEY définie (et différente de l'ancien placeholder) → SHA-256.
    - Absente + LAURENTIA_ALLOW_EPHEMERAL_KEY=true → clé aléatoire éphémère
      (dev uniquement : la mémoire chiffrée est perdue au redémarrage).
    - Sinon → EncryptionKeyMissing (fail closed). Jamais de constante en code.
    """
    global _AES
    if _AES is not None:
        return _AES
    from services.security import ephemeral_key_allowed

    raw = os.environ.get("LAURENTIA_ENCRYPTION_KEY", "").strip()
    if raw and raw not in _FORBIDDEN_KEYS:
        key = hashlib.sha256(raw.encode("utf-8")).digest()
    elif ephemeral_key_allowed():
        logger.warning(
            "LAURENTIA_ENCRYPTION_KEY absente — clé ÉPHÉMÈRE aléatoire (dev uniquement, "
            "données illisibles après redémarrage)."
        )
        key = os.urandom(32)
    else:
        raise EncryptionKeyMissing(
            "LAURENTIA_ENCRYPTION_KEY absente ou invalide : chiffrement refusé. "
            "Définir la variable (ou LAURENTIA_ALLOW_EPHEMERAL_KEY=true en dev)."
        )
    _AES = AESGCM(key)
    return _AES


def ensure_key() -> None:
    """Vérification au démarrage : lève EncryptionKeyMissing si la clé manque."""
    _load_aes()


def encrypt_text(plaintext: str | None) -> dict | None:
    """
    Chiffre un texte UTF-8. Retourne un dict stockable en MongoDB.
    None → None (aucun chiffrement d'absence).
    """
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        plaintext = str(plaintext)
    nonce = os.urandom(12)
    ct = _load_aes().encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "v": 1,
        "n": base64.b64encode(nonce).decode("ascii"),
        "c": base64.b64encode(ct).decode("ascii"),
    }


def decrypt_text(blob) -> str:
    """
    Déchiffre. Accepte :
      - dict {v:1, n, c} → AES-GCM décrypté
      - str (legacy plaintext non chiffré) → renvoyé tel quel
      - None → ""
    En cas d'échec cryptographique : log + renvoi vide (jamais d'exception
    propagée au client — un message corrompu ne doit pas bloquer toute la session).
    """
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    if not isinstance(blob, dict) or blob.get("v") != 1:
        return ""
    aes = _load_aes()  # EncryptionKeyMissing propagée : jamais de déchiffrement sans clé
    try:
        nonce = base64.b64decode(blob["n"])
        ct = base64.b64decode(blob["c"])
        return aes.decrypt(nonce, ct, None).decode("utf-8")
    except Exception as e:
        logger.warning("decrypt_text failed: %s", e)
        return ""


def is_encrypted(blob) -> bool:
    return isinstance(blob, dict) and blob.get("v") == 1
