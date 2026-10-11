"""C1 fix — the first passkey of the principal can only be registered with the
one-time enrollment token issued at setup, and registration closes for good once
the principal is bound. Nothing reaches FREKCORE without a valid token.
"""
import hashlib
import os

import pytest
from pymongo import MongoClient

from _harness.fake_frekcore import FakeFrekcore

PRINCIPAL = "FREK-ENRL-TEST"
TOKEN = "enrollment-token-for-tests-0123456789abcdef"


@pytest.fixture
def frek(monkeypatch):
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    db.laurentia_settings.delete_many({"_id": "principal_enrollment"})
    with FakeFrekcore() as f:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("FREKCORE_API_URL", f.url)
        monkeypatch.setenv("FREKCORE_API_KEY", "x")
        monkeypatch.setenv("LAURENTIA_PRINCIPAL_FREK_ID", PRINCIPAL)
        monkeypatch.setenv("LAURENTIA_ENROLLMENT_TOKEN_SHA256", hashlib.sha256(TOKEN.encode()).hexdigest())
        from services import frekcore_client
        frekcore_client._token.update(value=None, expires=0.0)
        yield f
    db.laurentia_settings.delete_many({"_id": "principal_enrollment"})


def _begin(client, token=None):
    body = {"frek_id": PRINCIPAL}
    if token is not None:
        body["enrollment_token"] = token
    return client.post("/api/auth/passkey/register/begin", json=body)


def _complete(client, token=None, lock=None):
    body = {"frek_id": PRINCIPAL, "credential": {"id": "x"}}
    if token is not None:
        body["enrollment_token"] = token
    if lock is not None:
        body["enrollment_lock"] = lock  # the reservation of this ceremony (C1 fix 2)
    return client.post("/api/auth/passkey/register/complete", json=body)


def test_registration_without_token_is_refused_before_frekcore(app_client, frek):
    assert _begin(app_client).status_code == 403
    assert _complete(app_client).status_code == 403
    assert frek.count("/register/begin") == 0 and frek.count("/register/complete") == 0


def test_registration_with_a_wrong_token_is_refused_before_frekcore(app_client, frek):
    assert _begin(app_client, "not-the-token").status_code == 403
    assert _complete(app_client, "not-the-token").status_code == 403
    assert frek.count("/register/begin") == 0 and frek.count("/register/complete") == 0


def test_registration_is_closed_when_no_enrollment_token_is_configured(app_client, frek, monkeypatch):
    monkeypatch.delenv("LAURENTIA_ENROLLMENT_TOKEN_SHA256", raising=False)
    assert _begin(app_client, TOKEN).status_code == 403
    assert frek.count("/register/begin") == 0


def test_valid_token_enrolls_once_then_registration_closes(app_client, frek):
    r = _begin(app_client, TOKEN)
    assert r.status_code == 200
    assert _complete(app_client, TOKEN, r.json()["enrollment_lock"]).status_code == 200
    # The same token, a second time: closed. FREKCORE is not even asked.
    before = frek.count("/register/begin")
    assert _begin(app_client, TOKEN).status_code == 403
    assert _complete(app_client, TOKEN).status_code == 403
    assert frek.count("/register/begin") == before


def test_closure_is_stored_in_the_database_not_in_memory(app_client, frek):
    lock = _begin(app_client, TOKEN).json()["enrollment_lock"]
    _complete(app_client, TOKEN, lock)
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    doc = db.laurentia_settings.find_one({"_id": "principal_enrollment"})
    assert doc and doc.get("completed") is True and doc.get("frek_id") == PRINCIPAL
    assert TOKEN not in str(doc)  # the token itself is never stored


def test_sign_in_routes_are_unchanged_by_enrollment(app_client, frek):
    # Sign-in never needs the enrollment token (it proves possession of the passkey).
    r = app_client.post("/api/auth/passkey/login/begin", json={"frek_id": PRINCIPAL})
    assert r.status_code != 403
