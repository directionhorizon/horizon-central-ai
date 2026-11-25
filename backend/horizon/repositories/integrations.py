"""Dépôt du registre des connexions et intégrations de HORIZON CENTRAL AI.

Principe de sécurité : **aucune valeur secrète n'est stockée ni renvoyée**.
Seul le *nom* de la variable d'environnement porteuse de la clé est conservé
(`api_key_env`). Les réponses ne contiennent donc jamais de secret.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = (
    "id,name,category,method,endpoint,status,permissions,capabilities,"
    "api_key_env,last_checked_at,last_error,config_json,archived,created_at,updated_at"
)

CATEGORIES = (
    "orchestrator",
    "app",
    "llm_provider",
    "model",
    "mcp",
    "api",
    "machine",
    "storage",
    "communication",
    "payment",
)

METHODS = ("oauth2", "api_key", "bearer", "endpoint", "mcp", "rest", "cli", "webhook")

STATUSES = (
    "connected",
    "not_configured",
    "pending",
    "expired",
    "unavailable",
    "error",
    "partial",
)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    try:
        item["config"] = json.loads(item.pop("config_json") or "{}")
    except ValueError:
        item["config"] = {}
    item["archived"] = bool(item.get("archived"))
    return item


def list_integrations(
    db: sqlite3.Connection,
    *,
    category: str | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    query = f"SELECT {FIELDS} FROM integrations"
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("archived=0")
    if category:
        clauses.append("category=?")
        params.append(category)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY category, name"
    return [_row_to_dict(row) for row in db.execute(query, tuple(params)) if row]


def get_integration(db: sqlite3.Connection, integration_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {FIELDS} FROM integrations WHERE id=?", (integration_id,)).fetchone()
    return _row_to_dict(row)


def create_integration(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    row_id, stamp = str(uuid.uuid4()), now()
    db.execute(
        "INSERT INTO integrations(id,name,category,method,endpoint,status,permissions,"
        "capabilities,api_key_env,last_checked_at,last_error,config_json,archived,created_at,updated_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)",
        (
            row_id,
            payload["name"],
            payload["category"],
            payload["method"],
            payload.get("endpoint", ""),
            payload.get("status", "not_configured"),
            payload.get("permissions", ""),
            payload.get("capabilities", ""),
            payload.get("api_key_env", ""),
            None,
            "",
            json.dumps(payload.get("config") or {}, ensure_ascii=False),
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_integration(db, row_id) or {}


def update_integration(
    db: sqlite3.Connection, integration_id: str, changes: dict[str, Any]
) -> dict[str, Any] | None:
    current = get_integration(db, integration_id)
    if current is None:
        return None
    mapping = {
        "name": "name",
        "category": "category",
        "method": "method",
        "endpoint": "endpoint",
        "status": "status",
        "permissions": "permissions",
        "capabilities": "capabilities",
        "api_key_env": "api_key_env",
    }
    assignments: list[str] = []
    params: list[Any] = []
    for key, column in mapping.items():
        if key in changes and changes[key] is not None:
            assignments.append(f"{column}=?")
            params.append(changes[key])
    if "config" in changes and isinstance(changes["config"], dict):
        assignments.append("config_json=?")
        params.append(json.dumps(changes["config"], ensure_ascii=False))
    if not assignments:
        return current
    assignments.append("updated_at=?")
    params.append(now())
    params.append(integration_id)
    db.execute(f"UPDATE integrations SET {', '.join(assignments)} WHERE id=?", tuple(params))
    db.commit()
    return get_integration(db, integration_id)


def upsert_integration(
    db: sqlite3.Connection, integration_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Enregistre ou rafraîchit une fiche de façon idempotente (même identifiant).

    Les champs descriptifs sont mis à jour ; les choix de l'utilisateur
    (`permissions`, `config`) et l'état d'archivage ne sont jamais écrasés.
    Aucun secret n'est écrit : seul le nom de la variable d'environnement est
    conservé (`api_key_env`).
    """
    stamp = now()
    db.execute(
        "INSERT INTO integrations(id,name,category,method,endpoint,status,"
        "permissions,capabilities,api_key_env,config_json,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,'',?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "name=excluded.name, "
        "category=excluded.category, "
        "method=excluded.method, "
        "endpoint=excluded.endpoint, "
        "status=excluded.status, "
        "capabilities=excluded.capabilities, "
        "api_key_env=excluded.api_key_env, "
        "updated_at=excluded.updated_at",
        (
            integration_id,
            str(payload.get("name") or integration_id)[:120],
            str(payload.get("category") or "app"),
            str(payload.get("method") or "endpoint"),
            str(payload.get("endpoint") or "")[:500],
            str(payload.get("status") or "not_configured"),
            str(payload.get("capabilities") or "")[:500],
            str(payload.get("api_key_env") or "")[:120],
            "",
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_integration(db, integration_id) or {}


def archive_integration(db: sqlite3.Connection, integration_id: str) -> dict[str, Any] | None:
    """Suppression logique : la fiche est conservée, jamais purgée."""
    db.execute(
        "UPDATE integrations SET archived=1, status='unavailable', updated_at=? WHERE id=?",
        (now(), integration_id),
    )
    db.commit()
    return get_integration(db, integration_id)


def record_check(
    db: sqlite3.Connection, integration_id: str, status: str, error: str = ""
) -> dict[str, Any] | None:
    stamp = now()
    db.execute(
        "UPDATE integrations SET status=?, last_error=?, last_checked_at=?, updated_at=? WHERE id=?",
        (status, error[:500], stamp, stamp, integration_id),
    )
    db.commit()
    return get_integration(db, integration_id)


def stats(db: sqlite3.Connection) -> dict[str, Any]:
    rows = db.execute(
        "SELECT status, COUNT(*) AS n FROM integrations WHERE archived=0 GROUP BY status"
    ).fetchall()
    by_status = {row["status"]: int(row["n"]) for row in rows}
    total = db.execute("SELECT COUNT(*) AS n FROM integrations WHERE archived=0").fetchone()
    return {
        "total": int(total["n"]) if total else 0,
        "by_status": by_status,
        "connected": by_status.get("connected", 0),
        "needs_action": sum(
            count
            for status, count in by_status.items()
            if status in {"error", "expired", "partial", "pending"}
        ),
    }