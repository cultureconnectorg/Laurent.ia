"""Regression tests for the official Stripe integration and payment authorization."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from routes import billing  # noqa: E402


def request_for(db=None, origin="https://app.example.com", signature=None):
    headers = {}
    if origin:
        headers["origin"] = origin
    if signature:
        headers["Stripe-Signature"] = signature
    async def body():
        return b'{"type":"checkout.session.completed"}'
    return SimpleNamespace(
        headers=headers,
        app=SimpleNamespace(state=SimpleNamespace(db=db)),
        body=body,
    )


def test_payment_status_requires_authentication(monkeypatch):
    async def no_user(_request):
        return None
    monkeypatch.setattr(billing, "get_current_user", no_user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(billing.get_status("cs_test_secret", request_for()))
    assert exc.value.status_code == 401


def test_payment_status_cannot_be_read_by_another_user(monkeypatch):
    class Transactions:
        async def find_one(self, *_args, **_kwargs):
            return {"session_id": "cs_test", "user_id": "user-alice", "frek_id": "FREK-ALICE"}
    db = SimpleNamespace(payment_transactions=Transactions())
    async def bob(_request):
        return {"user_id": "user-bob", "frek_id": "FREK-BOB"}
    monkeypatch.setattr(billing, "get_current_user", bob)
    monkeypatch.setattr(
        billing.stripe.checkout.Session,
        "retrieve",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Stripe must not be called")),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(billing.get_status("cs_test", request_for(db)))
    assert exc.value.status_code == 403


def test_checkout_rejects_unconfigured_redirect_origin(monkeypatch):
    monkeypatch.setattr(billing, "STRIPE_API_KEY", "sk_test_unit")
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    async def alice(_request):
        return {"user_id": "user-alice", "frek_id": "FREK-ALICE"}
    monkeypatch.setattr(billing, "get_current_user", alice)

    payload = billing.CheckoutRequest(origin_url="https://attacker.example", package_id="creator_monthly")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(billing.create_checkout(payload, request_for(origin="https://attacker.example")))
    assert exc.value.status_code == 400


def test_checkout_uses_server_side_price_and_subscription_metadata(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setattr(billing, "STRIPE_API_KEY", "sk_test_unit")
    async def alice(_request):
        return {"user_id": "user-alice", "frek_id": "FREK-ALICE"}
    monkeypatch.setattr(billing, "get_current_user", alice)

    captured = {}
    def create_session(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_test_123", url="https://checkout.stripe.test/session")
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create_session)

    class Transactions:
        async def insert_one(self, doc):
            self.doc = doc
    transactions = Transactions()
    db = SimpleNamespace(payment_transactions=transactions)
    result = asyncio.run(
        billing.create_checkout(
            billing.CheckoutRequest(origin_url="https://app.example.com", package_id="creator_monthly"),
            request_for(db),
        )
    )

    assert result["session_id"] == "cs_test_123"
    assert captured["mode"] == "subscription"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 1500
    assert captured["metadata"]["frek_id"] == "FREK-ALICE"
    assert captured["subscription_data"]["metadata"]["package_id"] == "creator_monthly"
    assert transactions.doc["amount"] == 15.0


def test_webhook_fails_closed_when_signing_secret_is_missing(monkeypatch):
    monkeypatch.setattr(billing, "STRIPE_WEBHOOK_SECRET", "")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(billing.stripe_webhook(request_for(signature="t=1,v1=invalid")))
    assert exc.value.status_code == 503
