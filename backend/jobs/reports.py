"""
reports.py — Génération de rapports daily/weekly (user + founder).

Cron quotidien 00:00 heure Martinique (UTC-4) :
  - snapshot daily user reports (un doc par frek_id actif dans les dernières 24h)
  - snapshot daily founder report (agrégé global)
  - Si lundi : snapshot weekly founder + weekly user reports

Lecture temps-réel via routes/reports.py si l'utilisateur consulte avant le cron.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

MARTINIQUE_TZ = timezone(timedelta(hours=-4))


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _window(hours: int) -> str:
    return _utc_iso(datetime.now(timezone.utc) - timedelta(hours=hours))


# ---------- Calcul des rapports ----------

async def compute_user_daily(db: AsyncIOMotorDatabase, frek_id: str,
                              *, hours: int = 24) -> dict:
    since = _window(hours)
    pipeline = [
        {"$match": {"frek_id": frek_id, "ts": {"$gte": since}}},
        {"$group": {
            "_id": "$action",
            "count": {"$sum": 1},
            "time_saved_min": {"$sum": "$time_saved_min"},
            "alerts": {"$sum": {"$cond": ["$is_alert", 1, 0]}},
        }},
        {"$sort": {"count": -1}},
    ]
    by_action = []
    total_actions = 0
    total_minutes = 0
    total_alerts = 0
    async for r in db.laurentia_activity_log.aggregate(pipeline):
        by_action.append({
            "action": r["_id"],
            "count": r["count"],
            "time_saved_min": r["time_saved_min"],
            "alerts": r["alerts"],
        })
        total_actions += r["count"]
        total_minutes += r["time_saved_min"]
        total_alerts += r["alerts"]

    # Top 3 incidents souverains affectant ce tenant (via session_id mapping si dispo)
    incidents_cur = db.laurentia_orchestrator_incidents.find(
        {"created_at": {"$gte": since}},
        {"_id": 0, "incident_id": 1, "agent": 1, "reason": 1, "summary": 1, "status": 1},
    ).sort("created_at", -1).limit(3)
    incidents = await incidents_cur.to_list(length=3)

    # Tier resolution + account age
    inst = await db.laurentia_instances.find_one(
        {"frek_id": frek_id}, {"_id": 0, "tier": 1, "version": 1, "created_at": 1}
    )
    tier = (inst or {}).get("tier") or (inst or {}).get("version") or "free"
    created_at = (inst or {}).get("created_at")

    # Timeline 7 derniers jours (pour la courbe)
    timeline = await compute_user_timeline(db, frek_id, days=max(7, hours // 24))

    # Upsell hint smart — pas de spam, only when value delivered
    upsell_hint = compute_upsell_hint(
        tier=tier,
        total_actions_window=total_actions,
        time_saved_min_window=total_minutes,
        account_created_at=created_at,
    )

    return {
        "frek_id": frek_id,
        "tier": tier,
        "window_hours": hours,
        "since": since,
        "total_actions": total_actions,
        "time_saved_min": total_minutes,
        "time_saved_hours": round(total_minutes / 60.0, 2),
        "alerts": total_alerts,
        "by_action": by_action,
        "top_incidents": incidents,
        "timeline": timeline,
        "upsell_hint": upsell_hint,
        "generated_at": _utc_iso(datetime.now(timezone.utc)),
    }


async def compute_user_timeline(db: AsyncIOMotorDatabase, frek_id: str,
                                 *, days: int = 7) -> list[dict]:
    """Renvoie [{date: 'YYYY-MM-DD', minutes: int, actions: int}, ...] des N derniers jours.
    Inclut les jours sans activité avec zéros pour une courbe propre."""
    since = _window(24 * days)
    pipeline = [
        {"$match": {"frek_id": frek_id, "ts": {"$gte": since}}},
        {"$addFields": {"day": {"$substr": ["$ts", 0, 10]}}},
        {"$group": {
            "_id": "$day",
            "minutes": {"$sum": "$time_saved_min"},
            "actions": {"$sum": 1},
        }},
    ]
    raw = {}
    async for r in db.laurentia_activity_log.aggregate(pipeline):
        raw[r["_id"]] = {"minutes": r["minutes"], "actions": r["actions"]}

    out: list[dict] = []
    today = datetime.now(timezone.utc).date()
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        rec = raw.get(key, {"minutes": 0, "actions": 0})
        out.append({"date": key, "minutes": rec["minutes"], "actions": rec["actions"]})
    return out


def compute_upsell_hint(*, tier: str, total_actions_window: int, time_saved_min_window: int,
                         account_created_at: str | None) -> dict | None:
    """
    Suggestion d'upsell SMART — ne s'affiche pas pour ne pas casser l'expérience.

    Règles :
      - Tier infinite/pro → None (déjà au max)
      - Compte < 3 jours OU < 20 actions cumulées → None (laisser le temps de tester)
      - Free + ≥20 actions sur la fenêtre OU ≥60 min sauvées → hint vers Creator
      - Creator + ≥80 actions OU ≥240 min sauvées → hint vers Infinite
    """
    tier = (tier or "free").lower()
    if tier in ("infinite", "pro"):
        return None

    # Âge du compte
    if account_created_at:
        try:
            created = datetime.fromisoformat(account_created_at.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created).days
        except Exception:
            age_days = 999
    else:
        age_days = 999
    if age_days < 3:
        return None

    if tier == "free":
        if total_actions_window < 20 and time_saved_min_window < 60:
            return None
        return {
            "target_tier": "creator",
            "headline": "Tu as gagné du temps. Active Creator pour aller plus loin.",
            "reason": f"+{time_saved_min_window // 60}h économisées · 7 agents Aigle débloqués (10/20)",
            "cta": "Voir Creator",
            "soft": True,
        }
    if tier == "creator":
        if total_actions_window < 80 and time_saved_min_window < 240:
            return None
        return {
            "target_tier": "infinite",
            "headline": "Tu utilises Laurent.ia intensément. Passe à Infinite.",
            "reason": "10 agents supplémentaires (créatifs, arbitrage, SMS alert) — pyramide complète",
            "cta": "Voir Infinite",
            "soft": True,
        }
    return None


async def compute_founder_daily(db: AsyncIOMotorDatabase, *, hours: int = 24) -> dict:
    since = _window(hours)

    # Agrégation par tenant
    tenant_pipeline = [
        {"$match": {"ts": {"$gte": since}}},
        {"$group": {
            "_id": "$frek_id",
            "tier": {"$last": "$tier"},
            "actions": {"$sum": 1},
            "time_saved_min": {"$sum": "$time_saved_min"},
            "alerts": {"$sum": {"$cond": ["$is_alert", 1, 0]}},
        }},
    ]
    tenants = []
    total_actions = 0
    total_minutes = 0
    total_alerts = 0
    tier_counts: dict[str, int] = {}
    async for r in db.laurentia_activity_log.aggregate(tenant_pipeline):
        tier = r.get("tier") or "free"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        total_actions += r["actions"]
        total_minutes += r["time_saved_min"]
        total_alerts += r["alerts"]
        tenants.append({
            "frek_id": r["_id"],
            "tier": tier,
            "actions": r["actions"],
            "time_saved_min": r["time_saved_min"],
            "alerts": r["alerts"],
        })

    # Latence p50/p95 via guardrail logs (agent-latence)
    lat_cur = db.laurentia_guardrail_logs.find(
        {"agent_id": "agent-latence", "ts": {"$gte": since}, "detail": {"$regex": "^latency="}},
        {"_id": 0, "detail": 1},
    )
    lat_values: list[int] = []
    async for row in lat_cur:
        try:
            lat_values.append(int(row["detail"].split("=")[1].rstrip("ms")))
        except Exception:
            pass
    lat_values.sort()
    p50 = lat_values[len(lat_values) // 2] if lat_values else None
    p95 = lat_values[max(0, int(len(lat_values) * 0.95) - 1)] if lat_values else None

    # Top incidents souverains
    inc_cur = db.laurentia_orchestrator_incidents.find(
        {"created_at": {"$gte": since}},
        {"_id": 0, "incident_id": 1, "agent": 1, "reason": 1, "summary": 1,
         "status": 1, "session_id": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10)
    incidents = await inc_cur.to_list(length=10)

    # Breach attempts (CHECK level)
    breach_count = await db.laurentia_guardrail_logs.count_documents(
        {"ts": {"$gte": since}, "level": {"$gte": 2}}
    )

    return {
        "window_hours": hours,
        "since": since,
        "active_tenants": len(tenants),
        "tier_distribution": tier_counts,
        "total_actions": total_actions,
        "time_saved_min": total_minutes,
        "time_saved_hours": round(total_minutes / 60.0, 2),
        "total_alerts": total_alerts,
        "breach_attempts": breach_count,
        "latency_ms_p50": p50,
        "latency_ms_p95": p95,
        "top_incidents": incidents,
        "top_tenants": sorted(tenants, key=lambda t: t["actions"], reverse=True)[:10],
        "generated_at": _utc_iso(datetime.now(timezone.utc)),
    }


async def compute_founder_weekly(db: AsyncIOMotorDatabase) -> dict:
    base = await compute_founder_daily(db, hours=24 * 7)
    base["report_type"] = "weekly"
    # Score corpus moyen sur la semaine
    rep_cur = db.laurentia_corpus_reports.find(
        {"date": {"$gte": base["since"]}}, {"_id": 0, "score_moyen": 1}
    )
    scores = [r["score_moyen"] for r in await rep_cur.to_list(length=20) if r.get("score_moyen") is not None]
    base["corpus_score_avg"] = round(sum(scores) / len(scores), 3) if scores else None
    # MRR estimé via subscriptions actives (laurentia_instances)
    paid_count = await db.laurentia_instances.count_documents(
        {"tier": {"$in": ["creator", "pro", "infinite"]}}
    )
    base["paid_subscribers"] = paid_count
    return base


# ---------- Snapshots persistés ----------

async def snapshot_daily(db: AsyncIOMotorDatabase) -> dict:
    today = datetime.now(MARTINIQUE_TZ).strftime("%Y-%m-%d")
    founder = await compute_founder_daily(db, hours=24)
    founder.update({"report_id": f"founder-daily-{today}",
                    "report_type": "founder_daily", "date": today})
    await db.laurentia_reports_daily.replace_one(
        {"report_id": founder["report_id"]}, founder, upsert=True
    )
    # Un rapport par tenant actif
    cursor = db.laurentia_activity_log.aggregate([
        {"$match": {"ts": {"$gte": _window(24)}}},
        {"$group": {"_id": "$frek_id"}},
    ])
    tenant_reports = 0
    async for row in cursor:
        user_rep = await compute_user_daily(db, row["_id"], hours=24)
        user_rep.update({"report_id": f"user-daily-{row['_id']}-{today}",
                         "report_type": "user_daily", "date": today})
        await db.laurentia_reports_daily.replace_one(
            {"report_id": user_rep["report_id"]}, user_rep, upsert=True
        )
        tenant_reports += 1
    return {"founder": True, "tenant_daily_reports": tenant_reports, "date": today}


async def snapshot_weekly(db: AsyncIOMotorDatabase) -> dict:
    week_label = datetime.now(MARTINIQUE_TZ).strftime("%G-W%V")
    founder = await compute_founder_weekly(db)
    founder.update({"report_id": f"founder-weekly-{week_label}",
                    "report_type": "founder_weekly", "week": week_label})
    await db.laurentia_reports_weekly.replace_one(
        {"report_id": founder["report_id"]}, founder, upsert=True
    )
    cursor = db.laurentia_activity_log.aggregate([
        {"$match": {"ts": {"$gte": _window(24 * 7)}}},
        {"$group": {"_id": "$frek_id"}},
    ])
    tenant_reports = 0
    async for row in cursor:
        user_rep = await compute_user_daily(db, row["_id"], hours=24 * 7)
        user_rep.update({"report_id": f"user-weekly-{row['_id']}-{week_label}",
                         "report_type": "user_weekly", "week": week_label})
        await db.laurentia_reports_weekly.replace_one(
            {"report_id": user_rep["report_id"]}, user_rep, upsert=True
        )
        tenant_reports += 1
    return {"founder": True, "tenant_weekly_reports": tenant_reports, "week": week_label}


# ---------- Scheduler ----------

def _seconds_until_next_midnight_martinique() -> float:
    now_mq = datetime.now(MARTINIQUE_TZ)
    target = (now_mq + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (target - now_mq).total_seconds()


def schedule_reports(app, db) -> None:
    async def _loop():
        while True:
            try:
                wait_s = _seconds_until_next_midnight_martinique()
                await asyncio.sleep(max(wait_s, 60.0))
                # Daily systématique
                await snapshot_daily(db)
                # Hebdomadaire le lundi (weekday=0 Martinique)
                if datetime.now(MARTINIQUE_TZ).weekday() == 0:
                    await snapshot_weekly(db)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("reports_loop_error: %s", e)
                await asyncio.sleep(3600)

    app.state.reports_task = asyncio.create_task(_loop())
