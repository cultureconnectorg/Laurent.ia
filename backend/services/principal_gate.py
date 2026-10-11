"""
principal_gate.py — deny-by-default access control for a deployed instance (C1/C2).

Laurent.ia V1 has a single principal (LIA-D1). In a deployed environment every /api
route requires the principal's session (passkey sign-in, routes/passkey_auth.py),
except the short explicit list below. In development and test the gate is off.
"""
from __future__ import annotations

import os

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
    return await call_next(request)
