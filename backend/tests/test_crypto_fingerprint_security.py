"""Regression tests for Laurentia at-rest encryption and device fingerprints.

These tests use ephemeral test-only secrets. They never read Render secrets or
connect to MongoDB, and they must not print secret material.
"""
import base64
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def crypto_module(monkeypatch):
    monkeypatch.setenv("LAURENTIA_ENCRYPTION_KEY", "unit-test-encryption-key-never-use-in-production")
    import backend.services.crypto as crypto
    return importlib.reload(crypto)


@pytest.fixture
def fingerprint_module(monkeypatch):
    monkeypatch.setenv("LAURENTIA_SECRET_SALT", "unit-test-fingerprint-salt-never-use-in-production")
    import backend.services.fingerprint as fingerprint
    return importlib.reload(fingerprint)


def test_encrypt_decrypt_round_trip_and_storage_shape(crypto_module):
    plaintext = "Test Laurentia 2026 — données privées"
    blob = crypto_module.encrypt_text(plaintext)

    assert isinstance(blob, dict)
    assert blob["v"] == 1
    assert set(blob) == {"v", "n", "c"}
    nonce = base64.b64decode(blob["n"], validate=True)
    ciphertext = base64.b64decode(blob["c"], validate=True)
    assert len(nonce) == 12
    assert ciphertext != plaintext.encode("utf-8")
    assert crypto_module.is_encrypted(blob)
    assert crypto_module.decrypt_text(blob) == plaintext


def test_each_encryption_uses_a_fresh_nonce(crypto_module):
    first = crypto_module.encrypt_text("same plaintext")
    second = crypto_module.encrypt_text("same plaintext")
    assert first["n"] != second["n"]
    assert first["c"] != second["c"]


def test_wrong_key_fails_closed_without_plaintext(crypto_module, caplog):
    blob = crypto_module.encrypt_text("sensitive sentinel")
    crypto_module._AES = AESGCM(b"x" * 32)

    assert crypto_module.decrypt_text(blob) == ""
    assert "sensitive sentinel" not in caplog.text


def test_tampered_ciphertext_fails_closed(crypto_module):
    blob = crypto_module.encrypt_text("sensitive sentinel")
    raw = bytearray(base64.b64decode(blob["c"]))
    raw[-1] ^= 1
    blob["c"] = base64.b64encode(raw).decode("ascii")
    assert crypto_module.decrypt_text(blob) == ""


@pytest.mark.parametrize("value", [None, "", "legacy plaintext"])
def test_legacy_and_empty_values_remain_compatible(crypto_module, value):
    expected = "" if value is None else value
    assert crypto_module.decrypt_text(value) == expected


def test_unknown_or_malformed_blob_fails_closed(crypto_module):
    assert crypto_module.decrypt_text({"v": 2, "n": "x", "c": "y"}) == ""
    assert crypto_module.decrypt_text({"v": 1, "n": "not base64!", "c": "bad"}) == ""
    assert crypto_module.encrypt_text(None) is None
    assert not crypto_module.is_encrypted("legacy plaintext")


@pytest.mark.parametrize(
    ("module", "secret_name", "import_name"),
    [
        ("crypto", "LAURENTIA_ENCRYPTION_KEY", "backend.services.crypto"),
        ("fingerprint", "LAURENTIA_SECRET_SALT", "backend.services.fingerprint"),
    ],
)
def test_missing_required_secret_fails_at_import(module, secret_name, import_name):
    env = os.environ.copy()
    env.pop(secret_name, None)
    # Ensure the check is independent of a developer or CI runner's other secret.
    if module == "crypto":
        env.pop("LAURENTIA_ENCRYPTION_KEY", None)
    else:
        env.pop("LAURENTIA_SECRET_SALT", None)
    result = subprocess.run(
        [sys.executable, "-c", f"import {import_name}"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "obligatoire" in result.stderr or "required" in result.stderr.lower()


def test_default_secrets_are_rejected():
    cases = [
        ("LAURENTIA_ENCRYPTION_KEY", "mvp-encryption-placeholder-change-in-prod", "backend.services.crypto"),
        ("LAURENTIA_SECRET_SALT", "laurentia-mvp-salt-change-in-prod-7d3a9c", "backend.services.fingerprint"),
    ]
    for name, value, import_name in cases:
        env = os.environ.copy()
        env[name] = value
        result = subprocess.run(
            [sys.executable, "-c", f"import {import_name}"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "défaut" in result.stderr or "default" in result.stderr.lower()


def test_fingerprint_is_stable_opaque_and_input_bounded(fingerprint_module):
    raw_fingerprint = "device-fingerprint-test-123"
    first = fingerprint_module.device_id_from_fingerprint(raw_fingerprint)
    second = fingerprint_module.device_id_from_fingerprint(raw_fingerprint)

    assert first == second
    assert len(first) == 64
    assert raw_fingerprint not in first
    assert fingerprint_module.device_id_from_fingerprint(None) is None
    assert fingerprint_module.device_id_from_fingerprint("") is None
    assert fingerprint_module.device_id_from_fingerprint("short") is None
    assert fingerprint_module.device_id_from_fingerprint("x" * 4097) is None


def test_fingerprint_changes_with_salt(monkeypatch, fingerprint_module):
    value = "same-device-fingerprint-123"
    first = fingerprint_module.device_id_from_fingerprint(value)
    monkeypatch.setenv("LAURENTIA_SECRET_SALT", "a-different-test-only-salt")
    reloaded = importlib.reload(fingerprint_module)
    second = reloaded.device_id_from_fingerprint(value)
    assert first != second


def test_rate_limit_key_fallback_is_deterministic(fingerprint_module):
    first = fingerprint_module.resolve_limit_key("frek-user-1", None)
    second = fingerprint_module.resolve_limit_key("frek-user-1", None)
    assert first == second
    assert len(first) == 64
    assert fingerprint_module.resolve_limit_key(None, None) != first
