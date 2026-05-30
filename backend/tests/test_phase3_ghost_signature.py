"""
Tests Phase 3 — Persistance Fantôme + Signature PDF + Paywall 2 exports/mois.
"""
import io
import os
from datetime import datetime, timezone

import httpx
import pypdf
import pytest
from pymongo import MongoClient

from routes.pdf_export import (
    COLLECTION_EXPORTS,
    FREE_EXPORTS_PER_MONTH,
    _make_qr_data_uri,
    _signature_section_html,
)
from services.fingerprint import device_id_from_fingerprint

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "laurentia")


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def http_client():
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


# -------------------- QR & Signature page --------------------

def test_qr_data_uri_is_valid_png():
    uri = _make_qr_data_uri("https://laurent.ia/echo/test-session-123")
    assert uri.startswith("data:image/png;base64,")
    # Le contenu doit être suffisant pour un PNG
    assert len(uri) > 200


def test_signature_section_html_includes_branding():
    html = _signature_section_html("sess-abc-123")
    assert "Certifié par l'Infrastructure Laurent.ia" in html
    assert "CVLN Group" in html
    assert "data:image/png;base64," in html
    assert "/echo/sess-abc-123" in html
    assert "La parole reste" in html


def test_signature_section_html_no_session_falls_back_to_root():
    html = _signature_section_html(None)
    assert "Certifié par l'Infrastructure Laurent.ia" in html
    assert "/echo/" not in html  # pas de session = URL racine


# -------------------- Persistance Fantôme --------------------

def test_resolve_returns_null_without_fingerprint(http_client):
    r = http_client.get("/api/laurentia/resolve")
    assert r.status_code == 200
    data = r.json()
    assert data["device_id"] is None
    assert data["frek_id"] is None
    assert data["instance"] is None


def test_resolve_returns_device_id_with_fingerprint(http_client):
    fp = "ghost-persistance-test-" + os.urandom(6).hex()
    r = http_client.get("/api/laurentia/resolve", headers={"X-Device-Fingerprint": fp})
    assert r.status_code == 200
    data = r.json()
    expected = device_id_from_fingerprint(fp)
    assert data["device_id"] == expected
    # Aucune instance liée → frek_id null
    assert data["frek_id"] is None


def test_resolve_returns_frek_when_device_linked(http_client, db):
    """Simule un device déjà utilisé : injecte la liaison en DB et vérifie le resolve."""
    fp = "ghost-linked-" + os.urandom(6).hex()
    did = device_id_from_fingerprint(fp)
    frek = f"DEMO-GHOST-{os.urandom(3).hex()}"
    db.laurentia_instances.update_one(
        {"frek_id": frek},
        {
            "$set": {
                "frek_id": frek,
                "tier": "free",
                "version": "free",
                "last_active": datetime.now(timezone.utc).isoformat(),
            },
            "$addToSet": {"device_ids": did},
        },
        upsert=True,
    )
    r = http_client.get("/api/laurentia/resolve", headers={"X-Device-Fingerprint": fp})
    assert r.status_code == 200
    data = r.json()
    assert data["device_id"] == did
    assert data["frek_id"] == frek
    assert data["instance"]["tier"] == "free"
    # cleanup
    db.laurentia_instances.delete_one({"frek_id": frek})


# -------------------- Compteur d'exports Free 2/mois --------------------

def _purge_exports(db, device_id):
    db[COLLECTION_EXPORTS].delete_many({"device_id": device_id})


def test_pdf_quota_initial_state(http_client, db):
    fp = "quota-initial-" + os.urandom(6).hex()
    did = device_id_from_fingerprint(fp)
    _purge_exports(db, did)
    r = http_client.get("/api/export/pdf/quota", headers={"X-Device-Fingerprint": fp})
    assert r.status_code == 200
    data = r.json()
    assert data["free_exports_used"] == 0
    assert data["free_exports_limit"] == FREE_EXPORTS_PER_MONTH
    assert data["free_exports_remaining"] == FREE_EXPORTS_PER_MONTH


