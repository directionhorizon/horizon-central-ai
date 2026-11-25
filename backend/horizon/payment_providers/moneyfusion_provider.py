"""Adaptateur MoneyFusion (Mobile Money + carte Visa, Congo / Afrique centrale).

MoneyFusion expose une page de paiement hébergée : HORIZON crée une session,
renvoie l'URL, et le client paie par Mobile Money (MTN, Airtel) ou carte Visa.
Aucune donnée bancaire ne transite par HORIZON.

Sécurité : le webhook MoneyFusion n'est pas signé (contrairement à Stripe).
Un événement n'est donc jamais cru sur parole : l'adaptateur rappelle l'API de
statut (`paiementNotif/{token}`) avant de mettre à jour le statut local, et
n'accepte que les statuts réellement constatés à la source.
"""
from __future__ import annotations

import json
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

#: Base de l'API de vérification de statut (documentation MoneyFusion).
STATUS_BASE = "https://pay.moneyfusion.net/paiementNotif"

#: Devises sans décimale : le montant est déjà exprimé en unité entière (FCFA).
ZERO_DECIMAL = {
    "xof",
    "xaf",
    "jpy",
    "krw",
    "clp",
    "gnf",
    "cdf",
    "rwf",
    "bif",
    "mga",
    "kmf",
}

#: Statuts MoneyFusion -> statuts locaux HORIZON.
STATUS_MAP = {
    "paid": "succeeded",
    "no paid": "pending",
    "not paid": "pending",
    "success": "succeeded",
    "pending": "processing",
    "failure": "failed",
    "failed": "failed",
    "cancelled": "canceled",
    "canceled": "canceled",
    "no paid": "canceled",
    "not paid": "canceled",
}


def _public_url(path: str = "/payments") -> str:
    base = (os.getenv("HORIZON_PUBLIC_URL") or "https://horizon.mayela-crm.com").rstrip("/")
    return f"{base}{path}"


def _major_amount(amount: int, currency: str) -> int:
    """Convertit le montant local vers l'unité attendue par MoneyFusion.

    Les devises sans décimale (XOF, XAF…) sont transmises telles quelles ; les
    autres sont converties depuis la plus petite unité (centimes).
    """
    code = str(currency or "").strip().lower()
    if code in ZERO_DECIMAL:
        return int(amount)
    return int(round(int(amount) / 100))


def _status_of(payload: Mapping[str, Any]) -> str:
    raw = str(payload.get("statut") or payload.get("status") or "").strip().lower()
    return STATUS_MAP.get(raw, "processing")


def _fetch_status(token: str) -> dict[str, Any] | None:
    """Vérifie un paiement à la source (le webhook non signé ne fait pas foi)."""
    try:
        response = httpx.get(f"{STATUS_BASE}/{token}", timeout=20.0)
    except httpx.HTTPError as error:
        raise ProviderError(
            f"Vérification MoneyFusion injoignable ({type(error).__name__})."
        ) from error
    if response.status_code >= 400:
        raise ProviderError(
            f"Vérification MoneyFusion refusée (HTTP {response.status_code})."
        )
    try:
        payload = response.json()
    except Exception as error:
        raise ProviderError("Réponse de vérification MoneyFusion illisible.") from error
    if not isinstance(payload, dict):
        return None
    return payload


class MoneyFusionProvider(PaymentProvider):
    kind = "moneyfusion"
    label = "MoneyFusion (Mobile Money / Visa)"
    capabilities = (MODE_CHECKOUT,)
    env_vars = ("HORIZON_MONEYFUSION_API_URL",)
    docs_url = "https://docs.moneyfusion.net/"

    async def create(
        self,
        request: PaymentRequest,
        credentials: Mapping[str, str],
        mode: str = MODE_CHECKOUT,
    ) -> PaymentResult:
        api_url = str(credentials.get("HORIZON_MONEYFUSION_API_URL") or "").strip()
        if not api_url:
            raise ProviderError(
                "MoneyFusion n'est pas configuré : URL d'API absente "
                "(HORIZON_MONEYFUSION_API_URL)."
            )
        if mode != MODE_CHECKOUT:
            raise ProviderError(
                "MoneyFusion ne gère que le mode « checkout » (page de paiement hébergée)."
            )
        amount = _major_amount(request.amount, request.currency)
        article = request.detail.strip() or "Paiement HORIZON"
        body: dict[str, Any] = {
            "totalPrice": amount,
            "article": [{article[:80]: amount}],
            "numeroSend": request.customer.strip() or "00000000",
            "nomclient": request.customer_name.strip() or "Client HORIZON",
            "return_url": request.success_url or _public_url("/payments?status=success"),
            "webhook_url": _public_url("/api/v1/payments/webhook/moneyfusion"),
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(api_url, json=body)
        payload = self._read(response)
        token = str(payload.get("token") or "").strip()
        url = str(payload.get("url") or "").strip()
        if not token or not url:
            raise ProviderError(
                "MoneyFusion n'a pas renvoyé de jeton ou d'URL de paiement."
            )
        return PaymentResult(
            provider=self.kind,
            id=token,
            status="pending",
            amount=int(request.amount),
            currency=str(request.currency or "xaf").lower(),
            mode=MODE_CHECKOUT,
            detail=request.detail
            or fallback_detail(
                self.label, int(request.amount), request.currency, token
            ),
            checkout_url=url,
            raw=payload,
        )

    def verify_webhook(
        self, payload: bytes, headers: Mapping[str, str]
    ) -> dict[str, Any]:
        api_url = (os.getenv("HORIZON_MONEYFUSION_API_URL") or "").strip()
        if not api_url:
            raise ProviderError(
                "Webhook MoneyFusion non configuré (HORIZON_MONEYFUSION_API_URL)."
            )
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as error:
            raise ProviderError("Charge utile MoneyFusion illisible.") from error
        if not isinstance(event, dict):
            raise ProviderError("Charge utile MoneyFusion inattendue.")
        token = str(event.get("tokenPay") or event.get("token") or "").strip()
        if not token:
            raise ProviderError("Jeton de paiement absent dans l'événement MoneyFusion.")
        verified = _fetch_status(token)
        if not verified:
            raise ProviderError(
                "Paiement MoneyFusion introuvable (vérification à la source)."
            )
        status = _status_of(verified)
        suffix = "completed" if status == "succeeded" else "pending"
        if status in {"canceled", "failed"}:
            suffix = "cancelled"
        return {
            "id": f"{token}:{status}",
            "type": f"payin.session.{suffix}",
            "tokenPay": token,
            "status": status,
            "raw": verified,
        }

    def webhook_event(self, event: Mapping[str, Any]) -> tuple[str, str] | None:
        token = str(event.get("tokenPay") or "").strip()
        status = str(event.get("status") or "").strip()
        if not token or not status:
            return None
        return token, status

    def _read(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except Exception as error:
            raise ProviderError(
                f"Réponse MoneyFusion illisible (HTTP {response.status_code})."
            ) from error
        if not isinstance(payload, dict):
            raise ProviderError("Réponse MoneyFusion inattendue.")
        ok: Any = payload.get("statut", payload.get("status", True))
        if isinstance(ok, str):
            ok = ok.strip().lower() in {"true", "1", "success", "paid", "ok"}
        if response.status_code >= 400 or ok is False:
            message = str(payload.get("message") or "refusé").strip()
            raise ProviderError(f"MoneyFusion a refusé la création : {message}")
        return payload
