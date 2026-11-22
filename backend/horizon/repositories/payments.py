"""Dépôt des paiements (PaymentIntents Stripe)."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..db import now

FIELDS = (
    "id,provider,amount,currency,status,detail,mode,checkout_url,"
    "idempotency_key,created_at"
)


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
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Enregistre ou met à jour un paiement déjà créé. Idempotent sur l'identifiant.

    La première écriture peut venir du moteur (sans référence) ; la mise à jour
    ultérieure complète les champs vides sans jamais écraser une valeur existante.
    """
    stamp = now()
    db.execute(
        "INSERT INTO payments(id,provider,amount,currency,status,detail,mode,"
        "checkout_url,idempotency_key,created_at) VALUES(?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "status=excluded.status, "
        "detail=CASE WHEN excluded.detail<>'' THEN excluded.detail ELSE payments.detail END, "
        "provider=CASE WHEN excluded.provider<>'' THEN excluded.provider ELSE payments.provider END, "
        "mode=CASE WHEN excluded.mode<>'' THEN excluded.mode ELSE payments.mode END, "
        "checkout_url=CASE WHEN excluded.checkout_url<>'' THEN excluded.checkout_url "
        "ELSE payments.checkout_url END, "
        "idempotency_key=CASE WHEN excluded.idempotency_key<>'' "
        "THEN excluded.idempotency_key ELSE payments.idempotency_key END",
        (
            payment_id,
            str(provider or "stripe"),
            int(amount),
            str(currency or "eur").lower(),
            str(status or "created"),
            str(detail or ""),
            str(mode or "intent"),
            str(checkout_url or ""),
            str(idempotency_key or ""),
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
        "idempotency_key": idempotency_key,
        "created_at": stamp,
    }


def get_by_idempotency_key(
    db: sqlite3.Connection, idempotency_key: str
) -> dict[str, Any] | None:
    """Retrouve un paiement déjà créé avec la même clé d'idempotence."""
    key = str(idempotency_key or "").strip()
    if not key:
        return None
    row = db.execute(
        f"SELECT {FIELDS} FROM payments WHERE idempotency_key=?", (key,)
    ).fetchone()
    return dict(row) if row else None


def update_status(
    db: sqlite3.Connection, payment_id: str, status: str
) -> dict[str, Any] | None:
    """Met à jour le statut local d'un paiement (webhook, remboursement)."""
    db.execute(
        "UPDATE payments SET status=? WHERE id=?", (str(status or ""), payment_id)
    )
    db.commit()
    return get_payment(db, payment_id)


def record_event(
    db: sqlite3.Connection,
    event_id: str,
    provider: str,
    event_type: str,
    payment_id: str = "",
    payload: str = "",
) -> bool:
    """Enregistre un événement fournisseur. Rend False s'il était déjà connu."""
    identifier = str(event_id or "").strip()
    if not identifier:
        return False
    cursor = db.execute(
        "INSERT OR IGNORE INTO payment_events"
        "(id,provider,event_type,payment_id,payload,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (
            identifier,
            str(provider or ""),
            str(event_type or ""),
            str(payment_id or ""),
            str(payload or "")[:20000],
            now(),
        ),
    )
    db.commit()
    return cursor.rowcount > 0


def list_events(
    db: sqlite3.Connection, payment_id: str = "", limit: int = 100
) -> list[dict[str, Any]]:
    """Journal des événements reçus (le plus récent d'abord)."""
    if payment_id:
        rows = db.execute(
            "SELECT id,provider,event_type,payment_id,created_at FROM payment_events "
            "WHERE payment_id=? ORDER BY created_at DESC LIMIT ?",
            (payment_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id,provider,event_type,payment_id,created_at FROM payment_events "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
