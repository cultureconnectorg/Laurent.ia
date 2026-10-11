"""
passkey_auth.py — sign-in to Laurent.ia with a FREK-ID passkey (C1).

Laurent.ia is the WebAuthn relying party *mediator*: the browser runs the ceremony,
Laurent.ia relays it to FREKCORE through its authenticated API client, and FREKCORE
verifies challenge, origin and signature against the origin it was configured with.
Laurent.ia never reads FREKCORE's database and never sees a private key.

Single principal (LIA-D1): only LAURENTIA_PRINCIPAL_FREK_ID may register or sign in.

Enrollment (first passkey) is protected (security review, C1 fix): registration needs the
one-time enrollment token issued by deploy/scripts/frekcore-setup.sh (only its SHA-256 is
configured, LAURENTIA_ENROLLMENT_TOKEN_SHA256), and closes for good once the principal is
bound (stored in laurentia_settings). Without a configured token, registration is closed.
Nothing reaches FREKCORE before these checks.

Enrollment is reserved atomically by one ceremony (C1 fix 2). `begin` takes an exclusive,
expiring reservation in a single database operation (the document's unique _id makes a
concurrent reservation fail) and returns a ceremony lock; only that lock can `complete`,
once, and the claim is atomic too. States of the principal_enrollment document:
  open        → no ceremony in progress
  reserved    → a ceremony holds the lock until lock_until (LAURENTIA_ENROLLMENT_LOCK_TTL,
                default 300 s); an abandoned ceremony expires
  completing  → FREKCORE is being asked to store the key; never expires
  uncertain   → FREKCORE's answer was lost (5xx, timeout, crash): the key may or may not be
                stored, so enrollment stays locked (fail closed) until a passkey sign-in
                proves it happened
  completed   → closed for good
A refusal by FREKCORE (4xx) releases the reservation. Only the lock's SHA-256 is stored.

  POST /api/auth/passkey/register/begin     {frek_id, enrollment_token}                → options + enrollment_lock
  POST /api/auth/passkey/register/complete  {frek_id, enrollment_token, enrollment_lock,
                                             credential}                              → holder verified (notarized by FREKCORE)
  POST /api/auth/passkey/login/begin        {frek_id}             → WebAuthn request options
  POST /api/auth/passkey/login/complete     {frek_id, credential} → session cookie
  GET  /api/auth/passkey/proof              (signed in)           → FREKCORE proof of holder verification
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from routes.auth import COOKIE_NAME, SESSION_TTL_DAYS, require_user
from services import frekcore_client as fk

router = APIRouter(prefix="/api/auth/passkey", tags=["auth-passkey"])

PRINCIPAL_USER_ID = "principal"


class BeginRequest(BaseModel):
    frek_id: str = Field(min_length=3, max_length=160)


class CompleteRequest(BaseModel):
    frek_id: str = Field(min_length=3, max_length=160)
    credential: dict


class EnrollBeginRequest(BeginRequest):
    enrollment_token: str = Field(default="", max_length=256)


class EnrollCompleteRequest(CompleteRequest):
    enrollment_token: str = Field(default="", max_length=256)
    enrollment_lock: str = Field(default="", max_length=256)


ENROLLMENT_DOC = "principal_enrollment"
_ENROLL_REFUSED = "Inscription fermée ou code d'inscription invalide."
_ENROLL_BUSY = "Une inscription est déjà en cours ou son issue est inconnue."


async def _check_enrollment(request: Request, token: str) -> None:
    """Refuse unless enrollment is still open and the one-time token matches. Fails closed."""
    expected = os.environ.get("LAURENTIA_ENROLLMENT_TOKEN_SHA256", "").strip().lower()
    given = hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""
    if not expected or not given or not hmac.compare_digest(given, expected):
        raise HTTPException(403, _ENROLL_REFUSED)
    done = await request.app.state.db.laurentia_settings.find_one({"_id": ENROLLMENT_DOC})
    if done and done.get("completed"):
        raise HTTPException(403, _ENROLL_REFUSED)


def _principal() -> str:
    principal = os.environ.get("LAURENTIA_PRINCIPAL_FREK_ID", "").strip()
    if not principal:
        raise HTTPException(503, "Titulaire non configuré (LAURENTIA_PRINCIPAL_FREK_ID).")
    if not fk.configured():
        raise HTTPException(503, "FREKCORE non configuré.")
    return principal


def _only_principal(frek_id: str) -> str:
    principal = _principal()
    if frek_id.strip() != principal:
        # Same answer whatever the reason: do not reveal who the principal is.
        raise HTTPException(403, "Ce FREK-ID n'est pas autorisé sur cette instance.")
    return principal


def _http_error(e: fk.FrekcoreError) -> HTTPException:
    status = e.status if e.status in (400, 403, 404, 409) else 502
    return HTTPException(status, f"FREKCORE : {e.detail}")


async def _relay(coro):
    try:
        return await coro
    except fk.FrekcoreError as e:
        raise _http_error(e) from e


def _secure_cookie(request: Request) -> bool:
    # Secure everywhere except plain-HTTP localhost (a secure context for browsers).
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _lock_ttl() -> timedelta:
    try:
        return timedelta(seconds=max(1, int(os.environ.get("LAURENTIA_ENROLLMENT_LOCK_TTL", "300"))))
    except ValueError:
        return timedelta(seconds=300)


async def _reserve(db) -> str:
    """Take the enrollment for one ceremony, atomically. Raises 409 if another holds it."""
    lock = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    try:
        # Matches only an open or expired reservation; otherwise the upsert collides on _id.
        await db.laurentia_settings.update_one(
            {"_id": ENROLLMENT_DOC, "completed": {"$ne": True},
             "state": {"$nin": ["completing", "uncertain", "completed"]},
             "$or": [{"lock_until": {"$exists": False}}, {"lock_until": None}, {"lock_until": {"$lt": now}}]},
            {"$set": {"state": "reserved", "lock_hash": _sha256(lock), "lock_until": now + _lock_ttl()}},
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(409, _ENROLL_BUSY)
    return lock


async def _set_state(db, state: str, lock_hash: str | None = None) -> None:
    query = {"_id": ENROLLMENT_DOC}
    if lock_hash:
        query["lock_hash"] = lock_hash
    await db.laurentia_settings.update_one(
        query, {"$set": {"state": state}, "$unset": {"lock_hash": "", "lock_until": ""}})


@router.post("/register/begin")
async def register_begin(payload: EnrollBeginRequest, request: Request):
    frek_id = _only_principal(payload.frek_id)
    await _check_enrollment(request, payload.enrollment_token)
    db = request.app.state.db
    lock = await _reserve(db)
    try:
        options = await _relay(fk.passkey_register_begin(frek_id, display_name="Laurent"))
    except Exception:
        # A challenge alone stores nothing at FREKCORE: release on any failure.
        await _set_state(db, "open", _sha256(lock))
        raise
    return {**options, "enrollment_lock": lock}


@router.post("/register/complete")
async def register_complete(payload: EnrollCompleteRequest, request: Request):
    frek_id = _only_principal(payload.frek_id)
    await _check_enrollment(request, payload.enrollment_token)
    db = request.app.state.db
    if not payload.enrollment_lock:
        raise HTTPException(409, _ENROLL_BUSY)
    lock_hash = _sha256(payload.enrollment_lock)
    # Atomic claim: one live reservation, one completion.
    claimed = await db.laurentia_settings.update_one(
        {"_id": ENROLLMENT_DOC, "completed": {"$ne": True}, "state": "reserved",
         "lock_hash": lock_hash, "lock_until": {"$gte": datetime.now(timezone.utc)}},
        {"$set": {"state": "completing"}, "$unset": {"lock_until": ""}},
    )
    if claimed.modified_count != 1:
        raise HTTPException(409, _ENROLL_BUSY)
    try:
        result = await fk.passkey_register_complete(frek_id, payload.credential)
    except fk.FrekcoreError as e:
        if 400 <= e.status < 500:  # refused: nothing stored, the ceremony is over
            await _set_state(db, "open", lock_hash)
        else:
            await _set_state(db, "uncertain", lock_hash)
        raise _http_error(e) from e
    except Exception:
        # Answer lost (timeout, connection reset): fail closed. A cancelled request
        # leaves the state "completing", which never expires either.
        await _set_state(db, "uncertain", lock_hash)
        raise HTTPException(502, "FREKCORE : réponse perdue, inscription verrouillée.")
    if not result.get("ok"):
        await _set_state(db, "open", lock_hash)
        return {"ok": False, "holder_verified": bool(result.get("holder_verified"))}
    # Close enrollment for good; neither the token nor the lock is stored.
    await db.laurentia_settings.update_one(
        {"_id": ENROLLMENT_DOC},
        {"$set": {"completed": True, "state": "completed", "frek_id": frek_id,
                  "completed_at": datetime.now(timezone.utc).isoformat()},
         "$unset": {"lock_hash": "", "lock_until": ""}},
    )
    return {"ok": True, "holder_verified": bool(result.get("holder_verified"))}


@router.post("/login/begin")
async def login_begin(payload: BeginRequest):
    frek_id = _only_principal(payload.frek_id)
    return await _relay(fk.passkey_authenticate_begin(frek_id))


@router.post("/login/complete")
async def login_complete(payload: CompleteRequest, request: Request, response: Response):
    frek_id = _only_principal(payload.frek_id)
    result = await _relay(fk.passkey_authenticate_complete(frek_id, payload.credential))
    if not result.get("ok", True) or result.get("frek_id", frek_id) != frek_id:
        raise HTTPException(403, "Authentification FREKCORE refusée.")

    db = request.app.state.db
    now = datetime.now(timezone.utc)
    # A passkey sign-in proves the principal is enrolled: close enrollment if it was not
    # (e.g. FREKCORE's answer to register/complete was lost and the state is "uncertain").
    try:
        await db.laurentia_settings.update_one(
            {"_id": ENROLLMENT_DOC, "completed": {"$ne": True}},
            {"$set": {"completed": True, "state": "completed", "frek_id": frek_id,
                      "completed_at": now.isoformat(), "closed_by": "passkey_sign_in"},
             "$unset": {"lock_hash": "", "lock_until": ""}},
            upsert=True,
        )
    except DuplicateKeyError:
        pass  # already closed
    await db.users.update_one(
        {"user_id": PRINCIPAL_USER_ID},
        {"$set": {"frek_id": frek_id, "name": "Laurent", "email": "", "role": "principal",
                  "auth_method": "passkey", "last_login_at": now.isoformat()},
         "$setOnInsert": {"user_id": PRINCIPAL_USER_ID, "created_at": now.isoformat()}},
        upsert=True,
    )
    token = f"pk_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    await db.user_sessions.insert_one({
        "session_token": token, "user_id": PRINCIPAL_USER_ID, "auth_method": "passkey",
        "created_at": now.isoformat(), "expires_at": (now + timedelta(days=SESSION_TTL_DAYS)).isoformat(),
    })
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_TTL_DAYS * 24 * 3600, httponly=True,
                        secure=_secure_cookie(request), samesite="strict", path="/")
    return {"ok": True, "frek_id": frek_id}


@router.get("/proof")
async def holder_proof(user: dict = Depends(require_user)):
    """Proof, notarized by FREKCORE, that the principal's passkey was holder-verified."""
    if user.get("user_id") != PRINCIPAL_USER_ID:
        raise HTTPException(403, "Réservé au titulaire.")
    proof = await _relay(fk.proof(user["frek_id"]))
    chain = await _relay(fk.chain_verify())
    return {"frek_id": user["frek_id"], "proof": proof, "chain": chain}
