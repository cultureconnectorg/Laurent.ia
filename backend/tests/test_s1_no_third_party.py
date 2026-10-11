"""S1.5 — no third-party resource is loaded by the page or by PDF rendering (T4)."""
import io
import pathlib
import re

from pypdf import PdfReader
from weasyprint import CSS, HTML

from routes import pdf_export

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = ROOT / "frontend" / "public" / "index.html"
ANALYTICS = re.compile(r"posthog|emergent\.sh|emergent-main|googletagmanager|google-analytics|gtag\(|mixpanel|hotjar|segment\.com", re.I)


def test_index_html_loads_no_external_script_or_stylesheet():
    html = INDEX.read_text(encoding="utf-8")
    external = re.findall(r'<(?:script|link)\b[^>]*(?:src|href)="(https?:)?//[^"]+"', html, re.I)
    assert external == [], external


def test_index_html_has_no_analytics_or_session_recording():
    assert not ANALYTICS.search(INDEX.read_text(encoding="utf-8"))


def test_frontend_sources_and_dependencies_have_no_analytics_sdk():
    hits = []
    for path in list((ROOT / "frontend" / "src").rglob("*.js*")) + [ROOT / "frontend" / "package.json"]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"posthog|mixpanel|googletagmanager|google-analytics|@sentry|hotjar", text, re.I):
            hits.append(f"{path.relative_to(ROOT)}: {m.group(0)}")
    assert hits == [], hits


def test_self_hosted_fonts_referenced_by_the_page_exist():
    css = (ROOT / "frontend" / "public" / "fonts" / "fonts.css").read_text(encoding="utf-8")
    files = re.findall(r'url\("([^"]+)"\)', css)
    assert files and all((INDEX.parent / "fonts" / f).is_file() for f in files)


def test_pdf_rendering_uses_local_fonts_without_network():
    # The autouse network guard fails this test if rendering tries to reach any host.
    req = pdf_export.PdfExportRequest(title="Titre", content_md="Contenu **gras**", session_id="s1")
    html = pdf_export._build_html(req, include_signature=True)
    assert "googleapis" not in html
    pdf = HTML(string=html).write_pdf(stylesheets=[CSS(string=pdf_export.CSS_TEMPLATE)])
    embedded = {
        str(font.get_object()["/BaseFont"])
        for page in PdfReader(io.BytesIO(pdf)).pages
        for font in (page["/Resources"].get("/Font") or {}).values()
    }
    for family in ("Urbanist", "Cormorant-Garamond", "IBM-Plex-Mono"):
        assert any(family in name for name in embedded), (family, embedded)
