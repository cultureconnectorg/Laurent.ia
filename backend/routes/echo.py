"""
echo.py — Pipeline d'Échos omnicanal et Landing publique.

Endpoints :
  POST /api/laurentia/echo                → Génère 3 reformulations (LinkedIn/X, WhatsApp/Signal, Stories 9:16)
                                            à partir d'un session_id + interaction_id (ou d'un texte brut).
                                            Persiste le résultat dans `laurentia_echoes`.
  GET  /api/echo/{session_id}             → JSON public : titre, formats, méta SEO/OG.
  POST /api/echo/{session_id}/conversion  → Attribution : trace le clic CTA → création compte Creator.

La page publique frontend `/echo/{session_id}` consomme GET /api/echo/{session_id}
et déclenche POST /api/echo/{session_id}/conversion au clic du bouton « Activer ».
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services import cvl_brain
from services.crypto import decrypt_text
from services.fingerprint import device_id_from_fingerprint

logger = logging.getLogger(__name__)

# /api/laurentia/echo (génération) + /api/echo (consultation publique)
private_router = APIRouter(prefix="/api/laurentia", tags=["echo"])
public_router = APIRouter(prefix="/api/echo", tags=["echo-public"])


ECHO_SYSTEM_PROMPT = """Tu es le Pipeline d'Échos de Laurent.ia. À partir d'une analyse
souveraine fournie, produis EXACTEMENT trois reformulations en JSON pur. AUCUN texte
autour, AUCUN ``` ni Markdown. Schema strict :

{
  "title": "<6-12 mots, percutant, orientation business>",
  "summary": "<2 phrases — l'essentiel de l'insight pour quelqu'un qui n'a pas lu l'analyse>",
  "pro": {
    "headline": "<accroche LinkedIn/X 1 ligne>",
    "body": "<analyse structurée 100-180 mots, ton expert, 1-2 puces si pertinent, finit par une question d'ouverture>",
    "hashtags": ["<3 à 5 tags pertinents sans #>"]
  },
  "instant": {
    "lead": "<phrase d'accroche 1 ligne, percutante>",
    "bullets": ["<3 à 5 bullets de 1-2 lignes max, condensé, prêt WhatsApp>"]
  },
  "visual": {
    "punchlines": ["<3 punchlines isolées, 6-14 mots chacune, citations conceptuelles>"],
    "color_hint": "gold|blue|mixed"
  }
}

Règles : pas de "AI", pas de mention "Laurent.ia", pas de générique vide. Pense livrable
diffusable demain matin. Si la matière est faible, dis-le dans summary plutôt que de meubler."""


class EchoGenerateRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    raw_text: str | None = Field(default=None, max_length=8000)


def _trim(s: str, n: int = 4000) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + " …"


async def _fetch_session_content(db, session_id: str) -> tuple[str, str | None]:
    """Récupère le dernier output assistant de la session (déchiffré). Renvoie (text, frek_id)."""
    cursor = db.laurentia_interactions.find(
        {"session_id": session_id},
        {"_id": 0, "output_text": 1, "input_text": 1, "tenant_id": 1, "timestamp": 1},
        sort=[("timestamp", -1)],
    )
    docs = await cursor.to_list(length=3)
    if not docs:
        return "", None
    # Concatène les derniers exchanges (déchiffrés)
    parts = []
    for d in reversed(docs):
        u = decrypt_text(d.get("input_text"))
        a = decrypt_text(d.get("output_text"))
        if u:
            parts.append(f"[Question] {_trim(u, 800)}")
        if a:
            parts.append(f"[Réponse] {_trim(a, 1800)}")
    return "\n\n".join(parts), docs[0].get("tenant_id")


def _parse_json_strict(raw: str) -> dict:
    """Parse robuste : tolère un éventuel ```json autour."""
    import json
    txt = raw.strip()
    if txt.startswith("```"):
        # Strip the fence
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:].strip()
        # Re-strip trailing fence remnants
        end = txt.rfind("}")
        if end != -1:
            txt = txt[: end + 1]
    return json.loads(txt)


@private_router.post("/echo")
async def generate_echo(payload: EchoGenerateRequest, request: Request):
    db = request.app.state.db

    # 1. Source : session existante OU raw_text fourni
    if payload.raw_text:
        source = _trim(payload.raw_text, 6000)
        frek_tenant = None
    else:
        source, frek_tenant = await _fetch_session_content(db, payload.session_id)
        if not source:
            raise HTTPException(404, "Session introuvable ou vide.")

    # 2. Génération via Claude
    try:
        full = ""
        async for chunk in cvl_brain.chat_stream(
            user_text=f"Analyse à reformuler :\n\n{source}",
            system_message=ECHO_SYSTEM_PROMPT,
            session_id=f"echo-{payload.session_id}",
        ):
            full += chunk
        parsed = _parse_json_strict(full)
    except Exception as e:
        logger.exception("echo_generation_failed")
        raise HTTPException(502, f"Génération d'écho échouée : {e}")

    # 3. Validation minimale + sanitization
    required = {"title", "summary", "pro", "instant", "visual"}
    if not required.issubset(parsed.keys()):
        raise HTTPException(502, "Format d'écho invalide. Réessaie.")

    # 4. Persistance — distinct $set (updateable) vs $setOnInsert (initial-only)
    now = datetime.now(timezone.utc).isoformat()
    set_fields = {
        "session_id": payload.session_id,
        "tenant_id": frek_tenant,
        "echo": parsed,
        "updated_at": now,
        "is_public": True,
    }
    await db.laurentia_echoes.update_one(
        {"session_id": payload.session_id},
        {
            "$set": set_fields,
            "$setOnInsert": {"created_at": now, "views": 0, "conversions": 0},
        },
        upsert=True,
    )

    return {
        "ok": True,
        "session_id": payload.session_id,
        "public_url": f"/echo/{payload.session_id}",
        "echo": parsed,
    }


# ---------------- PUBLIC (no auth) ----------------

@public_router.get("/{session_id}")
async def get_public_echo(session_id: str, request: Request):
    db = request.app.state.db
    doc = await db.laurentia_echoes.find_one({"session_id": session_id}, {"_id": 0})
    if not doc or not doc.get("is_public", True):
        raise HTTPException(404, "Écho introuvable ou retiré.")

    # Tracking de vue (best-effort, ne bloque pas la lecture)
    try:
        await db.laurentia_echoes.update_one(
            {"session_id": session_id},
            {"$inc": {"views": 1}, "$set": {"last_view_at": datetime.now(timezone.utc).isoformat()}},
        )
    except Exception:
        pass

    echo = doc["echo"]
    return {
        "session_id": session_id,
        "title": echo.get("title"),
        "summary": echo.get("summary"),
        "pro": echo.get("pro"),
        "instant": echo.get("instant"),
        "visual": echo.get("visual"),
        "views": doc.get("views", 0),
        "conversions": doc.get("conversions", 0),
        "created_at": doc.get("created_at"),
    }


class ConversionPing(BaseModel):
    source: str = Field(default="echo_cta", max_length=40)


@public_router.post("/{session_id}/conversion")
async def track_conversion(session_id: str, payload: ConversionPing, request: Request):
    db = request.app.state.db
    device_fp = request.headers.get("x-device-fingerprint") or request.headers.get("X-Device-Fingerprint")
    device_id = device_id_from_fingerprint(device_fp)
    now = datetime.now(timezone.utc)

    await db.laurentia_echoes.update_one(
        {"session_id": session_id},
        {
            "$inc": {"conversions": 1},
            "$set": {"last_conversion_at": now.isoformat()},
        },
    )
    await db.laurentia_echo_attributions.insert_one({
        "session_id": session_id,
        "source": payload.source,
        "visitor_device_id": device_id,
        "ts": now,
    })
    return {"ok": True, "session_id": session_id, "redirect": "/?from_echo=" + session_id}
