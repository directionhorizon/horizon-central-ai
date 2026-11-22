"""Dépôt des paiements (PaymentIntents Stripe)."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..db import now

FIELDS = "id,amount,currency,status,detail,created_at"


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
) -> dict[str, Any]:
    """Enregistre un PaymentIntent déjà créé. Idempotent sur l'identifiant."""
    stamp = now()
    db.execute(
        "INSERT OR IGNORE INTO payments(id,amount,currency,status,detail,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (payment_id, int(amount), currency, status, detail, stamp),
    )
    db.commit()
    return get_payment(db, payment_id) or {
        "id": payment_id,
        "amount": int(amount),
        "currency": currency,
        "status": status,
        "detail": detail,
        "created_at": stamp,
    }
