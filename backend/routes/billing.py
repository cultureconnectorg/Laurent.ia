"""
billing.py — Stripe Checkout natif via le SDK officiel Stripe.

Les prix sont exclusivement définis côté serveur. Les sessions de paiement
sont liées à l'utilisateur authentifié et les webhooks exigent une signature
Stripe valide. Aucun wrapper Emergent n'est utilisé.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from routes.auth import get_current_user


router = APIRouter(prefix="/api/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/api/webhook", tags=["webhook"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

PACKAGES = {
    "creator_monthly": {
        "amount": 15.00, "currency": "eur", "tier": "creator", "label": "Creator",
        "tagline": "Pour les créateurs, étudiants et entrepreneurs",
        "tokens_limit_month": 2_000_000, "tokens_limit_day": 200_000,
        "memory_window": 100, "rate_per_min": 30,
        "features": ["Conversations longues", "Mémoire étendue · 100 échanges", "Upload de fichiers", "Historique complet", "Génération avancée"],
    },
    "infinite_monthly": {
        "amount": 39.00, "currency": "eur", "tier": "infinite", "label": "Infinite",
        "tagline": "Le cerveau augmenté · usage prioritaire",
        "tokens_limit_month": 10_000_000, "tokens_limit_day": 1_000_000,
        "memory_window": 500, "rate_per_min": 90,
        "features": ["Mémoire persistante illimitée", "Agents IA & automatisations", "Vitesse prioritaire", "Multi-modèles (à venir)", "Accès aux fonctionnalités expérimentales"],
    },
}

FREE_TIER = {
    "tier": "free", "label": "Free", "tokens_limit_month": 100_000,
    "tokens_limit_day": 15_000, "memory_window": 10, "rate_per_min": 10,
    "features": ["Découverte de Laurent.ia", "Mémoire courte · 10 échanges", "Quota quotidien de messages", "Accès standard"],
}


class CheckoutRequest(BaseModel):
    origin_url: str
    package_id: str = "creator_monthly"


def _field(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    getter = getattr(obj, "get", None)
    if callable(getter):
        return getter(name, default)
    return getattr(obj, name, default)


def _require_stripe_api_key() -> str:
    key = STRIPE_API_KEY or os.environ.get("STRIPE_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Paiement indisponible : STRIPE_API_KEY non configurée")
    return key


def _require_webhook_secret() -> str:
    secret = STRIPE_WEBHOOK_SECRET or os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "Webhook indisponible : STRIPE_WEBHOOK_SECRET non configuré")
    return secret


def _validated_origin(payload_origin: str, request: Request) -> str:
    """Reject caller-supplied checkout redirect origins not configured for this app."""
    origin = payload_origin.strip().rstrip("/")
    parsed = urlparse(origin)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password:
        raise HTTPException(400, "origin_url invalide")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise HTTPException(400, "origin_url doit utiliser HTTPS")

    allowed = {
        value.strip().rstrip("/")
        for value in (
            os.environ.get("FRONTEND_URL", ""),
            os.environ.get("CORS_ORIGINS", ""),
        )
        for value in value.split(",")
        if value.strip() and value.strip() != "*"
    }
    request_origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if request_origin:
        allowed.add(request_origin)
    if origin not in allowed:
        raise HTTPException(400, "origin_url non autorisée")
    return origin


async def _activate_paid_tier_once(db, session_id: str, tx: dict) -> bool:
    """Atomically claim a paid transaction so concurrent polls/webhooks cannot double-apply it."""
    claim = await db.payment_transactions.update_one(
        {"session_id": session_id, "credit_applied": {"$ne": True}},
        {"$set": {"credit_applied": True, "tier_applied_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not getattr(claim, "modified_count", 0):
        return False

    pkg = PACKAGES.get(tx.get("package_id"))
    if not pkg:
        # Unknown package must never grant a tier; revert the claim for investigation.
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"credit_applied": False, "tier_apply_error": "unknown_package"}},
        )
        return False

    await db.laurentia_instances.update_one(
        {"frek_id": tx["frek_id"]},
        {"$set": {
            "version": pkg["tier"], "tier": pkg["tier"],
            "tokens_limit_month": pkg["tokens_limit_month"],
            "tokens_limit_day": pkg["tokens_limit_day"],
            "memory_window": pkg["memory_window"], "rate_per_min": pkg["rate_per_min"],
            "tier_activated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return True


@router.post("/create-checkout")
async def create_checkout(payload: CheckoutRequest, request: Request):
    pkg = PACKAGES.get(payload.package_id)
    if not pkg:
        raise HTTPException(400, "Package inconnu")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Connexion requise pour activer Pro")

    api_key = _require_stripe_api_key()
    origin = _validated_origin(payload.origin_url, request)
    success_url = f"{origin}/?upgrade=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/?upgrade=cancel"
    metadata = {
        "user_id": str(user["user_id"]),
        "frek_id": str(user["frek_id"]),
        "package_id": payload.package_id,
    }

    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            api_key=api_key,
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": pkg["currency"],
                    "unit_amount": int(round(pkg["amount"] * 100)),
                    "recurring": {"interval": "month"},
                    "product_data": {"name": pkg["label"], "description": pkg["tagline"]},
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            subscription_data={"metadata": metadata},
        )
    except Exception as exc:
        # Do not expose Stripe internals, API keys, or provider response bodies.
        raise HTTPException(502, "Création de session de paiement impossible") from exc

    session_id = _field(session, "id")
    session_url = _field(session, "url")
    if not session_id or not session_url:
        raise HTTPException(502, "Réponse Stripe invalide")

    await request.app.state.db.payment_transactions.insert_one({
        "session_id": session_id,
        "user_id": user["user_id"],
        "frek_id": user["frek_id"],
        "package_id": payload.package_id,
        "amount": pkg["amount"],
        "currency": pkg["currency"],
        "payment_status": "pending",
        "status": "open",
        "credit_applied": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session_url, "session_id": session_id}


@router.get("/status/{session_id}")
async def get_status(session_id: str, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Connexion requise")

    db = request.app.state.db
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "Transaction inconnue")
    if tx.get("user_id") != user.get("user_id"):
        raise HTTPException(403, "Accès refusé à cette transaction")

    try:
        status = await asyncio.to_thread(
            stripe.checkout.Session.retrieve,
            session_id,
            api_key=_require_stripe_api_key(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Lecture du statut de paiement impossible") from exc

    payment_status = _field(status, "payment_status", "unpaid")
    session_status = _field(status, "status", "unknown")
    await db.payment_transactions.update_one(
        {"session_id": session_id, "user_id": user["user_id"]},
        {"$set": {
            "payment_status": payment_status,
            "status": session_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    if payment_status == "paid":
        await _activate_paid_tier_once(db, session_id, tx)

    cents = _field(status, "amount_total")
    return {
        "session_id": session_id,
        "status": session_status,
        "payment_status": payment_status,
        "amount_total": (cents / 100) if isinstance(cents, (int, float)) else None,
        "currency": _field(status, "currency"),
    }


@webhook_router.post("/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    if not signature:
        raise HTTPException(400, "Signature Stripe manquante")

    try:
        event = stripe.Webhook.construct_event(body, signature, _require_webhook_secret())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Signature ou événement Stripe invalide") from exc

    db = request.app.state.db
    event_type = _field(event, "type", "")
    event_id = _field(event, "id", "")
    data = _field(event, "data", {}) or {}
    obj = _field(data, "object", {}) or {}
    metadata = _field(obj, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        try:
            metadata = dict(metadata)
        except (TypeError, ValueError):
            metadata = {}

    if event_type == "checkout.session.completed":
        session_id = _field(obj, "id")
        if session_id:
            payment_status = _field(obj, "payment_status", "unpaid")
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "payment_status": payment_status,
                    "status": _field(obj, "status", "complete"),
                    "webhook_event_id": event_id,
                    "webhook_received_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
            if tx and payment_status == "paid":
                await _activate_paid_tier_once(db, session_id, tx)

    elif event_type == "customer.subscription.deleted":
        frek_id = metadata.get("frek_id")
        if frek_id:
            await db.laurentia_instances.update_one(
                {"frek_id": frek_id},
                {"$set": {
                    "version": "free", "tier": "free",
                    "tokens_limit_month": FREE_TIER["tokens_limit_month"],
                    "tokens_limit_day": FREE_TIER["tokens_limit_day"],
                    "memory_window": FREE_TIER["memory_window"],
                    "rate_per_min": FREE_TIER["rate_per_min"],
                    "tier_downgraded_at": datetime.now(timezone.utc).isoformat(),
                    "stripe_subscription_event_id": event_id,
                }},
            )

    return {"ok": True}


@router.get("/packages")
async def list_packages():
    """Renvoie les plans disponibles; les prix sont ceux définis côté serveur."""
    return {
        "free": {**FREE_TIER, "amount": 0.00, "package_id": None},
        "available": [{"package_id": package_id, **pkg} for package_id, pkg in PACKAGES.items()],
    }
