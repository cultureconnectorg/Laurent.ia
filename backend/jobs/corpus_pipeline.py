"""
corpus_pipeline.py — Cron hebdomadaire (dimanche 03:00 heure Martinique, UTC-4).

Mission : transformer les interactions Laurent.ia consenties en corpus
JSONL de fine-tuning, scoré, anonymisé, chiffré et versionné sur OVHcloud
Object Storage (S3-compatible).

Comportement Go-LIVE :
  - Si OVHCLOUD_S3_* non configuré → écrit le JSONL en local (/tmp/laurentia_corpus/)
    et logge la version. Aucune publication réelle, mais pipeline complet testé.
  - Le rapport est TOUJOURS écrit dans laurentia_corpus_reports.

Sélection :
  laurentia_interactions WHERE corpus_eligible=True
  AND anonymized_at IS NULL AND user_rating != -1
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Martinique = UTC-4 (pas de DST)
MARTINIQUE_TZ = timezone(timedelta(hours=-4))

OVHCLOUD_S3_KEY = os.environ.get("OVHCLOUD_S3_KEY", "")
OVHCLOUD_S3_SECRET = os.environ.get("OVHCLOUD_S3_SECRET", "")
OVHCLOUD_S3_BUCKET = os.environ.get("OVHCLOUD_S3_BUCKET", "laurentia-corpus")
OVHCLOUD_S3_ENDPOINT = os.environ.get("OVHCLOUD_S3_ENDPOINT", "https://s3.gra.io.cloud.ovh.net")
OVHCLOUD_S3_REGION = os.environ.get("OVHCLOUD_S3_REGION", "gra")

# Liste créole — détection lexicale légère
_CREOLE_MARKERS = {
    "moun", "tjè", "tjè-a", "bagay", "fanmi", "kontan", "lespri", "lavi",
    "péyi", "péyi-a", "doudou", "manmay", "tibwa", "anlè", "anba", "kò",
    "soti", "rivé", "rété", "fè", "ka", "ké", "an", "épi", "asou",
    "lanmou", "lakay", "lanmè", "soley", "lalin", "péyizan", "frè", "sè",
}

_CARIBBEAN_MARKERS = {
    "martinique", "guadeloupe", "guyane", "haiti", "haïti", "caraïbe", "caraïbes",
    "antilles", "fort-de-france", "schoelcher", "césaire", "fanon", "glissant",
    "kreyòl", "créole", "marronnage", "coeurvolan", "cvln", "frek",
    "kiltikonet", "laurent.ia", "labelos", "souveraineté", "souverain",
}

# Patterns PII résiduels à scrubber (par sécurité, on suppose anonymisation amont)
_PII_PATTERNS = [
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # CB
    re.compile(r"\b\d{2}[\s\-./]?\d{2}[\s\-./]?\d{2}[\s\-./]?\d{2}[\s\-./]?\d{2}\b"),  # tel FR
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),  # email
    re.compile(r"\bFREK-[A-Z0-9]+\b"),  # FREK-ID en clair
]


def _scrub_pii(text: str) -> str:
    out = text or ""
    for p in _PII_PATTERNS:
        out = p.sub("[REDACTED]", out)
    return out


def _normalize_creole(text: str) -> str:
    """Normalisation légère — espaces multiples, apostrophes typographiques."""
    if not text:
        return ""
    t = text.replace("’", "'").replace("‘", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _score_culturel(text: str) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    hits = sum(1 for w in _CREOLE_MARKERS if w in lower)
    # Saturation à 5 marqueurs → 1.0
    return min(hits / 5.0, 1.0)


def _score_souverain(text: str) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    hits = sum(1 for w in _CARIBBEAN_MARKERS if w in lower)
    return min(hits / 3.0, 1.0)


def _score_pertinence(output: str, satisfaction: float) -> float:
    length_factor = min(len(output or "") / 1000.0, 1.0)
    return length_factor * max(0.0, min(satisfaction, 1.0))


def score_interaction(interaction: dict) -> dict:
    """
    Scorer une interaction.

    Retourne {culturel, pertinence, souverain, global}.
    Pondération : culturel 0.30 · pertinence 0.40 · souverain 0.30
    """
    user_in = interaction.get("input") or interaction.get("user_input") or ""
    bot_out = interaction.get("output") or interaction.get("bot_output") or ""
    rating = interaction.get("user_rating", 0)
    # user_rating ∈ {-1, 0, 1} → satisfaction ∈ [0, 1]
    satisfaction = 1.0 if rating == 1 else (0.5 if rating == 0 else 0.0)

    s_cult = _score_culturel(f"{user_in} {bot_out}")
    s_pert = _score_pertinence(bot_out, satisfaction)
    s_souv = _score_souverain(f"{user_in} {bot_out}")
    s_global = 0.30 * s_cult + 0.40 * s_pert + 0.30 * s_souv
    return {"culturel": s_cult, "pertinence": s_pert, "souverain": s_souv, "global": s_global}


def format_jsonl(interaction: dict) -> str:
    """Formate une interaction en ligne JSONL { prompt, completion }."""
    prompt = _scrub_pii(_normalize_creole(interaction.get("input") or ""))
    completion = _scrub_pii(_normalize_creole(interaction.get("output") or ""))
    return json.dumps({"prompt": prompt, "completion": completion}, ensure_ascii=False)


def _upload_corpus_s3(payload: bytes, version_key: str) -> Optional[str]:
    """
    Upload chiffré AES-256 vers OVHcloud Object Storage (S3-compatible).
    Retourne l'URL versionnée ou None si non configuré / échec.
    """
    if not (OVHCLOUD_S3_KEY and OVHCLOUD_S3_SECRET and OVHCLOUD_S3_BUCKET):
        return None
    try:
        import boto3  # local import — boto3 lourd, ne charge que si nécessaire
        s3 = boto3.client(
            "s3",
            aws_access_key_id=OVHCLOUD_S3_KEY,
            aws_secret_access_key=OVHCLOUD_S3_SECRET,
            endpoint_url=OVHCLOUD_S3_ENDPOINT,
            region_name=OVHCLOUD_S3_REGION,
        )
        s3.put_object(
            Bucket=OVHCLOUD_S3_BUCKET,
            Key=version_key,
            Body=payload,
            ServerSideEncryption="AES256",
            ContentType="application/jsonl",
        )
        return f"s3://{OVHCLOUD_S3_BUCKET}/{version_key}"
    except Exception as e:
        logger.warning("corpus_pipeline: S3 upload failed (%s)", e)
        return None


def _write_local_fallback(payload: bytes, version_key: str) -> str:
    """Fallback local pour dev/test — écrit le JSONL dans /tmp/laurentia_corpus/."""
    local_dir = Path(os.environ.get("LAURENTIA_CORPUS_LOCAL_DIR", "/tmp/laurentia_corpus"))
    local_dir.mkdir(parents=True, exist_ok=True)
    path = local_dir / version_key.replace("/", "_")
    path.write_bytes(payload)
    return str(path)


async def _next_corpus_version(db) -> int:
    """Calcule la prochaine version corpus_v{n}."""
    last = await db.laurentia_corpus_reports.find_one(
        {}, sort=[("version", -1)], projection={"_id": 0, "version": 1}
    )
    if last and isinstance(last.get("version"), int):
        return last["version"] + 1
    return 1


async def run_corpus_pipeline(db, *, score_threshold: float = 0.7) -> dict:
    """
    Exécute le pipeline corpus complet.
    Retourne un rapport et l'écrit dans laurentia_corpus_reports.
    """
    started = datetime.now(timezone.utc)
    cursor = db.laurentia_interactions.find(
        {"corpus_eligible": True, "anonymized_at": None, "user_rating": {"$ne": -1}},
        {"_id": 0},
    )
    interactions = await cursor.to_list(length=100_000)

    retained_lines: list[str] = []
    retained_ids: list[str] = []
    rejected = 0
    score_sum = 0.0
    tokens_total = 0

    for it in interactions:
        scores = score_interaction(it)
        score_sum += scores["global"]
        if scores["global"] < score_threshold:
            rejected += 1
            continue
        line = format_jsonl(it)
        retained_lines.append(line)
        retained_ids.append(it.get("interaction_id") or it.get("id") or "")
        tokens_total += int(it.get("tokens", 0) or len((it.get("output") or "")) // 4)

    version_n = await _next_corpus_version(db)
    version_key = f"corpus_v{version_n}/{started.strftime('%Y%m%d')}.jsonl"
    payload = ("\n".join(retained_lines) + "\n").encode("utf-8") if retained_lines else b""

    storage_uri = _upload_corpus_s3(payload, version_key) if payload else None
    if payload and not storage_uri:
        storage_uri = _write_local_fallback(payload, version_key)

    # Marque anonymized_at sur les interactions retenues (idempotent)
    if retained_ids:
        await db.laurentia_interactions.update_many(
            {"interaction_id": {"$in": retained_ids}},
            {"$set": {"anonymized_at": started.isoformat()}},
        )

    report = {
        "date": started.isoformat(),
        "version": version_n,
        "interactions_traitees": len(interactions),
        "retenues": len(retained_lines),
        "rejetees": rejected,
        "tokens_total": tokens_total,
        "score_moyen": (score_sum / len(interactions)) if interactions else 0.0,
        "storage_uri": storage_uri,
        "score_threshold": score_threshold,
    }
    await db.laurentia_corpus_reports.insert_one(dict(report))
    logger.info("corpus_pipeline_done version=%s retained=%s rejected=%s",
                version_n, len(retained_lines), rejected)
    return report


def _seconds_until_next_sunday_3am_martinique() -> float:
    """Calcule les secondes jusqu'au prochain dimanche 03:00 heure Martinique."""
    now_mq = datetime.now(MARTINIQUE_TZ)
    # weekday: Mon=0 … Sun=6
    days_ahead = (6 - now_mq.weekday()) % 7
    target = now_mq.replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    if target <= now_mq:
        target += timedelta(days=7)
    return (target - now_mq).total_seconds()


def schedule_corpus_pipeline(app, db) -> None:
    """Lance le loop hebdomadaire en arrière-plan. Best-effort, non bloquant."""
    async def _loop():
        while True:
            try:
                wait_s = _seconds_until_next_sunday_3am_martinique()
                await asyncio.sleep(max(wait_s, 60.0))
                await run_corpus_pipeline(db)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("corpus_pipeline_loop_error: %s", e)
                await asyncio.sleep(3600)

    task = asyncio.create_task(_loop())
    app.state.corpus_pipeline_task = task
