"""Dépôt des missions, étapes et points de contrôle."""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..db import now

MISSION_FIELDS = (
    "id,project_id,title,description,status,priority,orchestrator_id,created_at,updated_at"
)


def _mission(db: sqlite3.Connection, mission_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {MISSION_FIELDS} FROM missions WHERE id=?", (mission_id,)).fetchone()
    return dict(row) if row else None


def _steps(db: sqlite3.Connection, mission_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """SELECT id,mission_id,position,title,status,assigned_orchestrator_id,assigned_agent_id,
                  started_at,completed_at,error
           FROM mission_steps WHERE mission_id=? ORDER BY position,id""",
        (mission_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _checkpoints(db: sqlite3.Connection, mission_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """SELECT id,mission_id,step_id,label,state_json,created_at
           FROM mission_checkpoints WHERE mission_id=? ORDER BY created_at,id""",
        (mission_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        raw = item.pop("state_json", "{}")
        try:
            item["state"] = json.loads(raw) if raw else {}
        except ValueError:
            item["state"] = {}
        items.append(item)
    return items


def get_mission(db: sqlite3.Connection, mission_id: str) -> dict[str, Any] | None:
    item = _mission(db, mission_id)
    if item is None:
        return None
    item["steps"] = _steps(db, mission_id)
    item["checkpoints"] = _checkpoints(db, mission_id)
    return item


def list_missions(
    db: sqlite3.Connection,
    project_id: str | None = None,
    status: str | None = None,
    orchestrator_id: str | None = None,
) -> list[dict[str, Any]]:
    query = f"SELECT {MISSION_FIELDS} FROM missions WHERE 1=1"
    params: list[Any] = []
    if project_id:
        query += " AND project_id=?"
        params.append(project_id)
    if status:
        query += " AND status=?"
        params.append(status)
    if orchestrator_id:
        query += " AND orchestrator_id=?"
        params.append(orchestrator_id)
    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["steps"] = _steps(db, item["id"])
        item["checkpoint_count"] = len(_checkpoints(db, item["id"]))
    return items


def create_mission(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    mid, stamp = str(uuid.uuid4()), now()
    db.execute(
        """INSERT INTO missions(
            id,project_id,title,description,status,priority,orchestrator_id,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            mid,
            data["project_id"],
            data["title"],
            data.get("description", ""),
            data.get("status", "draft"),
            data.get("priority", "normal"),
            data.get("orchestrator_id"),
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_mission(db, mid) or {}


def update_mission(db: sqlite3.Connection, mission_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    if _mission(db, mission_id) is None:
        return None
    allowed: dict[str, Any] = {}
    for key in ("title", "description", "status", "priority"):
        if changes.get(key) is not None:
            allowed[key] = changes[key]
    if "orchestrator_id" in changes:
        allowed["orchestrator_id"] = changes["orchestrator_id"]
    if allowed:
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(
            f"UPDATE missions SET {assignments}, updated_at=? WHERE id=?",
            (*allowed.values(), now(), mission_id),
        )
        db.commit()
    return get_mission(db, mission_id)


def next_position(db: sqlite3.Connection, mission_id: str) -> int:
    row = db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next FROM mission_steps WHERE mission_id=?",
        (mission_id,),
    ).fetchone()
    return int(row["next"]) if row else 0


def add_step(db: sqlite3.Connection, mission_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    if _mission(db, mission_id) is None:
        return None
    position = data.get("position")
    if position is None:
        position = next_position(db, mission_id)
    db.execute(
        """INSERT INTO mission_steps(
            id,mission_id,position,title,status,assigned_orchestrator_id,assigned_agent_id,error
        ) VALUES(?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            mission_id,
            int(position),
            data["title"],
            "pending",
            data.get("assigned_orchestrator_id"),
            data.get("assigned_agent_id", ""),
            "",
        ),
    )
    db.commit()
    return get_mission(db, mission_id)


def update_step(
    db: sqlite3.Connection, mission_id: str, step_id: str, changes: dict[str, Any]
) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT id,status FROM mission_steps WHERE id=? AND mission_id=?", (step_id, mission_id)
    ).fetchone()
    if row is None:
        return None
    stamp = now()
    allowed: dict[str, Any] = {}
    for key in ("title", "error"):
        if changes.get(key) is not None:
            allowed[key] = changes[key]
    if "assigned_orchestrator_id" in changes:
        allowed["assigned_orchestrator_id"] = changes["assigned_orchestrator_id"]
    if "assigned_agent_id" in changes:
        allowed["assigned_agent_id"] = changes["assigned_agent_id"]
    new_status = changes.get("status")
    if new_status is not None:
        allowed["status"] = new_status
        if new_status == "running" and row["status"] != "running":
            allowed["started_at"] = stamp
        if new_status in ("completed", "failed", "skipped"):
            allowed["completed_at"] = stamp
            if row["status"] != "running":
                allowed["started_at"] = stamp
    if allowed:
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(f"UPDATE mission_steps SET {assignments} WHERE id=?", (*allowed.values(), step_id))
        db.execute("UPDATE missions SET updated_at=? WHERE id=?", (stamp, mission_id))
        db.commit()
    return get_mission(db, mission_id)


def add_checkpoint(db: sqlite3.Connection, mission_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    if _mission(db, mission_id) is None:
        return None
    db.execute(
        """INSERT INTO mission_checkpoints(id,mission_id,step_id,label,state_json,created_at)
           VALUES(?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            mission_id,
            data.get("step_id"),
            data["label"],
            json.dumps(data.get("state") or {}, ensure_ascii=False),
            now(),
        ),
    )
    db.commit()
    return get_mission(db, mission_id)


def list_checkpoints(db: sqlite3.Connection, mission_id: str) -> list[dict[str, Any]]:
    return _checkpoints(db, mission_id)