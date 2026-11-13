"""Dépôt de la synchronisation Offline-First.

Modèle « boîte d'envoi » (outbox) : toute écriture locale est enregistrée ici
puis poussée vers le service distant quand la connexion revient. Un conflit est
toujours consigné, jamais écrasé silencieusement.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..db import now

OUTBOX_FIELDS = (
    "id,entity,entity_id,operation,payload_json,status,attempts,last_error,created_at,updated_at"
)
CONFLICT_FIELDS = (
    "id,entity,entity_id,local_updated_at,remote_updated_at,reason,resolved,created_at"
)


def enqueue(
    db: sqlite3.Connection,
    entity: str,
    entity_id: str,
    operation: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enregistre une intention de synchronisation (aucun envoi réseau ici)."""
    row_id, stamp = str(uuid.uuid4()), now()
    db.execute(
        "INSERT INTO sync_outbox(id,entity,entity_id,operation,payload_json,status,attempts,last_error,created_at,updated_at)"
        " VALUES(?,?,?,?,?,'pending',0,'',?,?)",
        (row_id, entity, entity_id, operation, json.dumps(payload or {}, ensure_ascii=False), stamp, stamp),
    )
    db.commit()
    return get_outbox(db, row_id) or {}


def get_outbox(db: sqlite3.Connection, row_id: str) -> dict[str, Any] | None:
    row = db.execute(
        f"SELECT {OUTBOX_FIELDS} FROM sync_outbox WHERE id=?", (row_id,)
    ).fetchone()
    return dict(row) if row else None


def list_outbox(
    db: sqlite3.Connection, status: str | None = "pending", limit: int = 200
) -> list[dict[str, Any]]:
    if status:
        rows = db.execute(
            f"SELECT {OUTBOX_FIELDS} FROM sync_outbox WHERE status=? ORDER BY created_at ASC LIMIT ?",
            (status, max(1, min(limit, 1000))),
        ).fetchall()
    else:
        rows = db.execute(
            f"SELECT {OUTBOX_FIELDS} FROM sync_outbox ORDER BY created_at ASC LIMIT ?",
            (max(1, min(limit, 1000)),),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_synced(db: sqlite3.Connection, row_id: str, remote_updated_at: str | None = None) -> None:
    stamp = now()
    row = get_outbox(db, row_id)
    if row is None:
        return
    db.execute(
        "UPDATE sync_outbox SET status='synced', attempts=attempts+1, last_error='', updated_at=? WHERE id=?",
        (stamp, row_id),
    )
    db.execute(
        "INSERT INTO sync_state(entity,entity_id,last_synced_at,remote_updated_at,local_updated_at)"
        " VALUES(?,?,?,?,?)"
        " ON CONFLICT(entity,entity_id) DO UPDATE SET"
        " last_synced_at=excluded.last_synced_at,"
        " remote_updated_at=COALESCE(excluded.remote_updated_at, sync_state.remote_updated_at),"
        " local_updated_at=excluded.local_updated_at",
        (row["entity"], row["entity_id"], stamp, remote_updated_at, row.get("updated_at")),
    )
    db.commit()


def mark_failed(db: sqlite3.Connection, row_id: str, error: str) -> None:
    db.execute(
        "UPDATE sync_outbox SET status='failed', attempts=attempts+1, last_error=?, updated_at=? WHERE id=?",
        (error[:2000], now(), row_id),
    )
    db.commit()


def mark_conflict(db: sqlite3.Connection, row_id: str, reason: str) -> None:
    db.execute(
        "UPDATE sync_outbox SET status='conflict', last_error=?, updated_at=? WHERE id=?",
        (reason[:2000], now(), row_id),
    )
    db.commit()


def record_conflict(
    db: sqlite3.Connection,
    entity: str,
    entity_id: str,
    reason: str,
    local_updated_at: str | None = None,
    remote_updated_at: str | None = None,
) -> dict[str, Any]:
    conflict_id, stamp = str(uuid.uuid4()), now()
    db.execute(
        "INSERT INTO sync_conflicts(id,entity,entity_id,local_updated_at,remote_updated_at,reason,resolved,created_at)"
        " VALUES(?,?,?,?,?,?,0,?)",
        (conflict_id, entity, entity_id, local_updated_at, remote_updated_at, reason[:2000], stamp),
    )
    db.commit()
    row = db.execute(
        f"SELECT {CONFLICT_FIELDS} FROM sync_conflicts WHERE id=?", (conflict_id,)
    ).fetchone()
    return dict(row) if row else {}


def list_conflicts(db: sqlite3.Connection, resolved: bool = False) -> list[dict[str, Any]]:
    rows = db.execute(
        f"SELECT {CONFLICT_FIELDS} FROM sync_conflicts WHERE resolved=? ORDER BY created_at DESC",
        (1 if resolved else 0,),
    ).fetchall()
    return [dict(row) for row in rows]


def resolve_conflict(db: sqlite3.Connection, conflict_id: str) -> dict[str, Any] | None:
    db.execute("UPDATE sync_conflicts SET resolved=1 WHERE id=?", (conflict_id,))
    db.commit()
    row = db.execute(
        f"SELECT {CONFLICT_FIELDS} FROM sync_conflicts WHERE id=?", (conflict_id,)
    ).fetchone()
    return dict(row) if row else None


def stats(db: sqlite3.Connection) -> dict[str, Any]:
    def count(query: str, params: tuple = ()) -> int:
        row = db.execute(query, params).fetchone()
        return int(row["n"]) if row else 0

    return {
        "pending": count("SELECT COUNT(*) AS n FROM sync_outbox WHERE status='pending'"),
        "synced": count("SELECT COUNT(*) AS n FROM sync_outbox WHERE status='synced'"),
        "failed": count("SELECT COUNT(*) AS n FROM sync_outbox WHERE status='failed'"),
        "conflicts": count("SELECT COUNT(*) AS n FROM sync_conflicts WHERE resolved=0"),
    }
