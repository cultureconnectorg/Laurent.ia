"""
billing.py — Stripe Checkout pour Laurent.ia Pro €15/mois.

Endpoints:
- POST /api/billing/create-checkout   body { origin_url, package_id="pro_monthly" }
- GET  /api/billing/status/{session_id}                                   (polling)
- POST /api/webhook/stripe                                                (Stripe webhook)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

from routes.auth import get_current_user


router = APIRouter(prefix="/api/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/api/webhook", tags=["webhook"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")

# Server-side packages — JAMAIS confiance au frontend pour le prix
PACKAGES = {
    "creator_monthly": {
        "amount": 15.00,
        "currency": "eur",
        "tier": "creator",
        "label": "Creator",
        "tagline": "Pour les créateurs, étudiants et entrepreneurs",
        "tokens_limit_month": 2_000_000,
        "tokens_limit_day": 200_000,
        "memory_window": 100,
        "rate_per_min": 30,
        "features": [
            "Conversations longues",
            "Mémoire étendue · 100 échanges",
            "Upload de fichiers",
            "Historique complet",
            "Génération avancée",
        ],
    },
    "infinite_monthly": {
        "amount": 39.00,
        "currency": "eur",
        "tier": "infinite",
        "label": "Infinite",
        "tagline": "Le cerveau augmenté · usage prioritaire",
        "tokens_limit_month": 10_000_000,
        "tokens_limit_day": 1_000_000,
        "memory_window": 500,
        "rate_per_min": 90,
        "features": [
            "Mémoire persistante illimitée",
            "Agents IA & automatisations",
            "Vitesse prioritaire",
            "Multi-modèles (à venir)",
            "Accès aux fonctionnalités expérimentales",
        ],
    },
}

FREE_TIER = {
    "tier": "free",
    "label": "Free",
    "tokens_limit_month": 100_000,
    "tokens_limit_day": 15_000,
    "memory_window": 10,
    "rate_per_min": 10,
    "features": [
        "Découverte de Laurent.ia",
        "Mémoire courte · 10 échanges",
        "Quota quotidien de messages",
        "Accès standard",
    ],
}


class CheckoutRequest(BaseModel):
    origin_url: str
    package_id: str = "creator_monthly"


def _checkout_client(host_url: str) -> StripeCheckout:
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url.rstrip('/')}/api/webhook/stripe")


@router.post("/create-checkout")
async def create_checkout(payload: CheckoutRequest, request: Request):
    pkg = PACKAGES.get(payload.package_id)
    if not pkg:
        raise HTTPException(400, "Package inconnu")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Connexion requise pour activer Pro")

    db = request.app.state.db
    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/?upgrade=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/?upgrade=cancel"

    stripe = _checkout_client(str(request.base_url))
    req = CheckoutSessionRequest(
        amount=pkg["amount"],
        currency=pkg["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["user_id"],
            "frek_id": user["frek_id"],
            "package_id": payload.package_id,
        },
    )
    session = await stripe.create_checkout_session(req)

    # Crée l'entrée transactions AVANT redirection
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
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

    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def get_status(session_id: str, request: Request):
    db = request.app.state.db
    stripe = _checkout_client(str(request.base_url))
    status = await stripe.get_checkout_status(session_id)

    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "Transaction inconnue")

    # Update transaction
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {
            "payment_status": status.payment_status,
            "status": status.status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    # Si payé ET pas encore crédité → activer le tier acheté (idempotent)
    if status.payment_status == "paid" and not tx.get("credit_applied"):
        await db.payment_transactions.update_one(
            {"session_id": session_id, "credit_applied": {"$ne": True}},
            {"$set": {"credit_applied": True}},
        )
        tx2 = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if tx2 and tx2.get("credit_applied"):
            pkg = PACKAGES.get(tx.get("package_id", "creator_monthly"), PACKAGES["creator_monthly"])
            await db.laurentia_instances.update_one(
                {"frek_id": tx["frek_id"]},
                {"$set": {
                    "version": pkg["tier"],
                    "tier": pkg["tier"],
                    "tokens_limit_month": pkg["tokens_limit_month"],
                    "tokens_limit_day": pkg["tokens_limit_day"],
                    "memory_window": pkg["memory_window"],
                    "rate_per_min": pkg["rate_per_min"],
                    "tier_activated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

    return {
        "session_id": session_id,
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
    }


@webhook_router.post("/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    stripe_client = _checkout_client(str(request.base_url))
    try:
        evt = await stripe_client.handle_webhook(body, sig)
    except Exception as e:
        raise HTTPException(400, f"Webhook invalide: {e}")

    db = request.app.state.db

    # 1. Activation idempotente via checkout.session.completed / payment_intent.succeeded
    if evt.event_type in ("checkout.session.completed", "payment_intent.succeeded"):
        await db.payment_transactions.update_one(
            {"session_id": evt.session_id},
            {"$set": {
                "payment_status": evt.payment_status,
                "webhook_event_id": evt.event_id,
                "webhook_received_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        tx = await db.payment_transactions.find_one({"session_id": evt.session_id}, {"_id": 0})
        if tx and evt.payment_status == "paid" and not tx.get("credit_applied"):
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id, "credit_applied": {"$ne": True}},
                {"$set": {"credit_applied": True}},
            )
            pkg = PACKAGES.get(tx.get("package_id", "creator_monthly"), PACKAGES["creator_monthly"])
            await db.laurentia_instances.update_one(
                {"frek_id": tx["frek_id"]},
                {"$set": {
                    "version": pkg["tier"],
                    "tier": pkg["tier"],
                    "tokens_limit_month": pkg["tokens_limit_month"],
                    "tokens_limit_day": pkg["tokens_limit_day"],
                    "memory_window": pkg["memory_window"],
                    "rate_per_min": pkg["rate_per_min"],
                    "tier_activated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

    # 2. Désactivation sur customer.subscription.deleted
    #    (l'event natif Stripe contient metadata.frek_id passé au checkout)
    if evt.event_type == "customer.subscription.deleted":
        metadata = getattr(evt, "metadata", None) or {}
        frek_id = metadata.get("frek_id") if isinstance(metadata, dict) else None
        if frek_id:
            await db.laurentia_instances.update_one(
                {"frek_id": frek_id},
                {"$set": {
                    "version": "free",
                    "tier": "free",
                    "tokens_limit_month": 100_000,
                    "tokens_limit_day": 15_000,
                    "memory_window": 10,
                    "rate_per_min": 10,
                    "tier_downgraded_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

    return {"ok": True}


@router.get("/packages")
async def list_packages():
    """Renvoie la liste des plans achetables (pricing modal frontend)."""
    return {
        "free": {**FREE_TIER, "amount": 0.00, "package_id": None},
        "available": [{"package_id": pid, **pkg} for pid, pkg in PACKAGES.items()],
    }
