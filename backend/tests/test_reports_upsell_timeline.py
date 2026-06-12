"""
test_reports_upsell_timeline.py — Chantier 10 frontend dashboard support :
  - compute_upsell_hint logique anti-spam (âge compte, seuils)
  - compute_user_timeline shape 7 jours avec zéros
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pymongo
import pytest

from jobs.reports import (
    compute_upsell_hint,
    compute_user_timeline,
    compute_user_daily,
)


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _fresh_db():
    cli = pymongo.MongoClient(MONGO_URL)
    name = f"{DB_NAME}_test_upsell_{uuid4().hex[:8]}"
    return cli, cli[name], name


# ---------- Upsell hint (logique anti-spam) ----------

def test_upsell_hint_infinite_returns_none():
    assert compute_upsell_hint(tier="infinite", total_actions_window=1000,
                               time_saved_min_window=10000,
                               account_created_at=None) is None


def test_upsell_hint_pro_returns_none():
    assert compute_upsell_hint(tier="pro", total_actions_window=1000,
                               time_saved_min_window=10000,
                               account_created_at=None) is None


def test_upsell_hint_account_too_young_returns_none():
    """Compte créé hier → JAMAIS d'upsell même si beaucoup d'actions."""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert compute_upsell_hint(tier="free", total_actions_window=100,
                               time_saved_min_window=500,
                               account_created_at=yesterday) is None


def test_upsell_hint_low_usage_returns_none():
    """Compte vieux mais <20 actions / <60min → pas de hint."""
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    assert compute_upsell_hint(tier="free", total_actions_window=5,
                               time_saved_min_window=15,
                               account_created_at=old) is None


def test_upsell_hint_free_meets_thresholds():
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    h = compute_upsell_hint(tier="free", total_actions_window=25,
                            time_saved_min_window=120,
                            account_created_at=old)
    assert h is not None
    assert h["target_tier"] == "creator"
    assert h["soft"] is True
    assert "headline" in h
    assert "cta" in h


def test_upsell_hint_free_high_time_saved_only():
    """Si peu d'actions MAIS beaucoup de minutes (lourdes tâches) → hint OK."""
    old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    h = compute_upsell_hint(tier="free", total_actions_window=10,
                            time_saved_min_window=90,
                            account_created_at=old)
    assert h is not None
    assert h["target_tier"] == "creator"


def test_upsell_hint_creator_to_infinite_thresholds():
    old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    # Creator avec usage modéré → pas de hint
    assert compute_upsell_hint(tier="creator", total_actions_window=30,
                               time_saved_min_window=60,
                               account_created_at=old) is None
    # Creator avec usage intense → hint vers Infinite
    h = compute_upsell_hint(tier="creator", total_actions_window=100,
                            time_saved_min_window=300,
                            account_created_at=old)
    assert h is not None
    assert h["target_tier"] == "infinite"


def test_upsell_hint_unknown_creation_date_treated_as_old():
    """account_created_at=None → considéré vieux (age=999), donc check normal."""
    h = compute_upsell_hint(tier="free", total_actions_window=25,
                            time_saved_min_window=120,
                            account_created_at=None)
    assert h is not None  # threshold respecté → hint
    h2 = compute_upsell_hint(tier="free", total_actions_window=5,
                             time_saved_min_window=10,
                             account_created_at=None)
    assert h2 is None  # threshold pas respecté → pas de hint


# ---------- Timeline ----------

def test_timeline_empty_returns_zeros_for_all_days():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await compute_user_timeline(adb, "FREK-NONE", days=7)
        out = asyncio.run(run())
        assert len(out) == 7
        assert all(d["minutes"] == 0 and d["actions"] == 0 for d in out)
        # Format date YYYY-MM-DD trié croissant
        for i in range(1, 7):
            assert out[i]["date"] > out[i - 1]["date"]
    finally:
        cli.drop_database(name)


def test_timeline_aggregates_minutes_per_day():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        now = datetime.now(timezone.utc)
        today_iso = now.isoformat()
        two_days_ago = (now - timedelta(days=2)).isoformat()
        db.laurentia_activity_log.insert_many([
            {"frek_id": "F1", "action": "QUERY_PROCESSED", "tier": "free",
             "time_saved_min": 5, "is_alert": False, "ts": today_iso},
            {"frek_id": "F1", "action": "QUERY_PROCESSED", "tier": "free",
             "time_saved_min": 5, "is_alert": False, "ts": today_iso},
            {"frek_id": "F1", "action": "PDF_EXPORT", "tier": "free",
             "time_saved_min": 15, "is_alert": False, "ts": two_days_ago},
        ])

        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await compute_user_timeline(adb, "F1", days=7)
        out = asyncio.run(run())
        assert len(out) == 7
        # Aujourd'hui = dernier élément
        assert out[-1]["minutes"] == 10
        assert out[-1]["actions"] == 2
        # J-2 = 5e élément (out[4])
        assert out[4]["minutes"] == 15
    finally:
        cli.drop_database(name)


# ---------- compute_user_daily intègre timeline + upsell_hint ----------

def test_compute_user_daily_includes_timeline_and_upsell_fields():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await compute_user_daily(adb, "FREK-X", hours=24)
        rep = asyncio.run(run())
        assert "timeline" in rep
        assert "upsell_hint" in rep
        assert isinstance(rep["timeline"], list)
        # Empty user → upsell_hint = None (pas de spam)
        assert rep["upsell_hint"] is None
    finally:
        cli.drop_database(name)
