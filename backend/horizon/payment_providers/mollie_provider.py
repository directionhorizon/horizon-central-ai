"""Adaptateur Mollie (paiements, redirection vers la page Mollie)."""
from __future__ import annotations

import os
from typing import Any, Mapping

import httpx

from .base import (
    MODE_CHECKOUT,
    PaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderError,
    fallback_detail,
)

API_BASE = "https://api.mollie.com/v2"


def _public_url(path: str = "/payments") -> str:
    base = (os.getenv("HORIZON_PUBLIC_URL") or "https://horizon.mayela-crm.com").rstrip("/")
    return f"{base}{path}"


class MollieProvider(PaymentProvider):
    kind = "mollie"
    label = "Mollie"
    capabilities = (MODE_CHECKOUT,)
    env_vars = ("HORIZON_MOLLIE_API_KEY",)
    docs_url = "https://docs.mollie.com/reference/create-payment"

    async def create(
        self,
        request: PaymentRequest,
        credentials: Mapping[str, str],
        mode: str = MODE_CHECKOUT,
    ) -> PaymentResult:
        key = str(credentials.get("HORIZON_MOLLIE_API_KEY") or "").strip()
        if not key:
            raise ProviderError("Mollie n'est pas configuré : clé absente (HORIZON_MOLLIE_API_KEY).")
        if mode not in self.capabilities:
            raise ProviderError(
                "Mollie gère uniquement le mode « checkout » (page de paiement hébergée)."
            )
        body: dict[str, Any] = {
            "amount": {
                "currency": request.currency.upper(),
                "value": request.decimal_amount(),
            },
            "description": (request.detail or "Paiement HORIZON")[:255],
            "redirectUrl": request.success_url or _public_url("/payments?status=success"),
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{API_BASE}/payments",
                headers={"Authorization": f"Bearer {key}"},
                json=body,
            )
        if response.status_code >= 400:
            message = ""
            try:
                message = str((response.json().get("detail") or ""))
            except Exception:
                message = ""
            suffix = f" : {message[:200]}" if message else ""
            raise ProviderError(
                f"Mollie a refusé la demande (HTTP {response.status_code}){suffix}"
            )
        payload = response.json()
        links = payload.get("_links") or {}
        checkout_url = str((links.get("checkout") or {}).get("href") or "")
        identifier = str(payload.get("id") or "")
        amount = int(request.amount)
        currency = request.currency.lower()
        return PaymentResult(
            provider=self.kind,
            id=identifier,
            status=str(payload.get("status") or "open"),
            amount=amount,
            currency=currency,
            mode=MODE_CHECKOUT,
            detail=request.detail
            or fallback_detail(self.label, amount, currency, identifier),
            checkout_url=checkout_url,
            raw=payload,
        )
