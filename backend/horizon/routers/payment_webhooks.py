"""Webhooks des fournisseurs de paiement (retour signé, idempotent).

Un webhook n'est jamais cru sur parole : la signature est vérifiée par
l'adaptateur du fournisseur avant tout enregistrement. Un événement déjà reçu
n'est jamais rejoué (idempotence par identifiant d'événement).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .. import payment_providers
from ..db import connect
from ..repositories import payments

router = APIRouter(prefix="/api/v1/payments/webhook", tags=["payments"])


@router.post("/{provider_kind}")
async def receive_webhook(provider_kind: str, request: Request):
    """Reçoit un événement fournisseur, vérifie sa signature, met à jour le statut."""
    body = await request.body()
    try:
        provider = payment_providers.get_provider(provider_kind)
    except payment_providers.ProviderError as error:
        raise HTTPException(404, str(error)) from error
    headers = {str(key): str(value) for key, value in request.headers.items()}
    try:
        event = provider.verify_webhook(body, headers)
    except payment_providers.ProviderError as error:
        raise HTTPException(400, str(error)) from error
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    target = provider.webhook_event(event)
    payment_id = target[0] if target else ""
    status = target[1] if target else ""
    with connect() as db:
        inserted = payments.record_event(
            db,
            event_id,
            provider.kind,
            event_type,
            payment_id,
            body.decode("utf-8", errors="replace"),
        )
        if not inserted:
            return {
                "received": True,
                "duplicate": True,
                "event": event_id,
                "type": event_type,
            }
        if payment_id and status:
            payments.update_status(db, payment_id, status)
    return {
        "received": True,
        "duplicate": False,
        "event": event_id,
        "type": event_type,
        "payment_id": payment_id,
        "status": status,
    }
