"""Dépôt des projets."""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = "id,name,description,status,created_at,updated_at"


def list_projects(db: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    if status:
        rows = db.execute(
            f"SELECT {FIELDS} FROM projects WHERE status=? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = db.execute(f"SELECT {FIELDS} FROM projects ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_project(db: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {FIELDS} FROM projects WHERE id=?", (project_id,)).fetchone()
    return dict(row) if row else None


def create_project(db: sqlite3.Connection, name: str, description: str, status: str) -> dict[str, Any]:
    pid, stamp = str(uuid.uuid4()), now()
    db.execute(
        "INSERT INTO projects(id,name,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (pid, name, description, status, stamp, stamp),
    )
    db.commit()
    return {"id": pid, "name": name, "description": description, "status": status,
            "created_at": stamp, "updated_at": stamp}


def update_project(db: sqlite3.Connection, project_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    current = get_project(db, project_id)
    if current is None:
        return None
    allowed = {key: value for key, value in changes.items() if key in {"name", "description", "status"} and value is not None}
    if allowed:
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(
            f"UPDATE projects SET {assignments}, updated_at=? WHERE id=?",
            (*allowed.values(), now(), project_id),
        )
        db.commit()
    return get_project(db, project_id)


def archive_project(db: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    """Archivage logique : aucune ligne n'est supprimée."""
    return update_project(db, project_id, {"status": "archived"})


def count_missions(db: sqlite3.Connection, project_id: str) -> int:
    row = db.execute("SELECT COUNT(*) AS n FROM missions WHERE project_id=?", (project_id,)).fetchone()
    return int(row["n"]) if row else 0


def count_orchestrators(db: sqlite3.Connection, project_id: str) -> int:
    row = db.execute(
        "SELECT COUNT(*) AS n FROM orchestrator_projects WHERE project_id=?", (project_id,)
    ).fetchone()
    return int(row["n"]) if row else 0
