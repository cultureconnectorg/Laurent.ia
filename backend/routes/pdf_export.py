"""
pdf_export.py — Export PDF souverain (WeasyPrint) avec charte CVLN + Signature de la Constellation.

Endpoints :
  POST /api/export/pdf

Modèle économique (Free tier) :
  - 2 exports gratuits / mois calendaire / device_id
  - 3ème tentative → HTTP 402 Payment Required avec CTA Stripe
  - Chaque export Free reçoit une PAGE DE SIGNATURE FINALE :
        Mention « Certifié par l'Infrastructure Laurent.ia »
        QR code → /echo/{session_id}
  - Tiers Creator / Infinite : aucune signature, exports illimités.

Charte graphique CVLN :
  Fond blanc épuré, Cormorant Garamond (titres souverains), Urbanist (UI),
  accents or #C9A24B / #E7C566, bleu nuit #0A0F1F en filet et pied de page.

Headers de réponse :
  X-Laurentia-Signature : "1" si la page de signature est injectée
  X-Laurentia-Free-Used : nombre d'exports Free utilisés ce mois
  X-Laurentia-Free-Limit : seuil mensuel (2)

Sécurité :
  - Limite payload markdown : 50_000 chars (Pydantic)
  - bleach strip HTML hostile (XSS impossible — WeasyPrint n'exécute pas de JS de toute façon)
  - Comptabilité incrémentée AVANT génération (pas de double-comptage en cas de retry)
"""
from __future__ import annotations

import base64
import io
import logging
import os
import re
from datetime import datetime, timezone

import bleach
import markdown as md_lib
import qrcode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from weasyprint import HTML, CSS

from services.fingerprint import device_id_from_fingerprint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])

MAX_MD_CHARS = 50_000
FREE_EXPORTS_PER_MONTH = 2
FREE_TIERS = {"free", None}  # None = device anonyme sans instance encore créée
PAYWALL_TIERS = {"free"}
COLLECTION_EXPORTS = "laurentia_pdf_exports"

# Tags / attrs autorisés (suffisant pour markdown standard)
_ALLOWED_TAGS = [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "strong", "em", "b", "i", "u", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "div", "span",
]
_ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "*": ["class"],
}


class PdfExportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    subtitle: str | None = Field(default=None, max_length=240)
    content_md: str = Field(min_length=1, max_length=MAX_MD_CHARS)
    footer_note: str | None = Field(default=None, max_length=240)
    session_id: str | None = Field(default=None, max_length=120)


def _md_to_safe_html(content_md: str) -> str:
    raw_html = md_lib.markdown(
        content_md,
        extensions=["extra", "sane_lists", "tables", "fenced_code"],
    )
    return bleach.clean(raw_html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s).strip("-").lower()
    return s[:60] or "rapport"


def _public_url() -> str:
    """URL publique racine (frontend). Fallback : variable backend si pas configurée."""
    return (
        os.environ.get("LAURENTIA_PUBLIC_URL")
        or os.environ.get("REACT_APP_BACKEND_URL")
        or "https://laurent.ia"
    ).rstrip("/")


