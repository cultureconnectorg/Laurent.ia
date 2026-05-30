"""
Tests complémentaires Phase 1 (review iteration 2) :
  - Chiffrement de la mémoire (laurentia_memory.sessions[*].input/output)
  - Round-trip déchiffrement via GET /api/laurentia/sessions/{sid}?frek_id=...
  - Upload PDF/DOCX via HTTP multipart (Claude voit le texte extrait)
  - Rejet HTTP du PNG → 415
  - Rejet HTTP du fichier > 10 Mio → 413

Demande explicitement DEMO-SAYD en tier 'creator'. Reset à 'free' en teardown.
"""
import io
import json
import os

import httpx
import pytest
from pymongo import MongoClient

from services.crypto import decrypt_text
from services.file_parser import FILE_MAX_BYTES

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "laurentia")

DEMO_FREK = "DEMO-SAYD"


@pytest.fixture(scope="module")
def http_client():
    return httpx.Client(base_url=BASE_URL, timeout=60.0)


@pytest.fixture(scope="module")
def db():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    # teardown : remet tier free
    c[DB_NAME].laurentia_instances.update_one(
        {"frek_id": DEMO_FREK},
        {"$set": {"tier": "free", "version": "free",
                  "tokens_limit_month": 100_000, "memory_window": 10, "rate_per_min": 10}},
    )
    c.close()


def _set_creator(db):
    db.laurentia_instances.update_one(
        {"frek_id": DEMO_FREK},
        {"$set": {"tier": "creator", "version": "creator",
                  "tokens_limit_month": 2_000_000, "memory_window": 100, "rate_per_min": 30},
         "$setOnInsert": {"frek_id": DEMO_FREK}},
        upsert=True,
    )


def _set_free(db):
    db.laurentia_instances.update_one(
        {"frek_id": DEMO_FREK},
        {"$set": {"tier": "free", "version": "free",
                  "tokens_limit_month": 100_000, "memory_window": 10, "rate_per_min": 10}},
    )


def _extract_meta(sse_text: str) -> dict:
    """Parse l'event: meta du SSE."""
    for line in sse_text.splitlines():
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if "session_id" in d and "interaction_id" in d:
                    return d
            except Exception:
                pass
    return {}


# ---------- Memory encryption ----------

def test_memory_sessions_are_encrypted_at_rest(http_client, db):
    """Après une query JSON, la dernière session en mémoire doit être chiffrée."""
    _set_free(db)
    r = http_client.post(
        "/api/laurentia/query",
        json={"frek_id": DEMO_FREK, "input": "Memo encryption check",
              "context": {"app": "direct"}},
    )
    assert r.status_code == 200
    mem = db.laurentia_memory.find_one({"frek_id": DEMO_FREK})
    assert mem is not None
    sessions = mem.get("sessions", [])
    assert len(sessions) >= 1
    last = sessions[-1]
    assert isinstance(last.get("input"), dict)
    assert last["input"].get("v") == 1
    assert "n" in last["input"] and "c" in last["input"]
    assert isinstance(last.get("output"), dict)
    assert last["output"].get("v") == 1
    assert decrypt_text(last["input"]).startswith("Memo encryption check")


# ---------- Round-trip via GET /sessions/{sid} ----------

def test_get_session_decrypts_blobs(http_client, db):
    _set_free(db)
    r = http_client.post(
        "/api/laurentia/query",
        json={"frek_id": DEMO_FREK, "input": "RoundTrip-MARKER-2026",
              "context": {"app": "direct"}},
    )
    assert r.status_code == 200
    meta = _extract_meta(r.text)
    sid = meta.get("session_id")
    assert sid, "session_id absent du SSE meta"

    rg = http_client.get(f"/api/laurentia/sessions/{sid}", params={"frek_id": DEMO_FREK})
    assert rg.status_code == 200
    body = rg.json()
    assert body["session_id"] == sid
    texts = " ".join(m["text"] for m in body["messages"])
    assert "RoundTrip-MARKER-2026" in texts


# ---------- PDF via HTTP ----------

def test_query_multipart_pdf(http_client, db):
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab non installé")
    _set_creator(db)
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Token-PDF-MARKER-ALPHA-2026")
    c.drawString(100, 730, "Souverainete caribeenne.")
    c.save()
    pdf_bytes = buf.getvalue()
    payload = json.dumps({"frek_id": DEMO_FREK,
                          "input": "Cite la chaine entre guillemets du PDF.",
                          "context": {"app": "direct"}})
    files = [("files", ("doc.pdf", pdf_bytes, "application/pdf"))]
    r = http_client.post("/api/laurentia/query", data={"payload": payload}, files=files)
    assert r.status_code == 200, r.text[:300]
    assert "event: meta" in r.text
    assert "doc.pdf" in r.text
    assert "\"kind\": \"pdf\"" in r.text or '"kind":"pdf"' in r.text
    # input_text stocké doit contenir le texte PDF déchiffré
    rec = db.laurentia_interactions.find_one(
        {"context_app": "direct"}, sort=[("timestamp", -1)],
    )
    plain = decrypt_text(rec["input_text"])
    assert "Token-PDF-MARKER-ALPHA-2026" in plain


# ---------- DOCX via HTTP ----------

def test_query_multipart_docx(http_client, db):
    try:
        from docx import Document as DocxDocument
    except ImportError:
        pytest.skip("python-docx non installé")
    _set_creator(db)
    doc = DocxDocument()
    doc.add_paragraph("DocxMarkerOmega2026 — phrase test.")
    buf = io.BytesIO()
    doc.save(buf)
    payload = json.dumps({"frek_id": DEMO_FREK,
                          "input": "Cite le marker du DOCX",
                          "context": {"app": "direct"}})
    files = [("files", ("brief.docx", buf.getvalue(),
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))]
    r = http_client.post("/api/laurentia/query", data={"payload": payload}, files=files)
    assert r.status_code == 200, r.text[:300]
    assert "brief.docx" in r.text
    assert '"kind": "docx"' in r.text or '"kind":"docx"' in r.text
    rec = db.laurentia_interactions.find_one(
        {"context_app": "direct"}, sort=[("timestamp", -1)],
    )
    plain = decrypt_text(rec["input_text"])
    assert "DocxMarkerOmega2026" in plain


# ---------- Rejet HTTP PNG → 415 ----------

def test_query_multipart_png_rejected_415(http_client, db):
    _set_creator(db)
    payload = json.dumps({"frek_id": DEMO_FREK, "input": "x", "context": {"app": "direct"}})
    files = [("files", ("photo.png", b"\x89PNG\r\n\x1a\n" + b"x" * 32, "image/png"))]
    r = http_client.post("/api/laurentia/query", data={"payload": payload}, files=files)
    assert r.status_code == 415, f"got {r.status_code}: {r.text[:200]}"


# ---------- Rejet HTTP file > 10 MiB → 413 ----------

def test_query_multipart_oversize_413(http_client, db):
    _set_creator(db)
    big = b"x" * (FILE_MAX_BYTES + 100)
    payload = json.dumps({"frek_id": DEMO_FREK, "input": "x", "context": {"app": "direct"}})
    files = [("files", ("big.txt", big, "text/plain"))]
    r = http_client.post("/api/laurentia/query", data={"payload": payload}, files=files)
    assert r.status_code == 413, f"got {r.status_code}: {r.text[:200]}"
