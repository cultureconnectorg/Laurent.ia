"""Official Stripe SDK adapter preserving Laurent.ia's previous checkout interface.

No Emergent SDK dependency. Checkout uses monthly subscriptions because the
published packages are explicitly monthly plans. Webhooks fail closed unless
a signing secret is configured.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import stripe


@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: dict[str, str]


class StripeCheckout:
    def __init__(self, api_key: str, webhook_secret: str | None = None, webhook_url: str | None = None):
        self.api_key = (api_key or "").strip()
        self.webhook_secret = (webhook_secret or "").strip()
        self.webhook_url = webhook_url
        if self.api_key:
            stripe.api_key = self.api_key

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("STRIPE_API_KEY is not configured.")

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> Any:
        self._require_api_key()
        metadata = {str(k): str(v) for k, v in req.metadata.items()}
        amount_cents = int(round(float(req.amount) * 100))
        session = await stripe.checkout.Session.create_async(
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": req.currency.lower(),
                    "unit_amount": amount_cents,
                    "recurring": {"interval": "month"},
                    "product_data": {"name": "Laurent.ia subscription"},
                },
                "quantity": 1,
            }],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            metadata=metadata,
            subscription_data={"metadata": metadata},
        )
        return SimpleNamespace(session_id=session.id, url=session.url)

    async def get_checkout_status(self, session_id: str) -> Any:
        self._require_api_key()
        session = await stripe.checkout.Session.retrieve_async(session_id)
        return SimpleNamespace(
            session_id=session.id,
            status=session.status,
            payment_status=session.payment_status,
            amount_total=session.amount_total,
            currency=session.currency,
        )

    async def handle_webhook(self, body: bytes, signature: str | None) -> Any:
        if not self.webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured; refusing unsigned webhook.")
        if not signature:
            raise ValueError("Missing Stripe-Signature header.")
        event = stripe.Webhook.construct_event(body, signature, self.webhook_secret)
        event_type = event["type"]
        obj = event["data"]["object"]
        # For checkout completion, the ID is the Checkout Session ID. For a
        # subscription event, it is the Subscription ID; handlers use metadata.
        session_id = obj.get("id") if event_type.startswith("checkout.session.") else None
        payment_status = obj.get("payment_status")
        if event_type == "payment_intent.succeeded":
            payment_status = "paid"
        metadata = obj.get("metadata") or {}
        return SimpleNamespace(
            event_id=event["id"],
            event_type=event_type,
            session_id=session_id,
            payment_status=payment_status,
            metadata=dict(metadata),
        )
