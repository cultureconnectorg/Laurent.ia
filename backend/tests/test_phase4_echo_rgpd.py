"""
Tests Phase 4 — Pipeline /echo + Landing publique + RGPD purge + Anti-jailbreak persona.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pymongo import MongoClient

from routes.rgpd_purge import purge_once, PURGE_AFTER_DAYS
from services.cvl_brain_knowledge import build_system_prompt, LAURENTIA_SYSTEM_PROMPT

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "laurentia")


@pytest.fixture(scope="module")
def http_client():
    return httpx.Client(base_url=BASE_URL, timeout=120.0)


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


# -------------------- Persona v1.2 anti-jailbreak --------------------

def test_persona_contains_anti_jailbreak_rules():
    p = build_system_prompt()
    assert "SECRET DÉFENSE" in p
    assert "ANTI-JAILBREAK" in p
    assert "Cette demande ne relève pas de mon protocole" in p
    # Vérifie que la consigne "ne pas nommer les fournisseurs tiers" est bien présente
    assert "Tu ne nommes ni Claude" in p
    assert "ni Anthropic" in p
    assert "ni OpenAI" in p


def test_persona_protects_secret_keys_in_text():
    p = LAURENTIA_SYSTEM_PROMPT
    assert "LAURENTIA_" in p  # mention dans liste à protéger
    assert "AES-256-GCM" in p or "AES-256" in p
    assert "fingerprinting" in p.lower()


# -------------------- Echo pipeline --------------------

@pytest.fixture
def cleanup_echo(db):
    sids = []
    yield sids
    for sid in sids:
        db.laurentia_echoes.delete_one({"session_id": sid})
        db.laurentia_echo_attributions.delete_many({"session_id": sid})


def test_echo_404_when_missing(http_client):
    r = http_client.get("/api/echo/this-does-not-exist-9999")
    assert r.status_code == 404


def test_echo_generate_with_raw_text_and_public_get(http_client, db, cleanup_echo):
    sid = f"echo-pytest-{int(time.time())}"
    cleanup_echo.append(sid)
    raw = (
        "La Diaspora caribéenne représente 37% du PIB régional via remittances. "
        "Top: Haïti 3.8B, Jamaïque 3.2B, RD 9.4B. Opportunité fintech décarbonée."
    )
    r = http_client.post("/api/laurentia/echo", json={"session_id": sid, "raw_text": raw})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["public_url"] == f"/echo/{sid}"
    echo = data["echo"]
    assert all(k in echo for k in ["title", "summary", "pro", "instant", "visual"])
    assert isinstance(echo["pro"].get("headline"), str)
    assert isinstance(echo["instant"].get("bullets"), list)
    assert isinstance(echo["visual"].get("punchlines"), list)

    # Public GET (premier appel : views=0 dans la réponse + increment async post-read)
    g = http_client.get(f"/api/echo/{sid}")
    assert g.status_code == 200
    pub = g.json()
    assert pub["session_id"] == sid
    assert pub["title"]
    # Le 2ème GET doit refléter le compteur (le 1er a incrémenté en post-read)
    g2 = http_client.get(f"/api/echo/{sid}")
    pub2 = g2.json()
    assert pub2["views"] >= 1


def test_echo_conversion_attribution(http_client, db, cleanup_echo):
    sid = f"echo-conv-{int(time.time())}"
    cleanup_echo.append(sid)
    # Crée un echo direct en base pour éviter le coût LLM
    db.laurentia_echoes.insert_one({
        "session_id": sid,
        "tenant_id": None,
        "echo": {
            "title": "T", "summary": "S",
            "pro": {"headline": "H", "body": "B", "hashtags": []},
            "instant": {"lead": "L", "bullets": ["b"]},
            "visual": {"punchlines": ["p"], "color_hint": "gold"},
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_public": True,
        "views": 0,
        "conversions": 0,
    })

    r = http_client.post(
        f"/api/echo/{sid}/conversion",
        json={"source": "echo_landing_cta"},
        headers={"X-Device-Fingerprint": "visitor-conv-fp-test-001"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["redirect"].startswith("/?from_echo=")

    # Vérifie attribution
    attr = db.laurentia_echo_attributions.find_one({"session_id": sid})
    assert attr is not None
    assert attr["source"] == "echo_landing_cta"
    assert attr["visitor_device_id"] is not None

    # Conversions incrémentées
    doc = db.laurentia_echoes.find_one({"session_id": sid})
    assert doc["conversions"] >= 1


# -------------------- RGPD purge --------------------

@pytest.mark.asyncio
async def test_rgpd_purge_anonymizes_old_instances():
    """Une instance non active depuis >90j doit voir ses device_ids vidés."""
    import motor.motor_asyncio as motor
    client = motor.AsyncIOMotorClient(MONGO_URL)
    adb = client[DB_NAME]

    frek = f"DEMO-PURGE-{int(time.time())}"
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=PURGE_AFTER_DAYS + 5)
    await adb.laurentia_instances.insert_one({
        "frek_id": frek,
        "tier": "free",
        "version": "free",
        "last_active": cutoff_dt.isoformat(),
        "device_ids": ["device-old-abc", "device-old-def"],
    })

    report = await purge_once(adb)
    assert report["instances_anonymized"] >= 1

    purged = await adb.laurentia_instances.find_one({"frek_id": frek})
    assert purged["device_ids"] == []
    assert "rgpd_purged_at" in purged

    await adb.laurentia_instances.delete_one({"frek_id": frek})
    client.close()


@pytest.mark.asyncio
async def test_rgpd_purge_anonymizes_old_attributions():
    import motor.motor_asyncio as motor
    client = motor.AsyncIOMotorClient(MONGO_URL)
    adb = client[DB_NAME]

    old = datetime.now(timezone.utc) - timedelta(days=PURGE_AFTER_DAYS + 1)
    res = await adb.laurentia_echo_attributions.insert_one({
        "session_id": "rgpd-test-sess",
        "source": "echo_landing_cta",
        "visitor_device_id": "device-old-attr",
        "ts": old,
    })

    report = await purge_once(adb)
    assert report["echo_attributions_anonymized"] >= 1

    doc = await adb.laurentia_echo_attributions.find_one({"_id": res.inserted_id})
    assert doc["visitor_device_id"] is None

    await adb.laurentia_echo_attributions.delete_one({"_id": res.inserted_id})
    client.close()


def test_rgpd_endpoint_idempotent(http_client):
    r1 = http_client.post("/api/admin/rgpd/purge", json={})
    r2 = http_client.post("/api/admin/rgpd/purge", json={})
    assert r1.status_code == 200
    assert r2.status_code == 200
    j2 = r2.json()
    # Le 2ème appel doit avoir 0 modif (déjà tout purgé)
    assert j2["instances_anonymized"] == 0
    assert j2["echo_attributions_anonymized"] == 0
