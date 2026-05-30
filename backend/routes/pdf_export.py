"""
pdf_export.py — Export PDF souverain (WeasyPrint) avec charte CVLN.

Endpoints :
  POST /api/export/pdf
    body JSON :
      {
        "title": "Analyse stratégique remittances",
        "subtitle": "Note Laurent.ia",            # optionnel
        "content_md": "...markdown...",
        "footer_note": "..."                       # optionnel
      }
    headers :
      X-Device-Fingerprint   (optionnel — rate-limit unifié)
    réponse :
      application/pdf (stream), filename suggested via Content-Disposition

Charte graphique CVLN :
  Fond blanc épuré corporate, titres en Cormorant Garamond (souveraineté),
  textes en Urbanist (technologie), accents dorés (#C9A24B / #E7C566).
  Bleu nuit profond #0A0F1F en filet de titre et en pied de page.

Sécurité :
  - Limite payload markdown : 50_000 chars.
  - Sanitization minimaliste : on rend du Markdown→HTML via `markdown` (bleach
    pour stripper le HTML brut entrant). WeasyPrint exécute du CSS, pas du JS.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone

import bleach
import markdown as md_lib
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])

MAX_MD_CHARS = 50_000

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


def _md_to_safe_html(content_md: str) -> str:
    raw_html = md_lib.markdown(
        content_md,
        extensions=["extra", "sane_lists", "tables", "fenced_code"],
    )
    return bleach.clean(raw_html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s).strip("-").lower()
    return s[:60] or "rapport"


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
"""

# Web fonts inlined via Google Fonts CSS (WeasyPrint suit @import).
GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400"
    "&family=Urbanist:wght@300;400;500;600;700"
    "&family=IBM+Plex+Mono:wght@400;500&display=swap"
)


def _build_html(req: PdfExportRequest) -> str:
    body_html = _md_to_safe_html(req.content_md)
    ts = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    subtitle_html = f'<div class="subtitle">{bleach.clean(req.subtitle, tags=[], strip=True)}</div>' if req.subtitle else ""
    footer_html = (
        f'<div class="footer-note">{bleach.clean(req.footer_note, tags=[], strip=True)}</div>'
        if req.footer_note else ""
    )
    title_safe = bleach.clean(req.title, tags=[], strip=True)
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
</body>
</html>"""


@router.post("/pdf")
async def export_pdf(payload: PdfExportRequest, request: Request):
    try:
        html_str = _build_html(payload)
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
        },
    )