def _make_qr_data_uri(payload: str) -> str:
    """Génère un QR code PNG → data: URI (inlinable dans le HTML)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0F1F", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


CSS_TEMPLATE = """
@page {
  size: A4;
  margin: 22mm 18mm 24mm 18mm;
  @bottom-left {
    content: "Laurent.ia · Intelligence souveraine · CVLN Group";
    font-family: "Urbanist", "Helvetica", sans-serif;
    font-size: 8pt;
    color: #6b7280;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-family: "Urbanist", "Helvetica", sans-serif;
    font-size: 8pt;
    color: #6b7280;
  }
}
@page :nth(1) { }
@page signature {
  margin: 28mm 22mm 30mm 22mm;
}
:root {
  --ink: #0A0F1F;
  --gold: #C9A24B;
  --gold-soft: #E7C566;
  --muted: #4b5563;
  --line: #d1d5db;
}
* { box-sizing: border-box; }
body {
  font-family: "Urbanist", "Helvetica", sans-serif;
  font-size: 10.5pt;
  line-height: 1.6;
  color: var(--ink);
  margin: 0;
}
.cover {
  border-bottom: 1px solid var(--gold);
  padding-bottom: 18px;
  margin-bottom: 28px;
}
.brand-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-family: "Urbanist", sans-serif;
  font-size: 8.5pt;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 14px;
}
.brand-row .meta { color: var(--muted); letter-spacing: 0.18em; }
h1.title {
  font-family: "Cormorant Garamond", "Georgia", serif;
  font-size: 32pt;
  font-weight: 600;
  line-height: 1.1;
  color: var(--ink);
  margin: 0 0 6px 0;
  letter-spacing: -0.01em;
}
.subtitle {
  font-family: "Urbanist", sans-serif;
  font-size: 11pt;
  color: var(--muted);
  letter-spacing: 0.04em;
}

article h1, article h2, article h3, article h4 {
  font-family: "Cormorant Garamond", "Georgia", serif;
  font-weight: 600;
  color: var(--ink);
  margin-top: 22px;
  margin-bottom: 6px;
  line-height: 1.2;
}
article h1 { font-size: 22pt; border-bottom: 1px solid var(--line); padding-bottom: 4px; }
article h2 { font-size: 17pt; }
article h3 { font-size: 14pt; color: var(--gold); }
article h4 { font-size: 12pt; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }

article p { margin: 8px 0; text-align: justify; }
article ul, article ol { padding-left: 22px; margin: 8px 0; }
article li { margin: 3px 0; }

article strong { color: var(--ink); font-weight: 700; }
article em { color: var(--gold); font-style: italic; }

article blockquote {
  border-left: 3px solid var(--gold);
  background: #fafaf7;
  padding: 8px 14px;
  margin: 12px 0;
  font-family: "Cormorant Garamond", serif;
  font-style: italic;
  font-size: 12pt;
  color: var(--ink);
}

article code {
  font-family: "IBM Plex Mono", "Menlo", monospace;
  font-size: 9.5pt;
  background: #f4f4f1;
  padding: 1px 4px;
  border-radius: 3px;
}
article pre {
  background: #0A0F1F;
  color: #f1f4fa;
  padding: 10px 12px;
  border-radius: 4px;
  font-size: 9pt;
  overflow-x: auto;
  border-left: 3px solid var(--gold);
}
article pre code { background: transparent; color: inherit; padding: 0; }

article table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 9.5pt;
}
article th {
  background: var(--ink);
  color: #fff;
  font-weight: 600;
  text-align: left;
  padding: 6px 10px;
  letter-spacing: 0.04em;
  font-size: 9pt;
  text-transform: uppercase;
}
article td {
  border-bottom: 1px solid var(--line);
  padding: 6px 10px;
}
article tr:last-child td { border-bottom: 0; }

article a { color: var(--gold); text-decoration: none; border-bottom: 1px dotted var(--gold); }

.footer-note {
  margin-top: 28px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 8.5pt;
  color: var(--muted);
  font-style: italic;
}

/* === Signature de la Constellation (page finale Free tier) === */
.signature-page {
  page-break-before: always;
  page: signature;
  text-align: center;
  padding-top: 30mm;
}
.signature-mark {
  display: inline-block;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #E7C566 0%, #C9A24B 55%, #0A0F1F 100%);
  box-shadow: 0 0 24px rgba(201, 162, 75, 0.45);
  margin-bottom: 26px;
}
.signature-page h2 {
  font-family: "Cormorant Garamond", serif;
  font-size: 28pt;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 0.01em;
  margin: 0 auto 6px;
  max-width: 540px;
  line-height: 1.2;
}
.signature-page .signature-subtitle {
  font-family: "Urbanist", sans-serif;
  font-size: 10pt;
  text-transform: uppercase;
  letter-spacing: 0.28em;
  color: var(--gold);
  margin-bottom: 38px;
}
.signature-page .qr-frame {
  display: inline-block;
  padding: 14px;
  background: white;
  border: 2px solid var(--gold);
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(10, 15, 31, 0.08);
  margin-bottom: 18px;
}
.signature-page .qr-frame img { width: 160px; height: 160px; display: block; }
.signature-page .qr-caption {
  font-family: "IBM Plex Mono", monospace;
  font-size: 8.5pt;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}
