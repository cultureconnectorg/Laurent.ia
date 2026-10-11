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

  POST /api/auth/passkey/register/begin     {frek_id}             → WebAuthn creation options
  POST /api/auth/passkey/register/complete  {frek_id, credential} → holder verified (notarized by FREKCORE)
  POST /api/auth/passkey/login/begin        {frek_id}             → WebAuthn request options
  POST /api/auth/passkey/login/complete     {frek_id, credential} → session cookie
  GET  /api/auth/passkey/proof              (signed in)           → FREKCORE proof of holder verification
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

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


ENROLLMENT_DOC = "principal_enrollment"
_ENROLL_REFUSED = "Inscription fermée ou code d'inscription invalide."


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


async def _relay(coro):
    try:
        return await coro
    except fk.FrekcoreError as e:
        status = e.status if e.status in (400, 403, 404, 409) else 502
        raise HTTPException(status, f"FREKCORE : {e.detail}") from e


def _secure_cookie(request: Request) -> bool:
    # Secure everywhere except plain-HTTP localhost (a secure context for browsers).
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


@router.post("/register/begin")
async def register_begin(payload: EnrollBeginRequest, request: Request):
    frek_id = _only_principal(payload.frek_id)
    await _check_enrollment(request, payload.enrollment_token)
    return await _relay(fk.passkey_register_begin(frek_id, display_name="Laurent"))


@router.post("/register/complete")
async def register_complete(payload: EnrollCompleteRequest, request: Request):
    frek_id = _only_principal(payload.frek_id)
    await _check_enrollment(request, payload.enrollment_token)
    result = await _relay(fk.passkey_register_complete(frek_id, payload.credential))
    if result.get("ok"):
        # Close enrollment for good; the token itself is never stored.
        await request.app.state.db.laurentia_settings.update_one(
            {"_id": ENROLLMENT_DOC},
            {"$set": {"completed": True, "frek_id": frek_id,
                      "completed_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    return {"ok": bool(result.get("ok")), "holder_verified": bool(result.get("holder_verified"))}


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
