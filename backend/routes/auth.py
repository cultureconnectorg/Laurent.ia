"""
auth.py — Google OpenID Connect and local session management.

Endpoints (/api/auth/*):
- GET  /api/auth/google/start                 — begin Google OIDC
- GET  /api/auth/google/callback              — verify state, exchange code, issue local session
- GET  /api/auth/me                           — return current user (cookie or Bearer)
- POST /api/auth/logout                       — clear cookie + delete DB session
"""
from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services import frekcore_bridge

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
GOOGLE_STATE_COOKIE = "google_oauth_state"
SESSION_TTL_DAYS = 7
COOKIE_NAME = "session_token"


def _is_explicit_development() -> bool:
    markers = (
        os.environ.get("LAURENTIA_ENV", ""),
        os.environ.get("APP_ENV", ""),
        os.environ.get("ENVIRONMENT", ""),
        os.environ.get("NODE_ENV", ""),
        os.environ.get("VERCEL_ENV", ""),
        os.environ.get("RAILWAY_ENVIRONMENT", ""),
    )
    values = {value.strip().lower() for value in markers if value.strip()}
    return bool(values & {"dev", "development", "local", "test", "testing"}) and not bool(
        values & {"prod", "production"}
    )


router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------- Schemas ----------------

class FrekLoginRequest(BaseModel):
    frek_id: str


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str | None = None
    frek_id: str


# ---------------- Helpers ----------------

def _derive_frek_id(email: str) -> str:
    """FREK-G-{first 10 chars of sha256(email)}. Stable across logins."""
    h = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:10]
    return f"FREK-G-{h}"


async def _get_token(
    session_token_cookie: str | None,
    authorization: str | None,
) -> str | None:
    """Cookie first, then Authorization: Bearer."""
    if session_token_cookie:
        return session_token_cookie
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def _resolve_session(db, session_token: str) -> dict | None:
    """Returns user dict if session is valid, else None."""
    sess = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not sess:
        return None
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    return user


async def get_current_user(request: Request) -> dict | None:
    """Optional auth — returns user dict or None."""
    token = await _get_token(
        request.cookies.get(COOKIE_NAME),
        request.headers.get("authorization"),
    )
    if not token:
        return None
    return await _resolve_session(request.app.state.db, token)


async def require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Non authentifié")
    return user


# ---------------- Endpoints ----------------

def _google_oauth_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI and FRONTEND_URL)


def _frontend_auth_redirect(status: str) -> RedirectResponse:
    # FRONTEND_URL is an operator-controlled environment value, never request input.
    return RedirectResponse(url=f"{FRONTEND_URL}/#auth={status}", status_code=303)


@router.get("/google/start")
async def google_oauth_start():
    """Start Google OpenID Connect directly; no third-party auth broker."""
    if not _google_oauth_configured():
        raise HTTPException(
            status_code=503,
            detail="Connexion Google non configurée : définir GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI et FRONTEND_URL.",
        )
    state = secrets.token_urlsafe(32)
    params = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    response = RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        status_code=302,
    )
    response.set_cookie(
        key=GOOGLE_STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth/google",
    )
    return response


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=GOOGLE_STATE_COOKIE),
):
    """Validate Google OAuth state, exchange code, verify email, and issue a local session."""
    if not _google_oauth_configured():
        raise HTTPException(status_code=503, detail="Connexion Google non configurée")
    if error or not code or not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
        response = _frontend_auth_redirect("error")
        response.delete_cookie(GOOGLE_STATE_COOKIE, path="/api/auth/google", secure=True, samesite="lax")
        return response

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("Google n'a pas retourné de jeton d'accès")
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
    except (httpx.HTTPError, ValueError):
        response = _frontend_auth_redirect("error")
        response.delete_cookie(GOOGLE_STATE_COOKIE, path="/api/auth/google", secure=True, samesite="lax")
        return response

    email = (profile.get("email") or "").strip().lower()
    if not email or profile.get("email_verified") is not True or not profile.get("sub"):
        response = _frontend_auth_redirect("error")
        response.delete_cookie(GOOGLE_STATE_COOKIE, path="/api/auth/google", secure=True, samesite="lax")
        return response

    db = request.app.state.db
    name = (profile.get("name") or email.split("@")[0] or "Hôte").strip()
    picture = profile.get("picture")
    frek_id = _derive_frek_id(email)
    now_iso = datetime.now(timezone.utc).isoformat()

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture, "last_login": now_iso, "frek_id": frek_id}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "frek_id": frek_id,
            "created_at": now_iso,
            "last_login": now_iso,
            "auth_provider": "google",
            "google_sub": profile["sub"],
        })

    instance = await db.laurentia_instances.find_one({"frek_id": frek_id}, {"_id": 0})
    if not instance:
        await db.laurentia_instances.insert_one({
            "frek_id": frek_id,
            "tenant_path": f"/users/{frek_id}",
            "version": "free",
            "created_at": now_iso,
            "last_active": now_iso,
            "tokens_used_month": 0,
            "tokens_limit_month": 10000,
            "jcc_balance": 0,
            "stripe_customer_id": None,
            "status": "active",
            "encryption_key_ref": f"ref::{frek_id[-8:]}",
        })
        await db.laurentia_memory.update_one(
            {"frek_id": frek_id},
            {"$setOnInsert": {
                "frek_id": frek_id,
                "sessions": [],
                "long_term": {"facts": [], "preferences": {}, "projects": [], "people": []},
                "cultural_profile": {},
                "updated_at": now_iso,
            }},
            upsert=True,
        )

    session_token = f"google_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso,
        "auth_method": "google",
    })

    response = _frontend_auth_redirect("success")
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    response.delete_cookie(GOOGLE_STATE_COOKIE, path="/api/auth/google", secure=True, samesite="lax")
    return response


