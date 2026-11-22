"""Routes des paiements (multi-fournisseurs, via adaptateurs).

La création exige une validation humaine explicite (`confirm=true`) : sans cela,
l'outil répond `requires_human_validation` et aucun paiement n'est créé.
Le fournisseur est choisi par configuration (`HORIZON_PAYMENT_PROVIDER`) ou par
la demande ; aucun fournisseur n'est codé en dur dans ces routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import payment_providers, tool_runtime
from ..auth import require_admin
from ..db import connect
from ..models import PaymentCreate
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
async def create_payment(payload: PaymentCreate, actor: str = Depends(require_admin)):
    with connect() as db:
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
            "success_url": payload.success_url,
            "cancel_url": payload.cancel_url,
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
                payload.detail,
                provider=str(result.get("provider") or payload.provider or "stripe"),
                mode=str(result.get("mode") or payload.mode),
                checkout_url=str(result.get("checkout_url") or ""),
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


@router.get("/{payment_id}")
def read_payment(payment_id: str):
    with connect() as db:
        item = payments.get_payment(db, payment_id)
        if item is None:
            raise HTTPException(404, "Paiement introuvable.")
    return item
