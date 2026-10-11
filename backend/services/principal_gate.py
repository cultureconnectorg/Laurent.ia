"""
principal_gate.py — deny-by-default access control for a deployed instance (C1/C2).

Laurent.ia V1 has a single principal (LIA-D1). In a deployed environment every /api
route requires the principal's session (passkey sign-in, routes/passkey_auth.py),
except the short explicit list below. In development and test the gate is off.
"""
from __future__ import annotations

import os
import time

from fastapi import Request
from fastapi.responses import JSONResponse

# (method, path or prefix ending with "/") reachable without the principal's session.
PUBLIC = {
    ("GET", "/api/"),
    ("GET", "/api/health"),
    ("GET", "/api/brain/health"),
    ("GET", "/api/auth/me"),            # answers 401 when not signed in
    ("POST", "/api/auth/logout"),
    ("POST", "/api/brain/briefing"),    # machine-to-machine, own service-key check (laurentia.briefing@1.0)
    ("POST", "/api/auth/passkey/register/"),
    ("POST", "/api/auth/passkey/login/"),
}


# FREK-ID status cache: a revocation in FREKCORE closes the session within this delay.
STATUS_TTL_SECONDS = int(os.environ.get("LAURENTIA_IDENTITY_STATUS_TTL", "60"))
_status_cache: dict[str, tuple[float, bool]] = {}


async def identity_still_valid(frek_id: str) -> bool:
    """Ask FREKCORE (cached) whether the principal's FREK-ID is still valid. Fails closed."""
    now = time.time()
    hit = _status_cache.get(frek_id)
    if hit and now - hit[0] < STATUS_TTL_SECONDS:
        return hit[1]
    from services import frekcore_client

    try:
        st = await frekcore_client.identity_status(frek_id)
        ok = bool(st.get("active")) and not st.get("revoked") and not st.get("expired")
    except Exception:
        ok = False  # FREKCORE unreachable: no new decision without it
    _status_cache[frek_id] = (now, ok)
    return ok


def deployed() -> bool:
    return (os.environ.get("APP_ENV") or "production").strip().lower() not in ("development", "test")


def is_public(method: str, path: str) -> bool:
    for m, p in PUBLIC:
        if m == method and (path == p or (p.endswith("/") and path.startswith(p) and p != "/api/")):
            return True
    return False


async def principal_gate(request: Request, call_next):
    path = request.url.path
    if not deployed() or not path.startswith("/api") or request.method == "OPTIONS" or is_public(request.method, path):
        return await call_next(request)
    from routes.auth import get_current_user  # late import: avoids an import cycle at startup

    user = await get_current_user(request)
    if not user or user.get("user_id") != "principal":
        return JSONResponse({"detail": "Connexion requise (passkey FREK-ID du titulaire)."}, status_code=401)
    if user.get("auth_method") == "passkey" and not await identity_still_valid(user.get("frek_id", "")):
        await request.app.state.db.user_sessions.delete_many({"user_id": "principal"})
        return JSONResponse({"detail": "FREK-ID révoqué ou invalide dans FREKCORE : session fermée."}, status_code=401)
    return await call_next(request)
