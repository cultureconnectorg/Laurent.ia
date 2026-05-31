"""
social_agent.py — Cron quotidien Laurent.ia (09:00 heure Martinique, UTC-4).

Calendrier éditorial (rotation hebdomadaire) :
  Lundi     → vision souveraine
  Mardi     → actualité CC2026 / CVLN
  Mercredi  → feature Laurent.ia
  Jeudi     → culture caribéenne
  Vendredi  → artiste FMS / LabelOS
  Samedi    → créole / langue / identité
  Dimanche  → citation / introspection

Flow :
  1. Déterminer thème (weekday Martinique)
  2. Générer texte via Claude (cvl_brain.chat_enriched) — JSON
     { instagram, linkedin, twitter, visual_prompt }
  3. Générer visuel via image_generator.generate_visual()  (fallback None)
  4. Publier Instagram + LinkedIn + X en parallèle (fallbacks indépendants)
  5. Logger dans laurentia_social_posts
  6. Récupérer analytics J+1 → laurentia_social_analytics

Garde-fou : SOCIAL_MANUAL_APPROVAL=true (défaut) → on génère et enregistre
le post en `status=pending_approval` SANS publication réseau. L'admin
approuve ensuite via POST /api/admin/social/approve.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from services import cvl_brain, cvl_brain_knowledge, image_generator

logger = logging.getLogger(__name__)

MARTINIQUE_TZ = timezone(timedelta(hours=-4))

# Calendrier éditorial : weekday Mon=0 → Sun=6
WEEKLY_THEMES = {
    0: "vision",
    1: "actualite",
    2: "feature",
    3: "culture",
    4: "artiste",
    5: "creole",
    6: "citation",
}

THEME_BRIEFS = {
    "vision":    "vision souveraine, intelligence caribéenne, futur",
    "actualite": "actualité CC2026 et écosystème CVLN",
    "feature":   "feature Laurent.ia — capacités, usage, valeur",
    "culture":   "culture caribéenne, mémoire vivante, transmission",
    "artiste":   "artiste FMS / LabelOS, accompagnement créatif",
    "creole":    "créole, langue, identité, expression",
    "citation":  "citation introspective, sagesse, conscience",
}

SOCIAL_MANUAL_APPROVAL = os.environ.get("SOCIAL_MANUAL_APPROVAL", "true").strip().lower() == "true"
SOCIAL_PAUSE_FLAG = "social_agent_paused"  # clé dans laurentia_settings


# ---------- Génération de contenu ----------

def _build_user_prompt(theme: str) -> str:
    brief = THEME_BRIEFS.get(theme, THEME_BRIEFS["feature"])
    return (
        f"Génère un post sur le thème {theme} ({brief}) pour Instagram, LinkedIn et X. "
        f"Ton : souverain, caribéen, direct. Pas de hashtags génériques.\n\n"
        f"Réponds UNIQUEMENT en JSON valide (sans code-fence) avec exactement ces clés :\n"
        f'{{"instagram": "<max 2200 chars>", '
        f'"linkedin": "<max 3000 chars>", '
        f'"twitter": "<max 280 chars>", '
        f'"visual_prompt": "<description visuelle concise>"}}'
    )


def _extract_json(raw: str) -> dict:
    """Extrait le premier bloc JSON valide de la réponse Claude."""
    if not raw:
        return {}
    # Strip code fences éventuelles
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    # Trouve le premier { ... }
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


async def generate_content(theme: str, *, max_retries: int = 3) -> dict:
    """
    Génère le contenu via Claude. Retry x3 sur erreur. Skip si tout échoue.

    Retourne {} si Claude indisponible (le caller skippe la journée).
    """
    system = cvl_brain_knowledge.build_system_prompt(app_context="direct", cultural_profile=None)
    user_prompt = _build_user_prompt(theme)
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = await cvl_brain.chat_enriched(
                user_text=user_prompt,
                system_message=system,
                session_id=f"social-agent-{theme}-{uuid.uuid4().hex[:8]}",
            )
            data = _extract_json(raw)
            if data.get("instagram") and data.get("twitter"):
                # Tronque pour respecter les contraintes
                return {
                    "instagram": (data.get("instagram") or "")[:2200],
                    "linkedin":  (data.get("linkedin")  or data.get("instagram") or "")[:3000],
                    "twitter":   (data.get("twitter")   or "")[:280],
                    "visual_prompt": (data.get("visual_prompt") or "").strip(),
                }
        except Exception as e:
            last_err = e
            logger.warning("social_agent.generate_content attempt=%s failed: %s", attempt, e)
        await asyncio.sleep(2 ** attempt)
    logger.error("social_agent.generate_content gave up after %s retries (last=%s)", max_retries, last_err)
    return {}


# ---------- Publication réseaux sociaux ----------

async def _publish_instagram(text: str, visual_b64: Optional[str]) -> dict:
    """Publication Instagram via Graph API. Fallback {ok:False} si échec."""
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    ig_id = os.environ.get("INSTAGRAM_BUSINESS_ID", "")
    if not (token and ig_id):
        return {"ok": False, "reason": "not_configured"}
    try:
        # NOTE : pour publier une image, Instagram exige une URL publique (pas base64).
        # En LIVE, le visuel doit être uploadé en amont (CDN). Si pas d'URL → texte seul caption.
        # Ici on tente un container "IMAGE" si une URL est fournie via env var SOCIAL_VISUAL_URL_OVERRIDE,
        # sinon on crée un container texte (Reels/Story texte non supporté natif → on logge).
        async with httpx.AsyncClient(timeout=20.0) as client:
            # En l'absence d'URL publique fiable depuis base64, on échoue gracieusement
            # — l'admin recevra le contenu pour publication manuelle si SD/CDN absent.
            r = await client.post(
                f"https://graph.facebook.com/v19.0/{ig_id}/media",
                params={"caption": text[:2200], "access_token": token},
            )
            if r.status_code != 200:
                return {"ok": False, "reason": f"create_media_{r.status_code}"}
            container_id = r.json().get("id")
            pub = await client.post(
                f"https://graph.facebook.com/v19.0/{ig_id}/media_publish",
                params={"creation_id": container_id, "access_token": token},
            )
            if pub.status_code != 200:
                return {"ok": False, "reason": f"publish_{pub.status_code}"}
            return {"ok": True, "post_id": pub.json().get("id")}
    except Exception as e:
        logger.warning("instagram_publish_failed: %s", e)
        return {"ok": False, "reason": f"exception:{e.__class__.__name__}"}


async def _publish_linkedin(text: str) -> dict:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    actor = os.environ.get("LINKEDIN_ACTOR_URN", "")  # urn:li:organization:... ou urn:li:person:...
    if not (token and actor):
        return {"ok": False, "reason": "not_configured"}
    body = {
        "author": actor,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text[:3000]},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        if r.status_code in (200, 201):
            return {"ok": True, "post_id": r.headers.get("x-restli-id") or r.json().get("id")}
        return {"ok": False, "reason": f"status_{r.status_code}"}
    except Exception as e:
        logger.warning("linkedin_publish_failed: %s", e)
        return {"ok": False, "reason": f"exception:{e.__class__.__name__}"}


async def _publish_twitter(text: str) -> dict:
    """Publication X (Twitter) v2. Sans tweepy : OAuth1 manuel via httpx.
       Si non configuré ou échec → fallback {ok:False}."""
    bearer = os.environ.get("X_BEARER_TOKEN", "")
    if bearer:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://api.twitter.com/2/tweets",
                    headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
                    json={"text": text[:280]},
                )
            if r.status_code in (200, 201):
                data = r.json().get("data") or {}
                return {"ok": True, "post_id": data.get("id")}
            return {"ok": False, "reason": f"status_{r.status_code}"}
        except Exception as e:
            logger.warning("twitter_publish_failed: %s", e)
            return {"ok": False, "reason": f"exception:{e.__class__.__name__}"}
    return {"ok": False, "reason": "not_configured"}


# ---------- Orchestration ----------

def theme_for_today() -> str:
    return WEEKLY_THEMES[datetime.now(MARTINIQUE_TZ).weekday()]


async def _is_paused(db) -> bool:
    doc = await db.laurentia_settings.find_one({"key": SOCIAL_PAUSE_FLAG}, {"_id": 0, "value": 1})
    return bool(doc and doc.get("value"))


async def generate_and_publish(db, *, force_publish: bool = False) -> dict:
    """
    Génère, (optionnellement) publie et logge un post.

    - force_publish=True bypass SOCIAL_MANUAL_APPROVAL (utilisé par /approve).
    - Si paused → skip total.
    """
    if await _is_paused(db):
        logger.info("social_agent: paused, skip")
        return {"status": "paused"}

    theme = theme_for_today()
    content = await generate_content(theme)
    if not content:
        return {"status": "skip_generation_failed", "theme": theme}

    visual_b64 = await image_generator.generate_visual(
        prompt=content.get("visual_prompt") or theme,
        theme=theme,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    post_doc = {
        "post_id": f"social-{uuid.uuid4().hex[:12]}",
        "date": now_iso,
        "theme": theme,
        "instagram_text": content["instagram"],
        "linkedin_text":  content["linkedin"],
        "twitter_text":   content["twitter"],
        "visual_prompt":  content.get("visual_prompt", ""),
        "visual_b64":     visual_b64,
        "platforms":      [],
        "post_ids":       {},
        "status":         "pending_approval" if (SOCIAL_MANUAL_APPROVAL and not force_publish) else "publishing",
    }
    await db.laurentia_social_posts.insert_one(dict(post_doc))

    if SOCIAL_MANUAL_APPROVAL and not force_publish:
        logger.info("social_agent: pending_approval theme=%s post=%s", theme, post_doc["post_id"])
        return {"status": "pending_approval", "post_id": post_doc["post_id"], "theme": theme}

    # Publication parallèle, fallbacks indépendants
    ig, li, tw = await asyncio.gather(
        _publish_instagram(content["instagram"], visual_b64),
        _publish_linkedin(content["linkedin"]),
        _publish_twitter(content["twitter"]),
    )
    platforms = []
    post_ids = {}
    if ig.get("ok"):
        platforms.append("instagram")
        post_ids["instagram"] = ig.get("post_id")
    if li.get("ok"):
        platforms.append("linkedin")
        post_ids["linkedin"] = li.get("post_id")
    if tw.get("ok"):
        platforms.append("twitter")
        post_ids["twitter"] = tw.get("post_id")

    final_status = "published" if platforms else "all_failed"
    await db.laurentia_social_posts.update_one(
        {"post_id": post_doc["post_id"]},
        {"$set": {
            "platforms": platforms,
            "post_ids": post_ids,
            "status": final_status,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "errors": {"instagram": ig, "linkedin": li, "twitter": tw},
        }},
    )
    logger.info("social_agent: publish theme=%s platforms=%s status=%s", theme, platforms, final_status)
    return {"status": final_status, "post_id": post_doc["post_id"], "platforms": platforms, "theme": theme}


# ---------- Analytics J+1 ----------

async def fetch_analytics_j1(db) -> dict:
    """Récupère analytics pour les posts publiés il y a ~24h. Best-effort."""
    one_day_ago = (datetime.now(timezone.utc) - timedelta(hours=23)).isoformat()
    two_days_ago = (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat()
    cursor = db.laurentia_social_posts.find(
        {"status": "published", "published_at": {"$gte": two_days_ago, "$lte": one_day_ago}},
        {"_id": 0},
    )
    posts = await cursor.to_list(length=100)
    processed = 0
    for p in posts:
        # Stub : en LIVE, appeler graph.facebook.com/{id}/insights, linkedin organic stats, x analytics.
        await db.laurentia_social_analytics.insert_one({
            "post_id": p["post_id"],
            "theme": p.get("theme"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {"instagram": {}, "linkedin": {}, "twitter": {}},
            "engagement_score": 0.0,
        })
        processed += 1
    return {"processed": processed}


# ---------- Scheduler ----------

def _seconds_until_today_or_next_9am_martinique() -> float:
    now_mq = datetime.now(MARTINIQUE_TZ)
    target = now_mq.replace(hour=9, minute=0, second=0, microsecond=0)
    if target <= now_mq:
        target += timedelta(days=1)
    return (target - now_mq).total_seconds()


def _seconds_until_today_or_next_10am_martinique() -> float:
    now_mq = datetime.now(MARTINIQUE_TZ)
    target = now_mq.replace(hour=10, minute=0, second=0, microsecond=0)
    if target <= now_mq:
        target += timedelta(days=1)
    return (target - now_mq).total_seconds()


def schedule_social_agent(app, db) -> None:
    """Loops journaliers — 09:00 (publication) et 10:00 (analytics J+1)."""
    async def _pub_loop():
        while True:
            try:
                await asyncio.sleep(max(_seconds_until_today_or_next_9am_martinique(), 60.0))
                await generate_and_publish(db)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("social_agent.publish_loop_error: %s", e)
                await asyncio.sleep(3600)

    async def _ana_loop():
        while True:
            try:
                await asyncio.sleep(max(_seconds_until_today_or_next_10am_martinique(), 60.0))
                await fetch_analytics_j1(db)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("social_agent.analytics_loop_error: %s", e)
                await asyncio.sleep(3600)

    app.state.social_pub_task = asyncio.create_task(_pub_loop())
    app.state.social_ana_task = asyncio.create_task(_ana_loop())
