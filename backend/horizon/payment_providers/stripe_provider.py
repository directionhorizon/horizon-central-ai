"""Adaptateur Stripe (PaymentIntent, Checkout hébergé, SetupIntent via Checkout)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Mapping

import httpx

from .base import (
    MODE_CHECKOUT,
    MODE_INTENT,
    MODE_SETUP,
    PaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderError,
)

API_BASE = "https://api.stripe.com/v1"


def _public_url(path: str = "/payments") -> str:
    base = (os.getenv("HORIZON_PUBLIC_URL") or "https://horizon.mayela-crm.com").rstrip("/")
    return f"{base}{path}"


class StripeProvider(PaymentProvider):
    kind = "stripe"
    label = "Stripe"
    capabilities = (MODE_INTENT, MODE_CHECKOUT, MODE_SETUP, "refund")
    env_vars = ("HORIZON_STRIPE_SECRET_KEY",)
    docs_url = "https://docs.stripe.com/api"

    async def create(
        self,
        request: PaymentRequest,
        credentials: Mapping[str, str],
        mode: str = MODE_INTENT,
    ) -> PaymentResult:
        key = str(credentials.get("HORIZON_STRIPE_SECRET_KEY") or "").strip()
        if not key:
            raise ProviderError("Stripe n'est pas configuré : clé absente (HORIZON_STRIPE_SECRET_KEY).")
        if mode not in self.capabilities:
            raise ProviderError(f"Stripe ne gère pas le mode « {mode} ».")
        async with httpx.AsyncClient(timeout=20.0) as client:
            if mode == MODE_INTENT:
                payload = await self._intent(client, key, request)
            else:
                payload = await self._checkout(client, key, request, mode)
        return self._normalize(payload, request, mode)

    async def _intent(
        self, client: httpx.AsyncClient, key: str, request: PaymentRequest
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "amount": int(request.amount),
            "currency": request.currency.lower(),
            "automatic_payment_methods[enabled]": "true",
        }
        if request.detail:
            data["description"] = request.detail[:500]
        if request.customer_email:
            data["receipt_email"] = request.customer_email
        if request.customer:
            data["customer"] = request.customer
        headers: dict[str, str] = {}
        if request.idempotency_key:
            headers["Idempotency-Key"] = request.idempotency_key
        response = await client.post(
            f"{API_BASE}/payment_intents", auth=(key, ""), data=data, headers=headers
        )
        return self._read(response, "PaymentIntent")

    async def _checkout(
        self,
        client: httpx.AsyncClient,
        key: str,
        request: PaymentRequest,
        mode: str,
    ) -> dict[str, Any]:
        success_url = request.success_url or _public_url("/payments?status=success")
        cancel_url = request.cancel_url or _public_url("/payments?status=cancelled")
        data: dict[str, Any] = {
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        if mode == MODE_SETUP:
            data["mode"] = "setup"
        else:
            data["mode"] = "payment"
            data["line_items[0][quantity]"] = "1"
            data["line_items[0][price_data][currency]"] = request.currency.lower()
            data["line_items[0][price_data][unit_amount]"] = str(int(request.amount))
            data["line_items[0][price_data][product_data][name]"] = (
                request.detail or "Paiement HORIZON"
            )[:250]
        if request.customer_email:
            data["customer_email"] = request.customer_email
        if request.customer:
            data["customer"] = request.customer
        headers: dict[str, str] = {}
        if request.idempotency_key:
            headers["Idempotency-Key"] = request.idempotency_key
        response = await client.post(
            f"{API_BASE}/checkout/sessions", auth=(key, ""), data=data, headers=headers
        )
        return self._read(response, "Checkout Session")

    @staticmethod
    def _read(response: httpx.Response, label: str) -> dict[str, Any]:
        if response.status_code >= 400:
            message = ""
            try:
                message = str((response.json().get("error") or {}).get("message") or "")
            except Exception:
                message = ""
            suffix = f" : {message[:200]}" if message else ""
            raise ProviderError(
                f"Stripe a refusé la demande ({label}, HTTP {response.status_code}){suffix}"
            )
        try:
            return response.json()
        except Exception as error:  # pragma: no cover - réponse illisible
            raise ProviderError(f"Réponse Stripe illisible ({label}).") from error

    async def refund(
        self,
        payment_id: str,
        amount: int,
        credentials: Mapping[str, str],
        reason: str = "",
    ) -> PaymentResult:
        key = str(credentials.get("HORIZON_STRIPE_SECRET_KEY") or "").strip()
        if not key:
            raise ProviderError(
                "Stripe n'est pas configuré : clé absente (HORIZON_STRIPE_SECRET_KEY)."
            )
        async with httpx.AsyncClient(timeout=20.0) as client:
            intent_id = payment_id
            if payment_id.startswith("cs_"):
                session = await client.get(
                    f"{API_BASE}/checkout/sessions/{payment_id}", auth=(key, "")
                )
                session_payload = self._read(session, "Checkout Session")
                intent_id = str(session_payload.get("payment_intent") or "")
                if not intent_id:
                    raise ProviderError(
                        "Session Stripe sans PaymentIntent : remboursement impossible."
                    )
            data: dict[str, Any] = {"payment_intent": intent_id}
            if amount:
                data["amount"] = int(amount)
            if reason:
                data["reason"] = "requested_by_customer"
            response = await client.post(
                f"{API_BASE}/refunds", auth=(key, ""), data=data
            )
        payload = self._read(response, "Refund")
        return PaymentResult(
            provider=self.kind,
            id=str(payload.get("id") or ""),
            status=str(payload.get("status") or "pending"),
            amount=int(payload.get("amount") or amount or 0),
            currency=str(payload.get("currency") or "eur").lower(),
            mode="refund",
            detail=reason,
            raw=payload,
        )

    def verify_webhook(
        self, payload: bytes, headers: Mapping[str, str]
    ) -> dict[str, Any]:
        secret = (os.getenv("HORIZON_STRIPE_WEBHOOK_SECRET") or "").strip()
        if not secret:
            raise ProviderError(
                "Webhook Stripe non configuré (HORIZON_STRIPE_WEBHOOK_SECRET)."
            )
        signature = ""
        for name, value in headers.items():
            if str(name).lower() == "stripe-signature":
                signature = str(value)
                break
        if not signature:
            raise ProviderError("En-tête Stripe-Signature absent.")
        parts: dict[str, str] = {}
        for chunk in signature.split(","):
            if "=" in chunk:
                name, value = chunk.split("=", 1)
                parts[name.strip()] = value.strip()
        timestamp = parts.get("t", "")
        expected = parts.get("v1", "")
        if not timestamp or not expected:
            raise ProviderError("Signature Stripe incomplète.")
        try:
            age = abs(time.time() - int(timestamp))
        except ValueError as error:
            raise ProviderError("Horodatage de signature invalide.") from error
        if age > 300:
            raise ProviderError("Signature Stripe expirée (horodatage trop ancien).")
        signed = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
        computed = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, expected):
            raise ProviderError("Signature Stripe invalide.")
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as error:
            raise ProviderError("Charge utile Stripe illisible.") from error
        if not isinstance(event, dict):
            raise ProviderError("Charge utile Stripe inattendue.")
        return event

    def webhook_event(self, event: Mapping[str, Any]) -> tuple[str, str] | None:
        kind = str(event.get("type") or "")
        mapping = {
            "payment_intent.succeeded": "succeeded",
            "payment_intent.processing": "processing",
            "payment_intent.requires_action": "requires_action",
            "payment_intent.canceled": "canceled",
            "payment_intent.payment_failed": "failed",
            "checkout.session.completed": "succeeded",
            "checkout.session.expired": "canceled",
        }
        status = mapping.get(kind)
        if not status:
            return None
        data = event.get("data") or {}
        obj = data.get("object") or {}
        identifier = str(obj.get("id") or "")
        if not identifier:
            return None
        return identifier, status

    def _normalize(
        self, payload: dict[str, Any], request: PaymentRequest, mode: str
    ) -> PaymentResult:
        return PaymentResult(
            provider=self.kind,
            id=str(payload.get("id") or ""),
            status=str(payload.get("status") or "created"),
            amount=int(payload.get("amount_total") or payload.get("amount") or request.amount),
            currency=str(payload.get("currency") or request.currency).lower(),
            mode=mode,
            detail=request.detail,
            checkout_url=str(payload.get("url") or ""),
            raw=payload,
        )
