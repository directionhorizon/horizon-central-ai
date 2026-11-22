"""Routes des paiements (PaymentIntents Stripe).

La création exige une validation humaine explicite (`confirm=true`) : sans cela,
l'outil répond `requires_human_validation` et aucun paiement n'est créé.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import tool_runtime
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
            )
            operations.log(
                db,
                actor=actor,
                action="payment.create",
                target_type="payment",
                target_id=str(payment_id),
                detail=f"Paiement {result.get('status')}",
            )
    return result


@router.get("/{payment_id}")
def read_payment(payment_id: str):
    with connect() as db:
        item = payments.get_payment(db, payment_id)
        if item is None:
            raise HTTPException(404, "Paiement introuvable.")
    return item
