"""
Tests Phase 2 — Policière Invisible (fingerprint + HMAC + sliding window MongoDB)
                + Export PDF WeasyPrint + champ pages dans ParsedFile.
"""
import io
import json
import os

import httpx
import pypdf
import pytest
from pymongo import MongoClient

from services.fingerprint import device_id_from_fingerprint, resolve_limit_key
from services.rate_limit_mongo import LIMITS, COLLECTION
from services.file_parser import parse_file

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "laurentia")

DEMO_FREK = "DEMO-SAYD"


# -------------------- Fingerprint / HMAC --------------------

def test_device_id_deterministic():
    fp = "c:abc|g:nvidia|h:cpu:4|mem:8"
    a = device_id_from_fingerprint(fp)
    b = device_id_from_fingerprint(fp)
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_device_id_different_inputs():
    a = device_id_from_fingerprint("c:aaa|g:gpuA")
    b = device_id_from_fingerprint("c:bbb|g:gpuB")
    assert a != b


def test_device_id_none_when_empty():
    assert device_id_from_fingerprint("") is None
    assert device_id_from_fingerprint(None) is None
    assert device_id_from_fingerprint("short") is None  # < 8 chars


def test_resolve_limit_key_priority():
    """device_id prioritaire sur frek_id."""
    did = device_id_from_fingerprint("c:abc|g:gpu|h:cpu:4")
    key = resolve_limit_key("DEMO-SAYD", did)
    assert key == did
    # Fallback frek_id
    fb = resolve_limit_key("DEMO-SAYD", None)
    assert fb != did
    assert len(fb) == 64


# -------------------- Sliding window MongoDB --------------------

@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def http_client():
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


def _set_tier(db, frek_id, tier):
    quotas = {
        "free": dict(tier="free", version="free", tokens_limit_month=100_000, memory_window=10, rate_per_min=10),
        "creator": dict(tier="creator", version="creator", tokens_limit_month=2_000_000, memory_window=100, rate_per_min=30),
    }
    db.laurentia_instances.update_one(
        {"frek_id": frek_id},
        {"$set": quotas[tier], "$setOnInsert": {"frek_id": frek_id}},
        upsert=True,
    )


def test_ttl_index_present(db):
    info = db[COLLECTION].index_information()
    ttl = info.get("ttl_expires_at")
    assert ttl is not None
    assert ttl.get("expireAfterSeconds") == 0
    assert "key_ts" in info


def test_rate_limit_quotas_loaded():
    assert LIMITS["free"]["per_min"] == 10
    assert LIMITS["creator"]["per_min"] == 60
    assert LIMITS["infinite"]["per_min"] == 240


def test_rate_limit_triggers_429_with_noble_message(http_client, db):
    """Burst au-delà de la limite free (10/min) doit renvoyer un 429 noble.

    On bypass le SSE (lent à cause de Claude) en injectant directement N hits
    dans la collection juste avant l'appel HTTP final.
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    from services.rate_limit_mongo import check_and_consume, COLLECTION as RL_COLL
    from motor.motor_asyncio import AsyncIOMotorClient

    _set_tier(db, DEMO_FREK, "free")
    fp = "test-burst-" + os.urandom(8).hex()
    did = device_id_from_fingerprint(fp)
    db[RL_COLL].delete_many({"key": did})

    # Pré-remplit avec 10 hits fictifs dans la dernière minute
    now = datetime.now(timezone.utc)
    db[RL_COLL].insert_many([
        {
            "key": did,
            "tier": "free",
            "ts": now - timedelta(seconds=i),
            "expires_at": now + timedelta(seconds=3700),
        }
        for i in range(10)
    ])

    # Vérification fonctionnelle directe : la 11ème doit être REFUSÉE
    async def _check():
        amc = AsyncIOMotorClient(MONGO_URL)
        try:
            adb = amc[DB_NAME]
            return await check_and_consume(adb, key=did, tier="free")
        finally:
            amc.close()

    decision = asyncio.run(_check())
    assert decision.allowed is False
    assert decision.reason in ("per_min", "per_hour")

    # Validation HTTP (gateway répond 429 + message noble)
    r = http_client.post(
        "/api/laurentia/query",
        json={"frek_id": DEMO_FREK, "input": "burst-final", "context": {"app": "direct"}},
        headers={"X-Device-Fingerprint": fp},
    )
    assert r.status_code == 429, f"Expected 429, got {r.status_code} body={r.text[:200]}"
    body = r.text.lower()
    assert "luciole" in body
    assert "creator" in body

    db[RL_COLL].delete_many({"key": did})


# -------------------- ParsedFile.pages --------------------

def test_pdf_pages_count():
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab requis")
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Page 1")
    c.showPage()
    c.drawString(100, 750, "Page 2")
    c.showPage()
    c.drawString(100, 750, "Page 3")
    c.save()
    pf = parse_file("multi.pdf", "application/pdf", buf.getvalue())
    assert pf.pages == 3


def test_txt_pages_count():
    pf = parse_file("notes.txt", "text/plain", b"l1\nl2\nl3\nl4")
    assert pf.pages == 4


def test_summary_exposes_pages():
    pf = parse_file("a.txt", "text/plain", b"hello world")
    s = pf.as_summary()
    assert "pages" in s
    assert s["pages"] >= 1


# -------------------- Export PDF endpoint --------------------

def test_export_pdf_minimal(http_client):
    r = http_client.post(
        "/api/export/pdf",
        json={
            "title": "Test Export",
            "content_md": "## Section\n\n**Texte gras** et *italique*.\n\n- item 1\n- item 2",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:5] == b"%PDF-"
    # Parse pour vérifier que c'est un PDF valide avec contenu attendu
    reader = pypdf.PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) >= 1
    text = reader.pages[0].extract_text()
    assert "Test Export" in text
    assert "Section" in text


def test_export_pdf_with_subtitle_and_footer(http_client):
    r = http_client.post(
        "/api/export/pdf",
        json={
            "title": "Analyse Souveraine",
            "subtitle": "Note v0.9-VALIDÉ",
            "content_md": "# Conclusion\n\nDiaspora = 42% PIB.",
            "footer_note": "Confidentiel CVLN",
        },
    )
    assert r.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(r.content))
    text = reader.pages[0].extract_text()
    assert "Analyse Souveraine" in text
    assert "Confidentiel CVLN" in text


def test_export_pdf_rejects_oversize_payload(http_client):
    big_md = "x " * 30000  # 60k chars
    r = http_client.post(
        "/api/export/pdf",
        json={"title": "Big", "content_md": big_md},
    )
    assert r.status_code == 422  # pydantic max_length violation


def test_export_pdf_sanitizes_html():
    """Vérifie que le HTML brut hostile est strippé (pas exécuté)."""
    from routes.pdf_export import _md_to_safe_html
    out = _md_to_safe_html('Click <script>alert("xss")</script> me')
    assert "<script>" not in out
    assert "alert" not in out or ">" not in out.split("alert")[0][-1:]  # bleach strips
