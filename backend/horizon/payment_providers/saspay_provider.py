"""Adaptateur SasPay (Mobile Money + carte, Afrique de l'Ouest et du Centre).

SasPay expose une API REST unique : HORIZON crée une **session de checkout
hébergée**, renvoie l'URL au client, et SasPay notifie les changements de statut
par **webhook signé** (HMAC-SHA256 sur « horodatage.corps brut »).

Sécurité :
- la clé secrète (`sk_live_` / `sk_test_`) vit uniquement dans l'environnement ;
- le webhook est signé : la signature **et** l'horodatage sont vérifiés
  (tolérance 5 minutes), sinon un événement intercepté resterait rejouable ;
- aucune donnée bancaire ne transite par HORIZON : le client paie chez SasPay.

Point à confirmer par un test réel en sandbox : le rapprochement entre un
événement webhook et le paiement local. SasPay transmet l'identifiant de la
**transaction**, alors que HORIZON mémorise celui de la **session** de checkout.
Tant que ce point n'est pas vérifié sur un vrai événement, le statut peut être
réconcilié à la demande avec `GET /checkout-sessions/{id}/status/`.
"""
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
    ZERO_DECIMAL,
    PaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderError,
    fallback_detail,
)

#: API en production et en bac à sable (mêmes routes, données distinctes).
LIVE_BASE = "https://api.saspay.me/api/v1"
SANDBOX_BASE = "https://sandbox-api.saspay.me/api/v1"

BASE_ENV = "HORIZON_SASPAY_BASE_URL"
KEY_ENV = "HORIZON_SASPAY_API_KEY"
SECRET_ENV = "HORIZON_SASPAY_WEBHOOK_SECRET"

#: Tolérance d'horodatage du webhook, en secondes (documentation SasPay).
TOLERANCE_S = 300

#: Événements SasPay -> statuts locaux HORIZON.
EVENT_STATUS = {
    "transaction.created": "processing",
    "transaction.success": "succeeded",
    "transaction.failed": "failed",
    "transaction.cancelled": "canceled",
}

#: Statuts de session renvoyés par l'API -> statuts locaux.
SESSION_STATUS = {
    "paid": "succeeded",
    "success": "succeeded",
    "pending": "pending",
    "processing": "processing",
    "expired": "canceled",
    "cancelled": "canceled",
    "canceled": "canceled",
    "failed": "failed",
}


def _base() -> str:
    """Base d'API : production par défaut, sandbox si configurée."""
    return (os.getenv(BASE_ENV) or LIVE_BASE).strip().rstrip("/")


def _amount(amount: int, currency: str) -> str:
    """Montant au format attendu par SasPay : chaîne décimale.

    Les devises sans décimale (XAF, XOF…) sont déjà exprimées en unité entière
    dans HORIZON ; les autres sont converties depuis la plus petite unité.
    """
    code = str(currency or "").strip().lower()
    if code in ZERO_DECIMAL:
        return f"{int(amount)}.00"
    return f"{int(amount) / 100:.2f}"


