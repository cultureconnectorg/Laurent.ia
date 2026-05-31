"""
test_social_agent.py — Chantier 7 social_agent.py

Couvre :
  - theme_for_today retourne thème valide
  - generate_content : extraction JSON + retry + skip si Claude down
  - generate_and_publish en mode SOCIAL_MANUAL_APPROVAL → pending_approval, pas de publication
  - generate_and_publish en mode auto avec tous les réseaux down → all_failed
  - fallback visual_b64=None si SD indisponible
"""
import asyncio
import os
import json
from uuid import uuid4

import pytest
import pymongo

from jobs import social_agent as sa


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _fresh_db():
    cli = pymongo.MongoClient(MONGO_URL)
    name = f"{DB_NAME}_test_social_{uuid4().hex[:8]}"
    return cli, cli[name], name


def test_theme_for_today_returns_valid_theme():
    t = sa.theme_for_today()
    assert t in sa.WEEKLY_THEMES.values()
    assert t in sa.THEME_BRIEFS


def test_extract_json_clean_response():
    raw = '{"instagram": "post IG", "linkedin": "post LI", "twitter": "tw", "visual_prompt": "vp"}'
    d = sa._extract_json(raw)
    assert d["instagram"] == "post IG"
    assert d["twitter"] == "tw"


def test_extract_json_with_code_fence():
    raw = '```json\n{"instagram": "x", "linkedin": "y", "twitter": "z", "visual_prompt": "v"}\n```'
    d = sa._extract_json(raw)
    assert d.get("instagram") == "x"


def test_extract_json_invalid_returns_empty():
    assert sa._extract_json("pas du json du tout") == {}
    assert sa._extract_json("") == {}


def test_generate_content_skips_after_retries(monkeypatch):
    """Si Claude lève en permanence → retourne {} après max_retries."""
    async def _boom(*a, **k):
        raise RuntimeError("claude down")
    monkeypatch.setattr(sa.cvl_brain, "chat_enriched", _boom)
    result = asyncio.run(sa.generate_content("vision", max_retries=2))
    assert result == {}


def test_generate_content_success(monkeypatch):
    async def _ok(*a, **k):
        return '{"instagram": "ig texte", "linkedin": "li texte", "twitter": "tw texte", "visual_prompt": "vp"}'
    monkeypatch.setattr(sa.cvl_brain, "chat_enriched", _ok)
    result = asyncio.run(sa.generate_content("vision", max_retries=1))
    assert result["instagram"] == "ig texte"
    assert result["twitter"] == "tw texte"
    assert result["visual_prompt"] == "vp"


def test_generate_and_publish_manual_approval_pending(monkeypatch):
    """Mode SOCIAL_MANUAL_APPROVAL=true → status=pending_approval, jamais publié."""
    cli, db, name = _fresh_db()
    try:
        # Mock Claude
        async def _ok(*a, **k):
            return '{"instagram": "ig", "linkedin": "li", "twitter": "tw", "visual_prompt": "vp"}'
        monkeypatch.setattr(sa.cvl_brain, "chat_enriched", _ok)
        # SD indisponible
        async def _no_visual(*a, **k): return None
        monkeypatch.setattr(sa.image_generator, "generate_visual", _no_visual)
        # Force manual approval ON
        monkeypatch.setattr(sa, "SOCIAL_MANUAL_APPROVAL", True)
        # Spy publication — doit JAMAIS être appelé
        called = {"ig": 0, "li": 0, "tw": 0}
        async def _spy_ig(*a, **k): called["ig"] += 1; return {"ok": True}
        async def _spy_li(*a, **k): called["li"] += 1; return {"ok": True}
        async def _spy_tw(*a, **k): called["tw"] += 1; return {"ok": True}
        monkeypatch.setattr(sa, "_publish_instagram", _spy_ig)
        monkeypatch.setattr(sa, "_publish_linkedin",  _spy_li)
        monkeypatch.setattr(sa, "_publish_twitter",   _spy_tw)

        from motor.motor_asyncio import AsyncIOMotorClient
        adb = AsyncIOMotorClient(MONGO_URL)[name]
        result = asyncio.run(sa.generate_and_publish(adb))
        assert result["status"] == "pending_approval"
        assert called == {"ig": 0, "li": 0, "tw": 0}
        # Post persisté avec visual_b64=None (SD down)
        posts = list(db.laurentia_social_posts.find({}, {"_id": 0}))
        assert len(posts) == 1
        assert posts[0]["status"] == "pending_approval"
        assert posts[0]["visual_b64"] is None
    finally:
        cli.drop_database(name)


def test_generate_and_publish_all_networks_down(monkeypatch):
    """force_publish=True + tous réseaux down → status=all_failed, pas de crash."""
    cli, db, name = _fresh_db()
    try:
        async def _ok(*a, **k):
            return '{"instagram": "ig", "linkedin": "li", "twitter": "tw", "visual_prompt": "vp"}'
        monkeypatch.setattr(sa.cvl_brain, "chat_enriched", _ok)
        async def _no_visual(*a, **k): return None
        monkeypatch.setattr(sa.image_generator, "generate_visual", _no_visual)
        async def _down(*a, **k): return {"ok": False, "reason": "not_configured"}
        monkeypatch.setattr(sa, "_publish_instagram", _down)
        monkeypatch.setattr(sa, "_publish_linkedin",  _down)
        monkeypatch.setattr(sa, "_publish_twitter",   _down)

        from motor.motor_asyncio import AsyncIOMotorClient
        adb = AsyncIOMotorClient(MONGO_URL)[name]
        result = asyncio.run(sa.generate_and_publish(adb, force_publish=True))
        assert result["status"] == "all_failed"
        assert result["platforms"] == []
    finally:
        cli.drop_database(name)


def test_generate_and_publish_partial_success(monkeypatch):
    """Twitter OK, Instagram + LinkedIn down → status=published, platforms=[twitter]."""
    cli, db, name = _fresh_db()
    try:
        async def _ok(*a, **k):
            return '{"instagram": "ig", "linkedin": "li", "twitter": "tw", "visual_prompt": "vp"}'
        monkeypatch.setattr(sa.cvl_brain, "chat_enriched", _ok)
        async def _no_visual(*a, **k): return None
        monkeypatch.setattr(sa.image_generator, "generate_visual", _no_visual)
        async def _down(*a, **k): return {"ok": False, "reason": "not_configured"}
        async def _ok_tw(*a, **k): return {"ok": True, "post_id": "tw-123"}
        monkeypatch.setattr(sa, "_publish_instagram", _down)
        monkeypatch.setattr(sa, "_publish_linkedin",  _down)
        monkeypatch.setattr(sa, "_publish_twitter",   _ok_tw)

        from motor.motor_asyncio import AsyncIOMotorClient
        adb = AsyncIOMotorClient(MONGO_URL)[name]
        result = asyncio.run(sa.generate_and_publish(adb, force_publish=True))
        assert result["status"] == "published"
        assert result["platforms"] == ["twitter"]
    finally:
        cli.drop_database(name)


def test_generate_and_publish_skips_when_paused(monkeypatch):
    cli, db, name = _fresh_db()
    try:
        db.laurentia_settings.insert_one(
            {"key": sa.SOCIAL_PAUSE_FLAG, "value": True}
        )
        from motor.motor_asyncio import AsyncIOMotorClient
        adb = AsyncIOMotorClient(MONGO_URL)[name]
        result = asyncio.run(sa.generate_and_publish(adb))
        assert result["status"] == "paused"
        # Aucun post inséré
        assert db.laurentia_social_posts.count_documents({}) == 0
    finally:
        cli.drop_database(name)
