"""Dépôt des agents : chaque agent appartient à un système d'orchestration.

Le concept d'agent est générique : il vaut pour tous les systèmes. Un système
possède exactement un agent de rôle `orchestrator` (son coordinateur) et zéro ou
plusieurs agents `specialist`. HORIZON CORE supervise les systèmes sans
remplacer leurs agents coordinateurs.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = "id,orchestrator_id,name,role,description,spec,status,created_at,updated_at"


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def list_agents(
    db: sqlite3.Connection,
    *,
    orchestrator_id: str | None = None,
    role: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if orchestrator_id:
        clauses.append("orchestrator_id=?")
        params.append(orchestrator_id)
    if role:
        clauses.append("role=?")
        params.append(role)
    if status:
        clauses.append("status=?")
        params.append(status)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"SELECT {FIELDS} FROM agents{where} ORDER BY role DESC, name",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def get_agent(db: sqlite3.Connection, agent_id: str) -> dict[str, Any] | None:
    return _row(db.execute(f"SELECT {FIELDS} FROM agents WHERE id=?", (agent_id,)).fetchone())


def create_agent(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    aid, stamp = str(uuid.uuid4()), now()
    db.execute(
        """INSERT INTO agents(id,orchestrator_id,name,role,description,spec,status,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            aid,
            data["orchestrator_id"],
            data["name"],
            data.get("role", "specialist"),
            data.get("description", ""),
            data.get("spec", ""),
            data.get("status", "active"),
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_agent(db, aid) or {}


def update_agent(db: sqlite3.Connection, agent_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    if get_agent(db, agent_id) is None:
        return None
    columns = {
        "name": "name",
        "role": "role",
        "description": "description",
        "spec": "spec",
        "status": "status",
    }
    assignments = {
        column: value
        for key, column in columns.items()
        if key in changes and changes[key] is not None
    }
    if assignments:
        assignments["updated_at"] = now()
        clause = ", ".join(f"{column}=?" for column in assignments)
        db.execute(f"UPDATE agents SET {clause} WHERE id=?", (*assignments.values(), agent_id))
        db.commit()
    return get_agent(db, agent_id)
