"""C1 fix 2 — enrollment is reserved atomically by one WebAuthn ceremony.

Before: the "still open?" check read the database, FREKCORE was called, and the closure
was written only afterwards. Two concurrent ceremonies (double submission, or a leaked
code used at the same time) could both pass the check. Now `begin` takes an exclusive,
expiring reservation in one atomic database operation and returns a ceremony lock; only
that ceremony can `complete`, once. Failures are handled explicitly:
  - FREKCORE refuses (4xx)              -> reservation released, nothing closed
  - outcome unknown (5xx, timeout)      -> enrollment stays locked (fail closed); a
                                           successful passkey sign-in closes it
  - ceremony abandoned between the two  -> the reservation expires
                                           (LAURENTIA_ENROLLMENT_LOCK_TTL)
"""
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from pymongo import MongoClient

from _harness.fake_frekcore import FakeFrekcore

PRINCIPAL = "FREK-RACE-TEST"
TOKEN = "enrollment-token-for-race-tests-0123456789"
REFUSED = (403, 409)


def _db():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture
def frek(monkeypatch):
    _db().laurentia_settings.delete_many({"_id": "principal_enrollment"})
    with FakeFrekcore() as f:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("FREKCORE_API_URL", f.url)
        monkeypatch.setenv("FREKCORE_API_KEY", "x")
        monkeypatch.setenv("LAURENTIA_PRINCIPAL_FREK_ID", PRINCIPAL)
        monkeypatch.setenv("LAURENTIA_ENROLLMENT_TOKEN_SHA256", hashlib.sha256(TOKEN.encode()).hexdigest())
        monkeypatch.setenv("LAURENTIA_ENROLLMENT_LOCK_TTL", "300")
        from services import frekcore_client
        frekcore_client._token.update(value=None, expires=0.0)
        yield f
    _db().laurentia_settings.delete_many({"_id": "principal_enrollment"})


def _begin(client):
    return client.post("/api/auth/passkey/register/begin", json={"frek_id": PRINCIPAL, "enrollment_token": TOKEN})


def _complete(client, lock):
    body = {"frek_id": PRINCIPAL, "enrollment_token": TOKEN, "credential": {"id": "x"}}
    if lock is not None:
        body["enrollment_lock"] = lock
    return client.post("/api/auth/passkey/register/complete", json=body)


def _parallel(fn, n=6):
    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(lambda _: fn(), range(n)))


def _closed():
    doc = _db().laurentia_settings.find_one({"_id": "principal_enrollment"}) or {}
    return doc.get("completed") is True


def test_concurrent_begins_reserve_the_enrollment_once(app_client, frek):
    frek.delay["/register/begin"] = 0.5  # every request is in flight at the same time
    codes = [r.status_code for r in _parallel(lambda: _begin(app_client))]
    assert codes.count(200) == 1, codes
    assert all(c in REFUSED for c in codes if c != 200), codes
    assert frek.count("/register/begin") == 1


def test_complete_needs_the_lock_of_its_own_ceremony(app_client, frek):
    r = _begin(app_client)
    assert r.status_code == 200 and r.json().get("enrollment_lock")
    assert _complete(app_client, None).status_code in REFUSED
    assert _complete(app_client, "not-the-lock").status_code in REFUSED
    assert frek.count("/register/complete") == 0
    assert not _closed()


def test_concurrent_completes_reach_frekcore_once(app_client, frek):
    lock = _begin(app_client).json()["enrollment_lock"]
    frek.delay["/register/complete"] = 0.5
    codes = [r.status_code for r in _parallel(lambda: _complete(app_client, lock))]
    assert codes.count(200) == 1, codes
    assert all(c in REFUSED for c in codes if c != 200), codes
    assert frek.count("/register/complete") == 1
    assert _closed()


def test_double_submission_after_success_is_refused(app_client, frek):
    lock = _begin(app_client).json()["enrollment_lock"]
    assert _complete(app_client, lock).status_code == 200
    assert _complete(app_client, lock).status_code in REFUSED
    assert _begin(app_client).status_code in REFUSED
    assert frek.count("/register/complete") == 1 and frek.count("/register/begin") == 1


def test_interrupted_ceremony_blocks_others_then_expires(app_client, frek, monkeypatch):
    monkeypatch.setenv("LAURENTIA_ENROLLMENT_LOCK_TTL", "1")
    first = _begin(app_client).json()["enrollment_lock"]  # the browser never completes
    assert _begin(app_client).status_code in REFUSED
    time.sleep(1.5)
    r = _begin(app_client)
    assert r.status_code == 200
    second = r.json()["enrollment_lock"]
    assert second != first
    assert _complete(app_client, first).status_code in REFUSED  # stale ceremony
    assert frek.count("/register/complete") == 0
    assert _complete(app_client, second).status_code == 200
    assert _closed()


def test_frekcore_refusal_releases_the_reservation(app_client, frek):
    lock = _begin(app_client).json()["enrollment_lock"]
    frek.fail["/register/complete"] = 400  # e.g. invalid attestation
    assert _complete(app_client, lock).status_code == 400
    assert not _closed()
    assert _complete(app_client, lock).status_code in REFUSED  # that ceremony is over
    del frek.fail["/register/complete"]
    lock2 = _begin(app_client).json()["enrollment_lock"]  # immediately, no expiry wait
    assert _complete(app_client, lock2).status_code == 200


def test_frekcore_failure_at_begin_releases_the_reservation(app_client, frek):
    frek.fail["/register/begin"] = 400
    assert _begin(app_client).status_code == 400
    del frek.fail["/register/begin"]
    assert _begin(app_client).status_code == 200


def test_unknown_outcome_keeps_enrollment_locked_even_after_expiry(app_client, frek, monkeypatch):
    monkeypatch.setenv("LAURENTIA_ENROLLMENT_LOCK_TTL", "1")
    lock = _begin(app_client).json()["enrollment_lock"]
    frek.fail["/register/complete"] = 500  # FREKCORE may or may not have stored the key
    assert _complete(app_client, lock).status_code == 502
    del frek.fail["/register/complete"]
    time.sleep(1.5)
    assert _begin(app_client).status_code in REFUSED
    assert frek.count("/register/begin") == 1
    assert not _closed()


def test_sign_in_with_a_passkey_closes_an_unknown_enrollment(app_client, frek):
    lock = _begin(app_client).json()["enrollment_lock"]
    frek.fail["/register/complete"] = 500
    _complete(app_client, lock)
    del frek.fail["/register/complete"]
    # The key did reach FREKCORE: Laurent signs in with it, which proves enrollment happened.
    assert app_client.post("/api/auth/passkey/login/begin", json={"frek_id": PRINCIPAL}).status_code == 200
    r = app_client.post("/api/auth/passkey/login/complete", json={"frek_id": PRINCIPAL, "credential": {"id": "x"}})
    assert r.status_code == 200
    assert _closed()
    # Leave no principal behind for other tests (the gate would ask FREKCORE about it).
    app_client.cookies.clear()
    _db().user_sessions.delete_many({"user_id": "principal"})
    _db().users.delete_many({"user_id": "principal"})


def test_the_lock_is_never_stored_in_clear(app_client, frek):
    lock = _begin(app_client).json()["enrollment_lock"]
    doc = _db().laurentia_settings.find_one({"_id": "principal_enrollment"})
    assert lock not in str(doc) and TOKEN not in str(doc)
