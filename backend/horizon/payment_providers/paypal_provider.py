"""Adaptateur PayPal (Commandes v2, redirection vers la page PayPal)."""
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
)


def _api_base() -> str:
    return (os.getenv("HORIZON_PAYPAL_API_BASE") or "https://api-m.sandbox.paypal.com").rstrip("/")


def _public_url(path: str = "/payments") -> str:
    base = (os.getenv("HORIZON_PUBLIC_URL") or "https://horizon.mayela-crm.com").rstrip("/")
    return f"{base}{path}"


class PayPalProvider(PaymentProvider):
    kind = "paypal"
    label = "PayPal"
    capabilities = (MODE_CHECKOUT,)
    env_vars = ("HORIZON_PAYPAL_CLIENT_ID", "HORIZON_PAYPAL_CLIENT_SECRET")
    docs_url = "https://developer.paypal.com/docs/api/orders/v2/"

    async def create(
        self,
        request: PaymentRequest,
        credentials: Mapping[str, str],
        mode: str = MODE_CHECKOUT,
    ) -> PaymentResult:
        client_id = str(credentials.get("HORIZON_PAYPAL_CLIENT_ID") or "").strip()
        secret = str(credentials.get("HORIZON_PAYPAL_CLIENT_SECRET") or "").strip()
        if not client_id or not secret:
            raise ProviderError(
                "PayPal n'est pas configuré : identifiants absents (HORIZON_PAYPAL_CLIENT_ID / "
                "HORIZON_PAYPAL_CLIENT_SECRET)."
            )
        if mode not in self.capabilities:
            raise ProviderError(
                "PayPal gère uniquement le mode « checkout » (page de paiement hébergée)."
            )
        base = _api_base()
        async with httpx.AsyncClient(timeout=20.0) as client:
            token = await self._token(client, base, client_id, secret)
            order = await self._order(client, base, token, request)
        return self._normalize(order, request)

    @staticmethod
    async def _token(
        client: httpx.AsyncClient, base: str, client_id: str, secret: str
    ) -> str:
        response = await client.post(
            f"{base}/v1/oauth2/token",
            auth=(client_id, secret),
            data={"grant_type": "client_credentials"},
        )
        if response.status_code >= 400:
            raise ProviderError(
                f"PayPal a refusé l'authentification (HTTP {response.status_code})."
            )
        token = str(response.json().get("access_token") or "").strip()
        if not token:
            raise ProviderError("PayPal n'a pas renvoyé de jeton d'accès.")
        return token

    @staticmethod
    async def _order(
        client: httpx.AsyncClient, base: str, token: str, request: PaymentRequest
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": request.currency.upper(),
                        "value": request.decimal_amount(),
                    },
                    "description": (request.detail or "Paiement HORIZON")[:127],
                }
            ],
            "application_context": {
                "return_url": request.success_url or _public_url("/payments?status=success"),
                "cancel_url": request.cancel_url or _public_url("/payments?status=cancelled"),
                "user_action": "PAY_NOW",
            },
        }
        response = await client.post(
            f"{base}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        if response.status_code >= 400:
            message = ""
            try:
                message = str((response.json().get("message") or ""))
            except Exception:
                message = ""
            suffix = f" : {message[:200]}" if message else ""
            raise ProviderError(
                f"PayPal a refusé la commande (HTTP {response.status_code}){suffix}"
            )
        return response.json()

    def _normalize(self, order: dict[str, Any], request: PaymentRequest) -> PaymentResult:
        checkout_url = ""
        for link in order.get("links") or []:
            if str(link.get("rel")) in {"payer-action", "approve"}:
                checkout_url = str(link.get("href") or "")
                break
        return PaymentResult(
            provider=self.kind,
            id=str(order.get("id") or ""),
            status=str(order.get("status") or "CREATED"),
            amount=int(request.amount),
            currency=request.currency.lower(),
            mode=MODE_CHECKOUT,
            detail=request.detail,
            checkout_url=checkout_url,
            raw=order,
        )
