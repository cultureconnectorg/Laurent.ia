"""
social_admin.py — Routes admin pour superviser le Social Agent & Corpus Pipeline.

Auth : role ∈ {"founder", "admin"} (recyclage de get_current_user existant).
"""
from __future__ import annotations

import asyncio
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routes.auth import require_user
from jobs import social_agent, corpus_pipeline

router = APIRouter(prefix="/api/admin", tags=["social_admin"])


async def _require_admin(request: Request) -> dict:
    user = await require_user(request)
    role = (user.get("role") or "").lower()
    if role not in ("founder", "admin"):
        raise HTTPException(403, "Accès admin requis")
    return user


# ---------- Social posts ----------

@router.get("/social/posts")
async def list_social_posts(request: Request, limit: int = 50):
    await _require_admin(request)
    db = request.app.state.db
    cursor = db.laurentia_social_posts.find({}, {"_id": 0}).sort("date", -1).limit(max(1, min(limit, 200)))
    posts = await cursor.to_list(length=limit)
    # Attache analytics J+1 si présent
    ids = [p["post_id"] for p in posts]
    analytics = {}
    if ids:
        a_cur = db.laurentia_social_analytics.find({"post_id": {"$in": ids}}, {"_id": 0})
        for row in await a_cur.to_list(length=1000):
            analytics[row["post_id"]] = row
    for p in posts:
        p["analytics"] = analytics.get(p["post_id"])
    return {"posts": posts, "count": len(posts)}


@router.get("/social/preview")
async def preview_today(request: Request):
    """Génère (sans publier) le post du jour pour relecture."""
    await _require_admin(request)
    theme = social_agent.theme_for_today()
    content = await social_agent.generate_content(theme)
    if not content:
        raise HTTPException(503, "Génération Claude indisponible")
    return {"theme": theme, **content}


class ApproveRequest(BaseModel):
    post_id: Optional[str] = None
    generate_now: bool = False


@router.post("/social/approve")
async def approve_post(payload: ApproveRequest, request: Request):
    """
    Approve un post pending_approval et publie.
    Si generate_now=True ET aucun post_id fourni → génère + publie immédiatement
    (bypass SOCIAL_MANUAL_APPROVAL).
    """
    await _require_admin(request)
    db = request.app.state.db
    if payload.generate_now and not payload.post_id:
        return await social_agent.generate_and_publish(db, force_publish=True)
    if not payload.post_id:
        raise HTTPException(400, "post_id requis")

    admin = await _require_admin(request)
    post = await db.laurentia_social_posts.find_one({"post_id": payload.post_id}, {"_id": 0})
    if not post:
        raise HTTPException(404, "Post inconnu")
    if post.get("status") not in ("pending_approval", "all_failed"):
        return {"status": post.get("status"), "post_id": payload.post_id, "note": "already_processed"}

    # Re-publication réelle
    ig, li, tw = await asyncio.gather(
        social_agent._publish_instagram(post["instagram_text"], post.get("visual_b64")),
        social_agent._publish_linkedin(post["linkedin_text"]),
        social_agent._publish_twitter(post["twitter_text"]),
    )
    platforms, post_ids = [], {}
    if ig.get("ok"):
        platforms.append("instagram")
        post_ids["instagram"] = ig.get("post_id")
    if li.get("ok"):
        platforms.append("linkedin")
        post_ids["linkedin"] = li.get("post_id")
    if tw.get("ok"):
        platforms.append("twitter")
        post_ids["twitter"] = tw.get("post_id")

    final = "published" if platforms else "all_failed"
    await db.laurentia_social_posts.update_one(
        {"post_id": payload.post_id},
        {"$set": {
            "platforms": platforms, "post_ids": post_ids, "status": final,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "errors": {"instagram": ig, "linkedin": li, "twitter": tw},
            "approved_by": admin.get("user_id"),
        }},
    )
    return {"status": final, "post_id": payload.post_id, "platforms": platforms}


class PauseRequest(BaseModel):
    paused: bool = True


@router.post("/social/pause")
async def pause_social_agent(payload: PauseRequest, request: Request):
    await _require_admin(request)
    db = request.app.state.db
    await db.laurentia_settings.update_one(
        {"key": social_agent.SOCIAL_PAUSE_FLAG},
        {"$set": {"value": bool(payload.paused),
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"paused": bool(payload.paused)}


# ---------- Corpus pipeline ----------

@router.get("/corpus/stats")
async def corpus_stats(request: Request, limit: int = 20):
    await _require_admin(request)
    db = request.app.state.db
    cursor = db.laurentia_corpus_reports.find({}, {"_id": 0}).sort("date", -1).limit(max(1, min(limit, 100)))
    reports = await cursor.to_list(length=limit)
    return {"reports": reports, "count": len(reports)}


@router.post("/corpus/run")
async def corpus_run_now(request: Request):
    """Déclenche le pipeline corpus manuellement (admin)."""
    await _require_admin(request)
    db = request.app.state.db
    report = await corpus_pipeline.run_corpus_pipeline(db)
    return report


@router.get("/corpus/export")
async def corpus_export(request: Request, version: Optional[int] = None):
    """Télécharge le JSONL du corpus (dernière version par défaut)."""
    await _require_admin(request)
    db = request.app.state.db
    query = {"version": version} if version else {}
    report = await db.laurentia_corpus_reports.find_one(query, {"_id": 0}, sort=[("version", -1)])
    if not report:
        raise HTTPException(404, "Aucun rapport corpus disponible")

    # Reconstruit le JSONL en relisant les interactions retenues à la date du rapport
    # (mode fallback simple — si S3 absent, on régénère à partir de la DB)
    cursor = db.laurentia_interactions.find(
        {"corpus_eligible": True, "anonymized_at": {"$ne": None}},
        {"_id": 0, "input": 1, "output": 1},
    )
    lines = []
    for it in await cursor.to_list(length=100_000):
        lines.append(json.dumps(
            {"prompt": it.get("input", ""), "completion": it.get("output", "")},
            ensure_ascii=False,
        ))
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    return StreamingResponse(
        io.BytesIO(payload),
        media_type="application/jsonl",
        headers={"Content-Disposition": f'attachment; filename="laurentia_corpus_v{report["version"]}.jsonl"'},
    )