.signature-page .qr-url {
  font-family: "IBM Plex Mono", monospace;
  font-size: 9pt;
  color: var(--ink);
  word-break: break-all;
  max-width: 480px;
  margin: 0 auto 32px;
}
.signature-page .ribbon {
  margin: 0 auto;
  max-width: 500px;
  border-top: 1px solid var(--gold);
  border-bottom: 1px solid var(--gold);
  padding: 14px 8px;
}
.signature-page .ribbon p {
  font-family: "Cormorant Garamond", serif;
  font-style: italic;
  font-size: 13pt;
  color: var(--ink);
  margin: 0;
  line-height: 1.45;
}
.signature-page .signature-meta {
  margin-top: 30px;
  font-family: "Urbanist", sans-serif;
  font-size: 8pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
}
"""

# Web fonts inlined via Google Fonts CSS (WeasyPrint suit @import).
GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400"
    "&family=Urbanist:wght@300;400;500;600;700"
    "&family=IBM+Plex+Mono:wght@400;500&display=swap"
)


def _signature_section_html(session_id: str | None) -> str:
    """Page de signature avec QR vers /echo/{session_id} (ou racine si absent)."""
    base = _public_url()
    target = f"{base}/echo/{session_id}" if session_id else base
    qr_uri = _make_qr_data_uri(target)
    return f"""
  <section class="signature-page">
    <div class="signature-mark"></div>
    <h2>Certifié par l'Infrastructure Laurent.ia</h2>
    <div class="signature-subtitle">Connaissance Souveraine de la Diaspora · CVLN Group</div>
    <div class="qr-frame">
      <img src="{qr_uri}" alt="QR de vérification" />
    </div>
    <div class="qr-caption">Vérifier l'authenticité — scan</div>
    <div class="qr-url">{target}</div>
    <div class="ribbon">
      <p>« La parole reste. Le sceau valide. La constellation veille. »</p>
    </div>
    <div class="signature-meta">Document scellé · {datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")}</div>
  </section>"""


def _build_html(req: PdfExportRequest, include_signature: bool) -> str:
    body_html = _md_to_safe_html(req.content_md)
    ts = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    subtitle_html = (
        f'<div class="subtitle">{bleach.clean(req.subtitle, tags=[], strip=True)}</div>'
        if req.subtitle else ""
    )
    footer_html = (
        f'<div class="footer-note">{bleach.clean(req.footer_note, tags=[], strip=True)}</div>'
        if req.footer_note else ""
    )
    title_safe = bleach.clean(req.title, tags=[], strip=True)
    signature_html = _signature_section_html(req.session_id) if include_signature else ""
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{title_safe}</title>
<link rel="stylesheet" href="{GOOGLE_FONTS}">
</head>
<body>
  <section class="cover">
    <div class="brand-row">
      <span>Laurent.ia · CVLN Group</span>
      <span class="meta">{ts}</span>
    </div>
    <h1 class="title">{title_safe}</h1>
    {subtitle_html}
  </section>
  <article>
    {body_html}
  </article>
  {footer_html}
  {signature_html}
</body>
</html>"""


async def _resolve_tier_from_device(request: Request, device_fp: str | None) -> tuple[str, str | None]:
    """
    Retourne (tier, device_id).
    - Si device_fp fourni → tente de résoudre via la dernière `laurentia_instance`
      liée à ce device (champ `device_ids` ajouté côté gateway).
    - Fallback : 'free'.
    """
    device_id = device_id_from_fingerprint(device_fp)
    if not device_id:
        return "free", None
    db = request.app.state.db
    inst = await db.laurentia_instances.find_one(
        {"device_ids": device_id},
        {"_id": 0, "tier": 1, "version": 1},
    )
    if not inst:
        return "free", device_id
    return (inst.get("tier") or inst.get("version") or "free").lower(), device_id


async def _consume_free_quota(request: Request, device_id: str) -> tuple[int, int]:
    """
    Incrémente le compteur d'exports Free pour le device_id sur le mois en cours.
    Lève HTTPException(402) si le seuil est franchi.
    Retourne (used_after_increment, FREE_EXPORTS_PER_MONTH).
    """
    db = request.app.state.db
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    coll = db[COLLECTION_EXPORTS]

    # Comptage avant incrémentation
    existing = await coll.find_one({"device_id": device_id, "month": month})
    used = int(existing["count"]) if existing else 0
    if used >= FREE_EXPORTS_PER_MONTH:
        raise HTTPException(
            status_code=402,
            detail=(
                "Tu as utilisé tes 2 exports PDF gratuits du mois. "
                "Passe au tier Creator 🪙 (€15/mois) pour des exports illimités sans signature finale."
            ),
            headers={
                "X-Laurentia-Free-Used": str(used),
                "X-Laurentia-Free-Limit": str(FREE_EXPORTS_PER_MONTH),
                "X-Laurentia-Paywall": "creator",
            },
        )
    # Incrémente atomiquement
    await coll.update_one(
        {"device_id": device_id, "month": month},
        {
            "$inc": {"count": 1},
            "$set": {"last_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"device_id": device_id, "month": month, "created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )
    return used + 1, FREE_EXPORTS_PER_MONTH


@router.post("/pdf")
async def export_pdf(payload: PdfExportRequest, request: Request):
    device_fp = request.headers.get("x-device-fingerprint") or request.headers.get("X-Device-Fingerprint")
    tier, device_id = await _resolve_tier_from_device(request, device_fp)
    is_free = tier in PAYWALL_TIERS

    used_after = 0
    limit = FREE_EXPORTS_PER_MONTH
    if is_free and device_id:
        used_after, limit = await _consume_free_quota(request, device_id)

    include_signature = is_free  # Signature uniquement Free tier

    try:
        html_str = _build_html(payload, include_signature=include_signature)
        pdf_bytes = HTML(string=html_str).write_pdf(stylesheets=[CSS(string=CSS_TEMPLATE)])
    except Exception as e:
        logger.exception("pdf_export_failed")
        raise HTTPException(500, f"Génération PDF échouée : {e}")

    filename = f"laurentia-{_slugify(payload.title)}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Laurentia-Signature": "1" if include_signature else "0",
            "X-Laurentia-Free-Used": str(used_after),
            "X-Laurentia-Free-Limit": str(limit),
            "X-Laurentia-Tier": tier,
        },
    )


@router.get("/pdf/quota")
async def pdf_quota(request: Request):
    """Renvoie l'état du quota Free pour le device courant (pour pré-affichage UI)."""
    device_fp = request.headers.get("x-device-fingerprint") or request.headers.get("X-Device-Fingerprint")
    tier, device_id = await _resolve_tier_from_device(request, device_fp)
    if tier not in PAYWALL_TIERS or not device_id:
        return {"tier": tier, "unlimited": True, "free_exports_used": 0, "free_exports_limit": 0}
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    doc = await request.app.state.db[COLLECTION_EXPORTS].find_one(
        {"device_id": device_id, "month": month}, {"_id": 0, "count": 1}
    )
    used = int((doc or {}).get("count", 0))
    return {
        "tier": tier,
        "unlimited": False,
        "free_exports_used": used,
        "free_exports_limit": FREE_EXPORTS_PER_MONTH,
        "free_exports_remaining": max(0, FREE_EXPORTS_PER_MONTH - used),
    }
