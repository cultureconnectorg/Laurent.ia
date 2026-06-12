"""
test_chantier10.py — Pyramide Tenants + Reports + API Keys.
"""
import asyncio
import os
from uuid import uuid4

import pymongo
import pytest

from services import api_keys, value_estimator
from services.tenant_factory import (
    ALLOCATIONS,
    Tenant,
    TenantFactory,
    allocation_for,
    tenant_allows,
)
from jobs import reports as reports_job


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _fresh_db():
    cli = pymongo.MongoClient(MONGO_URL)
    name = f"{DB_NAME}_test_chantier10_{uuid4().hex[:8]}"
    return cli, cli[name], name


# ---------- Value Estimator ----------

def test_value_estimator_defaults():
    assert value_estimator.estimate("QUERY_PROCESSED") == 5
    assert value_estimator.estimate("PDF_EXPORT") == 15
    assert value_estimator.estimate("ECHO_SHARED") == 20
    assert value_estimator.estimate("UNKNOWN_ACTION") == 0


def test_value_estimator_env_override(monkeypatch):
    monkeypatch.setenv("LAURENTIA_VALUE_QUERY_PROCESSED", "10")
    assert value_estimator.estimate("QUERY_PROCESSED") == 10


def test_value_estimator_with_weight():
    assert value_estimator.estimate("QUERY_PROCESSED", weight=2.0) == 10


# ---------- Tenant allocation ----------

def test_allocations_have_proper_sizes():
    assert len(ALLOCATIONS["free"]) == 3
    assert len(ALLOCATIONS["creator"]) == 10
    assert len(ALLOCATIONS["pro"]) == 20
    assert len(ALLOCATIONS["infinite"]) == 20


def test_tenant_allows_strict_pyramid():
    # Free n'a PAS d'agent créatif
    assert not tenant_allows("free", "agent-redaction")
    # Creator a guardrail-text, mais pas d'iconographe
    assert tenant_allows("creator", "agent-guardrail-text")
    assert not tenant_allows("creator", "agent-visuel")
    # Infinite a tout
    for spec_id in ALLOCATIONS["infinite"]:
        assert tenant_allows("infinite", spec_id)


def test_allocation_for_unknown_tier_defaults_to_free():
    assert allocation_for("nonexistent_tier") == allocation_for("free")
    assert allocation_for(None) == allocation_for("free")


# ---------- Tenant log_activity ----------

def test_tenant_log_activity_persists_with_estimation():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            t = Tenant(frek_id="FREK-T1", tier="creator", db=adb)
            doc = await t.log_activity("QUERY_PROCESSED")
            assert doc["time_saved_min"] == 5
            # Custom time_saved override
            doc2 = await t.log_activity("PDF_EXPORT", time_saved=60)
            assert doc2["time_saved_min"] == 60

        asyncio.run(run())
        rows = list(db.laurentia_activity_log.find({"frek_id": "FREK-T1"}))
        assert len(rows) == 2
        assert {r["action"] for r in rows} == {"QUERY_PROCESSED", "PDF_EXPORT"}
    finally:
        cli.drop_database(name)


def test_tenant_factory_resolves_tier_from_instances():
    cli, db, name = _fresh_db()
    try:
        db.laurentia_instances.insert_one({"frek_id": "FREK-CREATOR", "tier": "creator"})

        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            factory = TenantFactory(adb)
            t = await factory.get_tenant("FREK-CREATOR")
            return t.snapshot()

        snap = asyncio.run(run())
        assert snap["tier"] == "creator"
        assert snap["agent_count"] == 10
    finally:
        cli.drop_database(name)


def test_tenant_factory_default_tier_for_unknown_user():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            factory = TenantFactory(adb)
            t = await factory.get_tenant("FREK-UNKNOWN")
            return t.snapshot()
        snap = asyncio.run(run())
        assert snap["tier"] == "free"
        assert snap["agent_count"] == 3
    finally:
        cli.drop_database(name)


# ---------- API Keys ----------

def test_api_key_create_validate_revoke_roundtrip():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        adb_url = MONGO_URL
        async def run():
            adb = AsyncIOMotorClient(adb_url)[name]
            created = await api_keys.create_key(adb, frek_id="FREK-K1", tier="creator", label="test")
            assert created["raw_key"].startswith("lia_creator_")
            assert created["status"] == "active"
            raw = created["raw_key"]
            # Validate
            doc = await api_keys.validate_key(adb, raw)
            assert doc is not None
            assert doc["frek_id"] == "FREK-K1"
            assert doc["tier"] == "creator"
            # List
            ks = await api_keys.list_keys(adb, frek_id="FREK-K1")
            assert len(ks) == 1
            assert ks[0]["label"] == "test"
            # Use count incremented
            doc2 = await api_keys.validate_key(adb, raw)
            assert doc2 is not None
            ks_after = await api_keys.list_keys(adb, frek_id="FREK-K1")
            assert ks_after[0]["use_count"] >= 2
            # Revoke
            ok = await api_keys.revoke_key(adb, frek_id="FREK-K1", key_id=created["key_id"])
            assert ok is True
            # After revoke → validate returns None
            doc3 = await api_keys.validate_key(adb, raw)
            assert doc3 is None
            # Double revoke returns False
            ok2 = await api_keys.revoke_key(adb, frek_id="FREK-K1", key_id=created["key_id"])
            assert ok2 is False

        asyncio.run(run())
    finally:
        cli.drop_database(name)