def test_pdf_export_increments_counter(http_client, db):
    fp = "quota-increment-" + os.urandom(6).hex()
    did = device_id_from_fingerprint(fp)
    _purge_exports(db, did)

    # Export 1 → 200 + signature
    r1 = http_client.post(
        "/api/export/pdf",
        headers={"X-Device-Fingerprint": fp, "Content-Type": "application/json"},
        json={"title": "Test 1", "content_md": "## Hello\nbody"},
    )
    assert r1.status_code == 200
    assert r1.headers["X-Laurentia-Signature"] == "1"
    assert r1.headers["X-Laurentia-Free-Used"] == "1"
    assert r1.headers["X-Laurentia-Tier"] == "free"

    # Export 2 → 200 + signature, counter=2
    r2 = http_client.post(
        "/api/export/pdf",
        headers={"X-Device-Fingerprint": fp, "Content-Type": "application/json"},
        json={"title": "Test 2", "content_md": "## Hello\nbody"},
    )
    assert r2.status_code == 200
    assert r2.headers["X-Laurentia-Free-Used"] == "2"

    # Export 3 → 402 paywall
    r3 = http_client.post(
        "/api/export/pdf",
        headers={"X-Device-Fingerprint": fp, "Content-Type": "application/json"},
        json={"title": "Test 3", "content_md": "## Hello\nbody"},
    )
    assert r3.status_code == 402
    body = r3.json()
    assert "Creator" in body["detail"]
    assert "🪙" in body["detail"]
    assert r3.headers["X-Laurentia-Paywall"] == "creator"

    _purge_exports(db, did)


def test_pdf_signature_only_for_free_tier(http_client, db):
    """Si le device_id est lié à une instance 'creator', PAS de signature, pas de compteur."""
    fp = "tier-creator-" + os.urandom(6).hex()
    did = device_id_from_fingerprint(fp)
    frek = f"DEMO-CREATOR-{os.urandom(3).hex()}"
    db.laurentia_instances.update_one(
        {"frek_id": frek},
        {
            "$set": {
                "frek_id": frek,
                "tier": "creator",
                "version": "creator",
                "last_active": datetime.now(timezone.utc).isoformat(),
            },
            "$addToSet": {"device_ids": did},
        },
        upsert=True,
    )
    _purge_exports(db, did)

    r = http_client.post(
        "/api/export/pdf",
        headers={"X-Device-Fingerprint": fp, "Content-Type": "application/json"},
        json={"title": "Creator export", "content_md": "## Premium content\nUnlimited."},
    )
    assert r.status_code == 200
    assert r.headers["X-Laurentia-Signature"] == "0"
    assert r.headers["X-Laurentia-Tier"] == "creator"

    # Vérifie que le PDF ne contient PAS la page signature
    reader = pypdf.PdfReader(io.BytesIO(r.content))
    full_text = " ".join(p.extract_text() for p in reader.pages)
    assert "Certifié par l'Infrastructure" not in full_text

    # Et que le compteur n'a pas été incrémenté
    doc = db[COLLECTION_EXPORTS].find_one({"device_id": did})
    assert doc is None

    db.laurentia_instances.delete_one({"frek_id": frek})


def test_pdf_pages_includes_signature_for_free(http_client, db):
    """PDF Free tier doit avoir au moins 2 pages (cover + content + signature)."""
    fp = "pages-check-" + os.urandom(6).hex()
    did = device_id_from_fingerprint(fp)
    _purge_exports(db, did)

    r = http_client.post(
        "/api/export/pdf",
        headers={"X-Device-Fingerprint": fp, "Content-Type": "application/json"},
        json={"title": "Sealed Doc", "content_md": "## Hello", "session_id": "sealed-sess-1"},
    )
    assert r.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) >= 2
    last_text = reader.pages[-1].extract_text()
    assert "Certifié par l'Infrastructure" in last_text
    # PDF text extraction peut casser les longues URLs sur plusieurs lignes
    # On vérifie juste la présence du préfixe et du début du session_id
    flat = last_text.replace("\n", "").replace(" ", "")
    assert "sealed" in flat and "sess-1" in flat.replace("-", "")[:10000] or "sealed-sess-1" in flat
    _purge_exports(db, did)
