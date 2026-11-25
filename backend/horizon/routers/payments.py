"""Routes des paiements (multi-fournisseurs, via adaptateurs).

La création exige une validation humaine explicite (`confirm=true`) : sans cela,
l'outil répond `requires_human_validation` et aucun paiement n'est créé.
Le fournisseur est choisi par configuration (`HORIZON_PAYMENT_PROVIDER`) ou par
la demande ; aucun fournisseur n'est codé en dur dans ces routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from .. import payment_providers, tool_runtime
from ..auth import require_admin
from ..db import connect
from ..models import PaymentCreate, RefundCreate
from ..repositories import operations, payments, tools

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.get("")
def list_payments(limit: int = 100):
    with connect() as db:
        items = payments.list_payments(db, limit=limit)
    return {"items": items}


@router.get("/providers")
def list_providers():
    """Adaptateurs disponibles et état de configuration (aucun secret exposé)."""
    return {
        "items": payment_providers.describe_providers(),
        "default": payment_providers.default_provider(),
    }


@router.post("")
async def create_payment(
    payload: PaymentCreate,
    actor: str = Depends(require_admin),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    key = str(idempotency_key or "").strip()
    with connect() as db:
        if key:
            existing = payments.get_by_idempotency_key(db, key)
            if existing is not None:
                # Rejeu : le même appel ne doit jamais créer un second paiement.
                return {**existing, "replayed": True}
        tool = tools.get_tool(db, "tool-payment")
        if tool is None:
            raise HTTPException(404, "Outil de paiement introuvable.")
        params = {
            "amount": payload.amount,
            "currency": payload.currency,
            "confirm": payload.confirm,
            "provider": payload.provider,
            "mode": payload.mode,
            "account": payload.account,
            "detail": payload.detail,
            "customer_email": payload.customer_email,
            "customer_name": payload.customer_name,
            "customer": payload.customer,
            "success_url": payload.success_url,
            "cancel_url": payload.cancel_url,
            "idempotency_key": key,
        }
        try:
            result = await tool_runtime.run_tool(db, tool, params)
        except tool_runtime.ToolError as error:
            raise HTTPException(400, str(error)) from error
        if result.get("status") == "requires_human_validation":
            return result
        payment_id = result.get("id")
        if payment_id:
            payments.record_payment(
                db,
                str(payment_id),
                payload.amount,
                payload.currency,
                str(result.get("status") or "created"),
                str(result.get("detail") or payload.detail),
                provider=str(result.get("provider") or payload.provider or "stripe"),
                mode=str(result.get("mode") or payload.mode),
                checkout_url=str(result.get("checkout_url") or ""),
                idempotency_key=key,
            )
            operations.log(
                db,
                actor=actor,
                action="payment.create",
                target_type="payment",
                target_id=str(payment_id),
                detail=f"Paiement {result.get('provider')} {result.get('status')}",
            )
    return result


@router.get("/events")
def list_payment_events(payment_id: str = "", limit: int = 100):
    """Journal des événements fournisseurs reçus (aucun secret exposé)."""
    with connect() as db:
        items = payments.list_events(db, payment_id=payment_id, limit=limit)
    return {"items": items}


@router.get("/{payment_id}")
def read_payment(payment_id: str):
    with connect() as db:
        item = payments.get_payment(db, payment_id)
        if item is None:
            raise HTTPException(404, "Paiement introuvable.")
    return item


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: str,
    payload: RefundCreate,
    actor: str = Depends(require_admin),
):
    """Rembourse un paiement via l'adaptateur de son fournisseur."""
    with connect() as db:
        item = payments.get_payment(db, payment_id)
        if item is None:
            raise HTTPException(404, "Paiement introuvable.")
        try:
            provider = payment_providers.get_provider(item.get("provider") or "stripe")
            credentials = payment_providers.resolve_credentials(provider)
            result = await provider.refund(
                payment_id, payload.amount or 0, credentials, payload.reason
            )
        except payment_providers.ProviderError as error:
            raise HTTPException(400, str(error)) from error
        total = int(item.get("amount") or 0)
        refunded = payload.amount or total
        status = "refunded" if refunded >= total else "partially_refunded"
        payments.update_status(db, payment_id, status)
        operations.log(
            db,
            actor=actor,
            action="payment.refund",
            target_type="payment",
            target_id=payment_id,
            detail=f"Remboursement {refunded} {item.get('currency')} ({status})",
        )
    return result.as_dict()
