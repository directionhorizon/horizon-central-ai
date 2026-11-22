"""Dépôt des paiements (PaymentIntents Stripe)."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..db import now

FIELDS = "id,provider,amount,currency,status,detail,mode,checkout_url,created_at"


def list_payments(db: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.execute(
        f"SELECT {FIELDS} FROM payments ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_payment(db: sqlite3.Connection, payment_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {FIELDS} FROM payments WHERE id=?", (payment_id,)).fetchone()
    return dict(row) if row else None


def record_payment(
    db: sqlite3.Connection,
    payment_id: str,
    amount: int,
    currency: str,
    status: str,
    detail: str = "",
    provider: str = "stripe",
    mode: str = "intent",
    checkout_url: str = "",
) -> dict[str, Any]:
    """Enregistre ou met à jour un paiement déjà créé. Idempotent sur l'identifiant.

    La première écriture peut venir du moteur (sans référence) ; la mise à jour
    ultérieure complète les champs vides sans jamais écraser une valeur existante.
    """
    stamp = now()
    db.execute(
        "INSERT INTO payments(id,provider,amount,currency,status,detail,mode,"
        "checkout_url,created_at) VALUES(?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "status=excluded.status, "
        "detail=CASE WHEN excluded.detail<>'' THEN excluded.detail ELSE payments.detail END, "
        "provider=CASE WHEN excluded.provider<>'' THEN excluded.provider ELSE payments.provider END, "
        "mode=CASE WHEN excluded.mode<>'' THEN excluded.mode ELSE payments.mode END, "
        "checkout_url=CASE WHEN excluded.checkout_url<>'' THEN excluded.checkout_url "
        "ELSE payments.checkout_url END",
        (
            payment_id,
            str(provider or "stripe"),
            int(amount),
            str(currency or "eur").lower(),
            str(status or "created"),
            str(detail or ""),
            str(mode or "intent"),
            str(checkout_url or ""),
            stamp,
        ),
    )
    db.commit()
    return get_payment(db, payment_id) or {
        "id": payment_id,
        "provider": provider,
        "amount": int(amount),
        "currency": str(currency or "eur").lower(),
        "status": status,
        "detail": detail,
        "mode": mode,
        "checkout_url": checkout_url,
        "created_at": stamp,
    }
