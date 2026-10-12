"""
Tests — correctifs sécurité critiques (branche claude/security-critical-auth-20261012).

Couvre :
  1. DEMO-* refusés sans LAURENTIA_ALLOW_DEMO_IDS, jamais founder/admin.
  2. Bridge Kiltikonet non configuré → fail closed (sauf ANON-* / mode dev).
  3. POST /api/auth/frek désactivé sans mode dev.
  4. POST /api/admin/rgpd/purge réservé founder/admin.
  5. /api/brain/chat-enriched et /api/omega/chat-enriched exigent une session.
  6. instances / memory / sessions : contrôle d'appartenance du FREK-ID.
  7. Clé de chiffrement : fail closed sans LAURENTIA_ENCRYPTION_KEY.
  8. Webhook SMS OVH : secret partagé obligatoire.
  9. CORS : jamais '*' + credentials.

Utilise FastAPI TestClient et une base MongoDB de test (TEST_MONGO_URL,
défaut mongodb://localhost:27018). Les tests HTTP sont ignorés si la base
est injoignable ; les tests unitaires tournent toujours.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest

# --- Stub emergentintegrations si non installable (wheel privée) -------------
try:  # pragma: no cover - dépend de l'environnement
    import emergentintegrations.llm.chat  # noqa: F401
except Exception:  # pragma: no cover
    ei = types.ModuleType("emergentintegrations")
    llm = types.ModuleType("emergentintegrations.llm")
    chat = types.ModuleType("emergentintegrations.llm.chat")

    class _LlmChat:  # minimal stub
        def __init__(self, *a, **k):
            pass

        def with_model(self, *a, **k):
            return self

        async def send_message(self, *a, **k):
            return "stub"

    class _UserMessage:
        def __init__(self, *a, **k):
            pass

    chat.LlmChat = _LlmChat
    chat.UserMessage = _UserMessage
    ei.llm = llm
    llm.chat = chat
    sys.modules.setdefault("emergentintegrations", ei)
    sys.modules.setdefault("emergentintegrations.llm", llm)
    sys.modules.setdefault("emergentintegrations.llm.chat", chat)

os.environ.setdefault("LAURENTIA_ENCRYPTION_KEY", "test-only-" + uuid.uuid4().hex)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from services import frekcore_bridge, kiltikonet_bridge, security  # noqa: E402

TEST_MONGO_URL = os.environ.get("TEST_MONGO_URL", "mongodb://localhost:27018")
TEST_DB_NAME = f"laurentia_sec_test_{uuid.uuid4().hex[:8]}"


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _no_demo_flags(monkeypatch):
    """Par défaut : aucun drapeau dev, bridges non configurés."""
    monkeypatch.delenv("LAURENTIA_ALLOW_DEMO_IDS", raising=False)
    monkeypatch.delenv("LAURENTIA_ALLOW_EPHEMERAL_KEY", raising=False)
    monkeypatch.setattr(kiltikonet_bridge, "KILTIKONET_API_URL", "")
    monkeypatch.setattr(kiltikonet_bridge, "KILTIKONET_API_KEY", "")
    monkeypatch.setattr(frekcore_bridge, "FREKCORE_API_URL", "")
    monkeypatch.setattr(frekcore_bridge, "FREKCORE_API_KEY", "")


# =========================== 1. DEMO-* (frekcore) ===========================

def test_frekcore_demo_ids_rejected_by_default():
    for fid in ("DEMO-SAYD", "DEMO-ARTIST", "DEMO-PRO"):
        assert _run(frekcore_bridge.validate_frek_id(fid))["valid"] is False


def test_frekcore_demo_ids_with_flag_never_privileged(monkeypatch):
    monkeypatch.setenv("LAURENTIA_ALLOW_DEMO_IDS", "true")
    v = _run(frekcore_bridge.validate_frek_id("DEMO-SAYD"))
    assert v["valid"] is True
    assert v["role"] not in security.PRIVILEGED_ROLES
    for meta in frekcore_bridge._DEV_VALID_FREK_IDS.values():
        assert meta["role"] not in security.PRIVILEGED_ROLES


def test_frekcore_unconfigured_non_demo_rejected(monkeypatch):
    assert _run(frekcore_bridge.validate_frek_id("FREK-G-0123456789"))["valid"] is False
    monkeypatch.setenv("LAURENTIA_ALLOW_DEMO_IDS", "true")
    assert _run(frekcore_bridge.validate_frek_id("FREK-G-0123456789"))["valid"] is False


def test_demote_role():
    assert security.demote_role("founder") == "member"
    assert security.demote_role("ADMIN") == "member"
    assert security.demote_role(None) == "member"
    assert security.demote_role("artist") == "artist"


# ======================= 2. Kiltikonet fail closed ==========================

def test_kiltikonet_unconfigured_rejects_arbitrary_frek_id():
    assert _run(kiltikonet_bridge.validate_frek_id("FREK-G-0123456789"))["valid"] is False
    assert _run(kiltikonet_bridge.validate_frek_id("DEMO-SAYD"))["valid"] is False


def test_kiltikonet_unconfigured_accepts_anonymous_visitor():
    v = _run(kiltikonet_bridge.validate_frek_id("ANON-ABCDEFGHIJ"))
    assert v["valid"] is True and v["role"] == "guest"
    # ANON trop court → refusé
    assert _run(kiltikonet_bridge.validate_frek_id("ANON-1"))["valid"] is False


def test_kiltikonet_dev_flag(monkeypatch):
    monkeypatch.setenv("LAURENTIA_ALLOW_DEMO_IDS", "true")
    v = _run(kiltikonet_bridge.validate_frek_id("DEMO-SAYD"))
    assert v["valid"] is True and v["role"] not in security.PRIVILEGED_ROLES
    assert _run(kiltikonet_bridge.validate_frek_id("FREK-X-DEV"))["valid"] is True
    for p in kiltikonet_bridge._MOCK_PROFILES.values():
        assert p["role"] not in security.PRIVILEGED_ROLES


# ============================ 7. Crypto =====================================

def _fresh_crypto():
    import services.crypto as crypto
    crypto = importlib.reload(crypto)
    return crypto


def test_crypto_fails_closed_without_key(monkeypatch):
    saved = os.environ.get("LAURENTIA_ENCRYPTION_KEY")
    monkeypatch.delenv("LAURENTIA_ENCRYPTION_KEY", raising=False)
    try:
        crypto = _fresh_crypto()
        with pytest.raises(crypto.EncryptionKeyMissing):
            crypto.ensure_key()
        with pytest.raises(crypto.EncryptionKeyMissing):
            crypto.encrypt_text("secret")
        with pytest.raises(crypto.EncryptionKeyMissing):
            crypto.decrypt_text({"v": 1, "n": "AAAA", "c": "AAAA"})
        # L'ancien placeholder public est refusé.
        monkeypatch.setenv("LAURENTIA_ENCRYPTION_KEY", "mvp-encryption-placeholder-change-in-prod")
        crypto = _fresh_crypto()
        with pytest.raises(crypto.EncryptionKeyMissing):
            crypto.ensure_key()
        assert not hasattr(crypto, "_DEFAULT_KEY")
    finally:
        if saved is not None:
            os.environ["LAURENTIA_ENCRYPTION_KEY"] = saved
        _fresh_crypto()


def test_crypto_ephemeral_key_only_with_flag(monkeypatch):
    saved = os.environ.get("LAURENTIA_ENCRYPTION_KEY")
    monkeypatch.delenv("LAURENTIA_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("LAURENTIA_ALLOW_EPHEMERAL_KEY", "true")
    try:
        c1 = _fresh_crypto()
        blob = c1.encrypt_text("bonjour")
        assert c1.decrypt_text(blob) == "bonjour"
        # Une autre instance (redémarrage) a une clé différente → illisible.
        c2 = _fresh_crypto()
        assert c2.decrypt_text(blob) == ""
    finally:
        if saved is not None:
            os.environ["LAURENTIA_ENCRYPTION_KEY"] = saved
        _fresh_crypto()


def test_crypto_roundtrip_with_key():
    crypto = _fresh_crypto()
    blob = crypto.encrypt_text("texte")
    assert crypto.is_encrypted(blob)
    assert crypto.decrypt_text(blob) == "texte"


# ============================ 9. CORS =======================================

def test_cors_wildcard_never_with_credentials():
    for env in (None, "", "*", " * ", "https://a.example,*"):
        kw = security.cors_middleware_kwargs(env)
        assert kw["allow_credentials"] is False
        assert kw["allow_origins"] == ["*"]
        assert "allow_origin_regex" not in kw


def test_cors_explicit_origins_with_credentials():
    kw = security.cors_middleware_kwargs("https://a.example, https://b.example")
    assert kw["allow_credentials"] is True
    assert kw["allow_origins"] == ["https://a.example", "https://b.example"]


def test_cors_preflight_does_not_reflect_origin_with_credentials():
    from starlette.middleware.cors import CORSMiddleware

    app = FastAPI()

    @app.get("/x")
    def _x():
        return {"ok": True}

    app.add_middleware(CORSMiddleware, **security.cors_middleware_kwargs(None))
    r = TestClient(app).get("/x", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") == "*"
    assert r.headers.get("access-control-allow-credentials") is None


# ===================== HTTP tests (TestClient + MongoDB) ====================

def _mongo_available() -> bool:
    try:
        from pymongo import MongoClient
        MongoClient(TEST_MONGO_URL, serverSelectionTimeoutMS=1500).admin.command("ping")
        return True
    except Exception:
        return False


mongo = pytest.mark.skipif(not _mongo_available(), reason="MongoDB de test injoignable")


@pytest.fixture(scope="module")
def sync_db():
    from pymongo import MongoClient
    c = MongoClient(TEST_MONGO_URL)
    yield c[TEST_DB_NAME]
    c.drop_database(TEST_DB_NAME)
    c.close()


@pytest.fixture(scope="module")
def client(sync_db):
    from motor.motor_asyncio import AsyncIOMotorClient
    from routes.auth import router as auth_router
    from routes.brain import router as brain_router
    from routes.omega import router as omega_router
    from routes.rgpd_purge import router as rgpd_router
    from routes.laurentia_gateway import router as gateway_router
    from routes.laurentia_sessions import router as sessions_router
    from routes.orchestrator_admin import webhook_router

    app = FastAPI()
    for r in (auth_router, brain_router, omega_router, rgpd_router,
              gateway_router, sessions_router, webhook_router):
        app.include_router(r)

    @app.on_event("startup")
    async def _db():
        app.state.mc = AsyncIOMotorClient(TEST_MONGO_URL)
        app.state.db = app.state.mc[TEST_DB_NAME]

    with TestClient(app) as c:
        yield c


def _make_user(sync_db, frek_id: str, role: str | None = None) -> str:
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    token = f"sess_{uuid.uuid4().hex}"
    doc = {"user_id": user_id, "email": f"{user_id}@test.invalid", "name": "T", "frek_id": frek_id}
    if role:
        doc["role"] = role
    sync_db.users.insert_one(doc)
    sync_db.user_sessions.insert_one({
        "user_id": user_id, "session_token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    })
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------ 3. /api/auth/frek ---------------------------

@mongo
def test_auth_frek_disabled_by_default(client, sync_db):
    r = client.post("/api/auth/frek", json={"frek_id": "DEMO-SAYD"})
    assert r.status_code == 404
    r = client.post("/api/auth/frek", json={"frek_id": "FREK-G-0123456789"})
    assert r.status_code == 404
    assert sync_db.users.count_documents({"frek_id": "DEMO-SAYD"}) == 0


@mongo
def test_auth_frek_dev_flag_never_founder(client, sync_db, monkeypatch):
    monkeypatch.setenv("LAURENTIA_ALLOW_DEMO_IDS", "true")
    r = client.post("/api/auth/frek", json={"frek_id": "DEMO-SAYD"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] not in security.PRIVILEGED_ROLES
    u = sync_db.users.find_one({"frek_id": "DEMO-SAYD"})
    assert u["role"] not in security.PRIVILEGED_ROLES


# ------------------------------ 4. RGPD purge -------------------------------

@mongo
def test_rgpd_purge_requires_admin(client, sync_db):
    assert client.post("/api/admin/rgpd/purge").status_code == 401
    member = _make_user(sync_db, "FREK-G-member0001", role="member")
    assert client.post("/api/admin/rgpd/purge", headers=_auth(member)).status_code == 403
    admin = _make_user(sync_db, "FREK-G-admin00001", role="founder")
    r = client.post("/api/admin/rgpd/purge", headers=_auth(admin))
    assert r.status_code == 200
    assert "instances_anonymized" in r.json()


# --------------------------- 5. LLM proxies ---------------------------------

@mongo
def test_llm_proxies_require_session(client, sync_db, monkeypatch):
    from services import cvl_brain

    calls = []

    async def fake_chat(message, system, session_id=None):
        calls.append(message)
        return "ok"

    async def fake_stream(message, system, session_id=None):
        calls.append(message)
        yield "ok"

    monkeypatch.setattr(cvl_brain, "chat_enriched", fake_chat)
    monkeypatch.setattr(cvl_brain, "chat_stream", fake_stream)

    assert client.post("/api/brain/chat-enriched", json={"message": "hi"}).status_code == 401
    assert client.post("/api/omega/chat-enriched", json={"message": "hi"}).status_code == 401
    assert calls == []

    tok = _make_user(sync_db, "FREK-G-llmuser001")
    r = client.post("/api/brain/chat-enriched", json={"message": "hi"}, headers=_auth(tok))
    assert r.status_code == 200 and r.json()["response"] == "ok"
    r = client.post("/api/omega/chat-enriched", json={"message": "hi"}, headers=_auth(tok))
    assert r.status_code == 200 and "event: token" in r.text


# ---------------------- 6. FREK-ID ownership --------------------------------

@mongo
def test_instance_and_memory_require_ownership(client, sync_db):
    victim = "FREK-G-victim0001"
    sync_db.laurentia_memory.insert_one({"frek_id": victim, "sessions": [],
                                         "long_term": {"facts": ["privé"]}})
    # Sans session → 401
    assert client.get(f"/api/laurentia/memory/{victim}").status_code == 401
    assert client.get(f"/api/laurentia/instances/{victim}").status_code == 401
    # Autre utilisateur → 403
    other = _make_user(sync_db, "FREK-G-attacker01")
    assert client.get(f"/api/laurentia/memory/{victim}", headers=_auth(other)).status_code == 403
    assert client.get(f"/api/laurentia/instances/{victim}", headers=_auth(other)).status_code == 403
    # Propriétaire → 200
    owner = _make_user(sync_db, victim)
    r = client.get(f"/api/laurentia/memory/{victim}", headers=_auth(owner))
    assert r.status_code == 200 and r.json()["long_term"] == {"facts": ["privé"]}
    assert client.get(f"/api/laurentia/instances/{victim}", headers=_auth(owner)).status_code == 200
    # Admin → 200
    admin = _make_user(sync_db, "FREK-G-admin00002", role="admin")
    assert client.get(f"/api/laurentia/memory/{victim}", headers=_auth(admin)).status_code == 200
    # DEMO-* sans drapeau → 401
    assert client.get("/api/laurentia/memory/DEMO-SAYD").status_code == 401
    # Visiteur anonyme (ANON-*) → autorisé
    assert client.get("/api/laurentia/memory/ANON-ABCDEFGHIJ").status_code == 200


@mongo
def test_sessions_require_ownership(client, sync_db):
    from services.security import tenant_id_for

    victim = "FREK-G-victim0002"
    sync_db.laurentia_interactions.insert_one({
        "tenant_id": tenant_id_for(victim), "session_id": "s-victim",
        "input_text": "q", "output_text": "a", "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # ?frek_id= d'un membre sans session → 401
    assert client.get(f"/api/laurentia/sessions/list?frek_id={victim}").status_code == 401
    assert client.get(f"/api/laurentia/sessions/s-victim?frek_id={victim}").status_code == 401
    assert client.delete(f"/api/laurentia/sessions/s-victim?frek_id={victim}").status_code == 401
    assert client.get("/api/laurentia/sessions/list").status_code == 401

    # Session d'un autre utilisateur : on ne voit que SES sessions (le ?frek_id= est ignoré)
    other = _make_user(sync_db, "FREK-G-attacker02")
    r = client.get(f"/api/laurentia/sessions/list?frek_id={victim}", headers=_auth(other))
    assert r.status_code == 200 and r.json()["sessions"] == []
    r = client.get(f"/api/laurentia/sessions/s-victim?frek_id={victim}", headers=_auth(other))
    assert r.status_code == 200 and r.json()["messages"] == []

    # Rien n'a été supprimé
    assert sync_db.laurentia_interactions.count_documents({"session_id": "s-victim"}) == 1

    # Propriétaire
    owner = _make_user(sync_db, victim)
    r = client.get("/api/laurentia/sessions/list", headers=_auth(owner))
    assert r.status_code == 200 and len(r.json()["sessions"]) == 1

    # Visiteur anonyme : flux ANON-* préservé
    assert client.get("/api/laurentia/sessions/list?frek_id=ANON-ABCDEFGHIJ").status_code == 200


@mongo
def test_query_rejects_unverified_frek_id(client, sync_db):
    """Bridge non configuré : un FREK-ID arbitraire sans session est refusé."""
    r = client.post("/api/laurentia/query", json={"frek_id": "FREK-G-victim0003", "input": "x"})
    assert r.status_code == 403
    r = client.post("/api/laurentia/instances/init", json={"frek_id": "FREK-G-victim0003"})
    assert r.status_code == 403
    # Le propriétaire authentifié passe la validation d'identité.
    owner = _make_user(sync_db, "FREK-G-victim0003")
    r = client.post("/api/laurentia/instances/init", json={"frek_id": "FREK-G-victim0003"},
                    headers=_auth(owner))
    assert r.status_code == 200


# --------------------------- 8. SMS webhook ---------------------------------

@mongo
def test_sms_webhook_requires_secret(client, monkeypatch):
    body = {"from": "+10000000000", "message": "OK inc-1"}
    monkeypatch.delenv("OVH_SMS_WEBHOOK_SECRET", raising=False)
    assert client.post("/api/webhook/ovh-sms-reply", json=body).status_code == 503

    monkeypatch.setenv("OVH_SMS_WEBHOOK_SECRET", "s3cret-test-value")
    monkeypatch.delenv("FOUNDER_PHONE_NUMBER", raising=False)
    assert client.post("/api/webhook/ovh-sms-reply", json=body).status_code == 403
    assert client.post("/api/webhook/ovh-sms-reply?token=wrong", json=body).status_code == 403
    r = client.post("/api/webhook/ovh-sms-reply", json=body, headers={"X-Webhook-Token": "s3cret-test-value"})
    assert r.status_code == 200
    # Pas d'orchestrateur dans l'app de test → passe l'auth, puis refus métier.
    assert r.json() == {"ok": False, "reason": "orchestrator_not_ready"}
    r = client.post("/api/webhook/ovh-sms-reply?token=s3cret-test-value", json=body)
    assert r.status_code == 200