def test_api_key_rejects_other_tenants_keys():
    """Tenant A ne peut PAS révoquer une clé de Tenant B."""
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            created = await api_keys.create_key(adb, frek_id="FREK-A", tier="free", label="a")
            # B essaie de révoquer la clé de A
            ok = await api_keys.revoke_key(adb, frek_id="FREK-B", key_id=created["key_id"])
            assert ok is False
            # La clé de A reste valide
            doc = await api_keys.validate_key(adb, created["raw_key"])
            assert doc is not None

        asyncio.run(run())
    finally:
        cli.drop_database(name)


def test_api_key_invalid_format_returns_none():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            assert await api_keys.validate_key(adb, "not-a-real-key") is None
            assert await api_keys.validate_key(adb, "") is None
        asyncio.run(run())
    finally:
        cli.drop_database(name)


# ---------- Reports ----------

def test_compute_user_daily_empty_returns_zero_stats():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await reports_job.compute_user_daily(adb, "FREK-EMPTY", hours=24)
        rep = asyncio.run(run())
        assert rep["total_actions"] == 0
        assert rep["time_saved_min"] == 0
        assert rep["by_action"] == []
        assert rep["tier"] == "free"
    finally:
        cli.drop_database(name)


def test_compute_user_daily_aggregates_correctly():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        db.laurentia_instances.insert_one({"frek_id": "FREK-AGG", "tier": "creator"})
        db.laurentia_activity_log.insert_many([
            {"frek_id": "FREK-AGG", "tier": "creator", "action": "QUERY_PROCESSED",
             "time_saved_min": 5, "is_alert": False, "ts": now},
            {"frek_id": "FREK-AGG", "tier": "creator", "action": "QUERY_PROCESSED",
             "time_saved_min": 5, "is_alert": False, "ts": now},
            {"frek_id": "FREK-AGG", "tier": "creator", "action": "PDF_EXPORT",
             "time_saved_min": 15, "is_alert": True, "ts": now},
        ])

        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await reports_job.compute_user_daily(adb, "FREK-AGG", hours=24)

        rep = asyncio.run(run())
        assert rep["total_actions"] == 3
        assert rep["time_saved_min"] == 25
        assert rep["alerts"] == 1
        assert rep["tier"] == "creator"
        actions = {a["action"]: a for a in rep["by_action"]}
        assert actions["QUERY_PROCESSED"]["count"] == 2
        assert actions["PDF_EXPORT"]["time_saved_min"] == 15
    finally:
        cli.drop_database(name)


def test_compute_founder_daily_aggregates_tenants_and_tiers():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        db.laurentia_activity_log.insert_many([
            {"frek_id": "FREK-A", "tier": "free", "action": "QUERY_PROCESSED",
             "time_saved_min": 5, "is_alert": False, "ts": now},
            {"frek_id": "FREK-B", "tier": "creator", "action": "PDF_EXPORT",
             "time_saved_min": 15, "is_alert": False, "ts": now},
            {"frek_id": "FREK-C", "tier": "infinite", "action": "ECHO_SHARED",
             "time_saved_min": 20, "is_alert": True, "ts": now},
        ])

        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await reports_job.compute_founder_daily(adb, hours=24)

        rep = asyncio.run(run())
        assert rep["active_tenants"] == 3
        assert rep["tier_distribution"] == {"free": 1, "creator": 1, "infinite": 1}
        assert rep["total_actions"] == 3
        assert rep["time_saved_min"] == 40
        assert rep["total_alerts"] == 1
    finally:
        cli.drop_database(name)


def test_snapshot_daily_persists_reports():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        db.laurentia_activity_log.insert_many([
            {"frek_id": "FREK-S1", "tier": "creator", "action": "QUERY_PROCESSED",
             "time_saved_min": 5, "is_alert": False, "ts": now},
            {"frek_id": "FREK-S2", "tier": "free", "action": "QUERY_PROCESSED",
             "time_saved_min": 5, "is_alert": False, "ts": now},
        ])

        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await reports_job.snapshot_daily(adb)

        res = asyncio.run(run())
        assert res["tenant_daily_reports"] == 2
        founder_count = db.laurentia_reports_daily.count_documents({"report_type": "founder_daily"})
        user_count = db.laurentia_reports_daily.count_documents({"report_type": "user_daily"})
        assert founder_count == 1
        assert user_count == 2
        # Idempotence : second snapshot replace, not duplicate
        asyncio.run(run())
        assert db.laurentia_reports_daily.count_documents({"report_type": "founder_daily"}) == 1
        assert db.laurentia_reports_daily.count_documents({"report_type": "user_daily"}) == 2
    finally:
        cli.drop_database(name)


def test_compute_founder_weekly_includes_paid_subscribers():
    cli, db, name = _fresh_db()
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        db.laurentia_instances.insert_many([
            {"frek_id": "P1", "tier": "creator"},
            {"frek_id": "P2", "tier": "infinite"},
            {"frek_id": "F1", "tier": "free"},
        ])

        async def run():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await reports_job.compute_founder_weekly(adb)

        rep = asyncio.run(run())
        assert rep["report_type"] == "weekly"
        assert rep["paid_subscribers"] == 2
    finally:
        cli.drop_database(name)