@router.get("/me")
async def me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Non authentifié")
    # Enrichit avec l'état du tier depuis l'instance
    db = request.app.state.db
    inst = await db.laurentia_instances.find_one({"frek_id": user["frek_id"]}, {"_id": 0}) or {}
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "frek_id": user["frek_id"],
        "role": user.get("role"),
        "ecosystem_member": bool(user.get("ecosystem_member", False)),
        "tier": inst.get("tier") or inst.get("version") or "free",
        "tokens_used_month": int(inst.get("tokens_used_month", 0)),
        "tokens_limit_month": int(inst.get("tokens_limit_month", 100_000)),
    }


@router.post("/frek")
async def login_with_frek_id(payload: FrekLoginRequest, request: Request, response: Response):
    """
    Connexion directe via un FREK-ID existant (membre de l'écosystème).
    Valide auprès du service frekcore (mocké en dev, HTTP en prod).
    """
    # A FREK-ID is an identifier, not proof that the caller controls the identity.
    # Until a signed challenge/passkey flow exists, production login by ID alone is denied.
    if not _is_explicit_development():
        raise HTTPException(
            status_code=403,
            detail="Connexion par FREK-ID seul désactivée : une preuve de possession vérifiable est requise.",
        )

    db = request.app.state.db
    raw = (payload.frek_id or "").strip().upper()
    if not raw or len(raw) < 4:
        raise HTTPException(400, "FREK-ID invalide")

    validation = await frekcore_bridge.validate_frek_id(raw)
    if not validation.get("valid"):
        raise HTTPException(404, "FREK-ID non reconnu")

    profile = await frekcore_bridge.get_profile(raw)
    frek_id = validation.get("frek_id", raw)
    first_name = profile.get("first_name") or raw.split("-")[-1].capitalize()
    role = validation.get("role") or profile.get("role") or "member"
    picture = profile.get("picture")
    email = profile.get("email") or f"{frek_id.lower()}@frekcore.local"

    now_iso = datetime.now(timezone.utc).isoformat()

    # Upsert user (clé = frek_id pour les membres écosystème)
    existing = await db.users.find_one({"frek_id": frek_id}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"frek_id": frek_id},
            {"$set": {"name": first_name, "picture": picture, "role": role, "last_login": now_iso}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": first_name,
            "picture": picture,
            "frek_id": frek_id,
            "role": role,
            "ecosystem_member": True,  # flag pour réactiver la couche écosystème dans l'UI
            "created_at": now_iso,
            "last_login": now_iso,
        })

    # Upsert instance Laurent.ia
    inst = await db.laurentia_instances.find_one({"frek_id": frek_id}, {"_id": 0})
    if not inst:
        await db.laurentia_instances.insert_one({
            "frek_id": frek_id,
            "tenant_path": f"/users/{frek_id}",
            "version": "free",
            "created_at": now_iso,
            "last_active": now_iso,
            "tokens_used_month": 0,
            "tokens_limit_month": 10000,
            "jcc_balance": int((profile.get("wallet") or {}).get("jcc_balance", 0)),
            "status": "active",
            "encryption_key_ref": f"ref::{frek_id[-8:]}",
        })
        await db.laurentia_memory.insert_one({
            "frek_id": frek_id,
            "sessions": [],
            "long_term": {"facts": [], "preferences": {}, "projects": [], "people": []},
            "cultural_profile": profile.get("cultural_profile", {}),
            "updated_at": now_iso,
        })

    # Crée la session
    session_token = f"frek_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso,
        "auth_method": "frek",
    })

    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    return {
        "ok": True,
        "user": {
            "user_id": user_id,
            "email": email,
            "name": first_name,
            "picture": picture,
            "frek_id": frek_id,
            "role": role,
            "ecosystem_member": True,
        },
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    authorization: str | None = Header(default=None),
):
    token = await _get_token(session_token, authorization)
    if token:
        await request.app.state.db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="none")
    return {"ok": True}


class MigrateAnonRequest(BaseModel):
    anon_frek_id: str


@router.post("/migrate-anon")
async def migrate_anon(payload: MigrateAnonRequest, request: Request):
    """
    Refuse la migration tant que le serveur ne peut pas prouver la possession
    du tenant invité source. Un FREK-ID ANON fourni par le client n'est pas
    une preuve d'identité : le migrer directement permettrait de réattribuer
    les interactions d'un autre invité.
    """
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Non authentifié")
    anon = (payload.anon_frek_id or "").strip().upper()
    if not anon.startswith("ANON-"):
        raise HTTPException(400, "FREK-ID invité invalide")
    raise HTTPException(
        409,
        "Migration invitée temporairement désactivée : une preuve de possession du tenant source est requise.",
    )
