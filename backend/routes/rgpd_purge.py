"""
rgpd_purge.py — Purge automatique J+90 de la correspondance device_id ↔ frek_id.

Politique souveraine v1.2 :
  - Conserve la donnée chiffrée (interactions, memory) — elle alimente le corpus
    d'entraînement futur.
  - Mais à J+90, on RETIRE le lien d'identification :
        laurentia_instances.device_ids → vidé pour les instances > 90j inactives
        laurentia_echo_attributions.visitor_device_id → réécrit à null
        laurentia_pdf_exports          → conservé pour comptabilité mais device_id haché à nouveau
  - Le résultat : un dataset d'analyses pures sans table de liaison identitaire.

Fréquence : déclenché au startup (best-effort, non bloquant) puis toutes les 24h.

Endpoint admin (idempotent) :
  POST /api/admin/rgpd/purge   →  exécute immédiatement, renvoie le nombre d'opérations.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/rgpd", tags=["admin"])

PURGE_AFTER_DAYS = 90
PURGE_INTERVAL_SECONDS = 24 * 3600  # une fois par jour


async def purge_once(db) -> dict:
    """Exécute une passe complète de purge J+90. Retourne le rapport."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PURGE_AFTER_DAYS)).isoformat()
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=PURGE_AFTER_DAYS)

    # 1. Instances inactives depuis >90j → vider device_ids
    res_inst = await db.laurentia_instances.update_many(
        {"last_active": {"$lt": cutoff}, "device_ids": {"$exists": True, "$ne": []}},
        {"$set": {"device_ids": [], "rgpd_purged_at": datetime.now(timezone.utc).isoformat()}},
    )

    # 2. Attributions echo > 90j → anonymiser visitor_device_id
    res_attr = await db.laurentia_echo_attributions.update_many(
        {"ts": {"$lt": cutoff_dt}, "visitor_device_id": {"$ne": None}},
        {"$set": {"visitor_device_id": None, "rgpd_purged_at": datetime.now(timezone.utc)}},
    )

    # 3. Exports PDF des mois > 3 → device_id anonymisé (on garde les counts agrégés)
    three_months_ago = (datetime.now(timezone.utc) - timedelta(days=PURGE_AFTER_DAYS)).strftime("%Y-%m")
    res_exp = await db.laurentia_pdf_exports.update_many(
        {"month": {"$lt": three_months_ago}, "device_id": {"$exists": True, "$ne": None}},
        {"$set": {"device_id": None, "rgpd_purged_at": datetime.now(timezone.utc)}},
    )

    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "cutoff_days": PURGE_AFTER_DAYS,
        "instances_anonymized": res_inst.modified_count if res_inst else 0,
        "echo_attributions_anonymized": res_attr.modified_count if res_attr else 0,
        "pdf_exports_anonymized": res_exp.modified_count if res_exp else 0,
    }
    logger.info("rgpd_purge_completed %s", report)
    return report


def schedule_periodic_purge(app, db) -> None:
    """Lance un loop asyncio en arrière-plan. Best-effort, non bloquant."""
    async def _loop():
        while True:
            try:
                await purge_once(db)
            except Exception as e:
                logger.warning("rgpd_purge_loop_error: %s", e)
            await asyncio.sleep(PURGE_INTERVAL_SECONDS)

    task = asyncio.create_task(_loop())
    # Garde une référence pour éviter qu'asyncio garbage-collect la task
    app.state.rgpd_purge_task = task


@router.post("/purge")
async def trigger_purge(request: Request):
    db = request.app.state.db
    return await purge_once(db)
