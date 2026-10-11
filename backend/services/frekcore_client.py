"""
frekcore_client.py — Laurent.ia's only door to FREKCORE (C1).

FREKCORE owns identity (FREK-ID), passkeys (WebAuthn) and proofs (notary).
Laurent.ia never touches FREKCORE's database: it is an authenticated API client
(`client_credentials`, client id `cvl-brain`) whose rights are the permissions that
FREKCORE grants it explicitly (see deploy/scripts/frekcore-grant.sh).

Configuration:
  FREKCORE_API_URL        FREKCORE base URL (e.g. http://frekcore:8001, internal network)
  FREKCORE_CLIENT_ID      client id (default "cvl-brain")
  FREKCORE_API_KEY        client secret issued for this client
  FREKCORE_TIMEOUT        seconds (default 10)
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx


class FrekcoreError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"FREKCORE {status}: {detail}")
        self.status = status
        self.detail = detail


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def configured() -> bool:
    return bool(_env("FREKCORE_API_URL") and _env("FREKCORE_API_KEY"))


_token: dict[str, Any] = {"value": None, "expires": 0.0}


def _base() -> str:
    url = _env("FREKCORE_API_URL").rstrip("/")
    if not url:
        raise FrekcoreError(503, "FREKCORE_API_URL non configuré")
    return url


def _timeout() -> float:
    try:
        return float(_env("FREKCORE_TIMEOUT", "10"))
    except ValueError:
        return 10.0


async def _access_token(client: httpx.AsyncClient, *, force: bool = False) -> str:
    if not force and _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    r = await client.post(f"{_base()}/api/v1/auth/token", json={
        "grant_type": "client_credentials",
        "client_id": _env("FREKCORE_CLIENT_ID", "cvl-brain"),
        "client_secret": _env("FREKCORE_API_KEY"),
    })
    if r.status_code != 200:
        raise FrekcoreError(r.status_code, _detail(r))
    data = r.json()
    _token["value"] = data["access_token"]
    _token["expires"] = time.time() + float(data.get("expires_in", 3600))
    return _token["value"]


def _detail(r: httpx.Response) -> str:
    try:
        d = r.json().get("detail")
        return d if isinstance(d, str) else str(d)
    except Exception:
        return r.text[:200]


async def _call(method: str, path: str, *, json: dict | None = None, auth: bool = True) -> Any:
    async with httpx.AsyncClient(timeout=_timeout()) as client:
        headers = {"Authorization": f"Bearer {await _access_token(client)}"} if auth else {}
        r = await client.request(method, f"{_base()}{path}", json=json, headers=headers)
        if r.status_code == 401 and auth:  # token revoked or expired: one retry with a new token
            headers = {"Authorization": f"Bearer {await _access_token(client, force=True)}"}
            r = await client.request(method, f"{_base()}{path}", json=json, headers=headers)
    if r.status_code >= 400:
        raise FrekcoreError(r.status_code, _detail(r))
    return r.json()


# ---- identity ----
async def identity_status(frek_id: str) -> dict:
    return await _call("GET", f"/api/v1/identity/{frek_id}/status", auth=False)


async def identity_detail(frek_id: str) -> dict:
    return await _call("GET", f"/api/v1/identity/{frek_id}/detail")


async def emit_identity(email: str, source: str = "laurentia") -> dict:
    return await _call("POST", "/api/v1/identity/emit", json={"email": email, "source": source})


async def revoke_identity(frek_id: str, reason: str) -> dict:
    return await _call("POST", f"/api/v1/identity/{frek_id}/revoke", json={"reason": reason})


# ---- passkeys (WebAuthn, mediated: FREKCORE checks the origin it was configured with) ----
_PK = "/api/v1/identity-client/passkeys"


async def passkey_register_begin(frek_id: str, display_name: str | None = None) -> dict:
    return await _call("POST", f"{_PK}/register/begin", json={"frek_id": frek_id, "display_name": display_name})


async def passkey_register_complete(frek_id: str, credential: dict) -> dict:
    return await _call("POST", f"{_PK}/register/complete", json={"frek_id": frek_id, "credential": credential})


async def passkey_authenticate_begin(frek_id: str) -> dict:
    return await _call("POST", f"{_PK}/authenticate/begin", json={"frek_id": frek_id})


async def passkey_authenticate_complete(frek_id: str, credential: dict) -> dict:
    return await _call("POST", f"{_PK}/authenticate/complete", json={"frek_id": frek_id, "credential": credential})


# ---- proofs (FREKCORE notary) ----
async def proof(payload_id: str) -> dict:
    return await _call("GET", f"/api/v1/notary/proof/{payload_id}", auth=False)


async def chain_verify() -> dict:
    return await _call("GET", "/api/v1/notary/chain/verify", auth=False)