class SasPayProvider(PaymentProvider):
    kind = "saspay"
    label = "SasPay (Mobile Money / carte)"
    capabilities = (MODE_CHECKOUT,)
    env_vars = (KEY_ENV,)
    docs_url = "https://docs.saspay.me/"

    async def create(
        self,
        request: PaymentRequest,
        credentials: Mapping[str, str],
        mode: str = MODE_INTENT,
    ) -> PaymentResult:
        key = str(credentials.get(KEY_ENV) or os.getenv(KEY_ENV) or "").strip()
        if not key:
            raise ProviderError(
                f"SasPay n'est pas configuré : clé absente ({KEY_ENV})."
            )
        if mode != MODE_CHECKOUT:
            raise ProviderError(
                f"SasPay ne gère pas le mode « {mode} » : seule la page de "
                "paiement hébergée est prise en charge."
            )
        body: dict[str, Any] = {
            "amount": _amount(int(request.amount), request.currency),
            "currency": str(request.currency or "xaf").upper(),
            "description": request.detail
            or fallback_detail(self.label, int(request.amount), request.currency),
            "customer_email": request.customer_email or "client@horizon.local",
            "customer_name": request.customer_name or request.customer or "Client",
        }
        if request.success_url:
            body["return_url"] = request.success_url
        # Permet, si SasPay le renvoie dans l'événement, de retrouver le
        # paiement local sans dépendre de l'identifiant de transaction.
        if request.idempotency_key:
            body["metadata"] = {"horizon_idempotency_key": request.idempotency_key}

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                f"{_base()}/checkout-sessions/",
                json=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
        payload = self._read(response)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        session_id = str(data.get("id") or "").strip()
        checkout_url = str(data.get("checkout_url") or data.get("url") or "").strip()
        if not session_id or not checkout_url:
            raise ProviderError(
                "SasPay n'a pas renvoyé d'identifiant de session ou d'URL de paiement."
            )
        return PaymentResult(
            provider=self.kind,
            id=session_id,
            status=SESSION_STATUS.get(
                str(data.get("status") or "").strip().lower(), "pending"
            ),
            amount=int(request.amount),
            currency=str(request.currency or "xaf").lower(),
            mode=MODE_CHECKOUT,
            detail=request.detail
            or fallback_detail(
                self.label, int(request.amount), request.currency, session_id
            ),
            checkout_url=checkout_url,
            raw=data,
        )

    def verify_webhook(
        self, payload: bytes, headers: Mapping[str, str]
    ) -> dict[str, Any]:
        """Vérifie l'horodatage **et** la signature HMAC du corps brut.

        La signature porte sur `horodatage.corps` : un attaquant ne peut donc pas
        rajeunir l'horodatage sans invalider la signature.
        """
        secret = (os.getenv(SECRET_ENV) or "").strip()
        if not secret:
            raise ProviderError(f"Webhook SasPay non configuré ({SECRET_ENV}).")
        lowered = {str(name).lower(): str(value) for name, value in headers.items()}
        signature = lowered.get("x-webhook-signature", "").strip()
        timestamp = lowered.get("x-webhook-timestamp", "").strip()
        if not signature or not timestamp:
            raise ProviderError(
                "En-têtes de signature SasPay absents (X-Webhook-Signature, "
                "X-Webhook-Timestamp)."
            )
        try:
            age = abs(time.time() - int(timestamp))
        except ValueError as error:
            raise ProviderError("Horodatage de webhook SasPay invalide.") from error
        if age > TOLERANCE_S:
            raise ProviderError("Webhook SasPay expiré (horodatage trop ancien).")
        # Signature calculée sur le corps BRUT reçu, jamais sur une re-sérialisation.
        signed = f"{timestamp}.".encode("utf-8") + payload
        computed = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, signature):
            raise ProviderError("Signature de webhook SasPay invalide.")
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as error:
            raise ProviderError("Charge utile SasPay illisible.") from error
        if not isinstance(event, dict):
            raise ProviderError("Charge utile SasPay inattendue.")
        event_type = str(event.get("event") or lowered.get("x-webhook-event") or "")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        identifier = str(
            data.get("transaction_id") or data.get("id") or data.get("reference") or ""
        ).strip()
        return {
            # Identifiant stable d'événement : garantit l'idempotence des rejeux.
            "id": f"{event_type}:{identifier}" if identifier else event_type,
            "type": event_type,
            "data": data,
        }

    def webhook_event(self, event: Mapping[str, Any]) -> tuple[str, str] | None:
        status = EVENT_STATUS.get(str(event.get("type") or ""))
        if not status:
            return None
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        identifier = str(
            metadata.get("horizon_idempotency_key")
            or data.get("transaction_id")
            or data.get("id")
            or data.get("reference")
            or ""
        ).strip()
        if not identifier:
            return None
        return identifier, status

    def _read(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except Exception as error:
            raise ProviderError(
                f"Réponse SasPay illisible (HTTP {response.status_code})."
            ) from error
        if not isinstance(payload, dict):
            raise ProviderError("Réponse SasPay inattendue.")
        if response.status_code >= 400 or payload.get("success") is False:
            error = payload.get("error")
            message = ""
            if isinstance(error, dict):
                message = str(error.get("code") or error.get("message") or "")
            elif isinstance(error, str):
                message = error
            raise ProviderError(
                f"SasPay a refusé la création : {message or 'refusé'} "
                f"(HTTP {response.status_code})."
            )
        return payload


