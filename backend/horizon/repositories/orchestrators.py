"""Dépôt des orchestrateurs : registre, capacités, associations projets."""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..db import now

BASE_FIELDS = (
    "id,name,kind,description,endpoint,version,status,health_status,"
    "last_checked_at,config_json,created_at,updated_at"
)

PREFIXED_FIELDS = ", ".join(f"o.{name}" for name in BASE_FIELDS.split(","))


def _decode(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    raw = item.pop("config_json", "{}")
    try:
        item["config"] = json.loads(raw) if raw else {}
    except ValueError:
        item["config"] = {}
    return item


def _capabilities(db: sqlite3.Connection, orchestrator_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not orchestrator_ids:
        return {}
    placeholders = ",".join("?" for _ in orchestrator_ids)
    rows = db.execute(
        f"""SELECT id,orchestrator_id,capability_id,level,detail,created_at
            FROM orchestrator_capabilities WHERE orchestrator_id IN ({placeholders})
            ORDER BY capability_id""",
        orchestrator_ids,
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(item.pop("orchestrator_id"), []).append(item)
    return grouped


def _projects(db: sqlite3.Connection, orchestrator_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not orchestrator_ids:
        return {}
    placeholders = ",".join("?" for _ in orchestrator_ids)
    rows = db.execute(
        f"""SELECT op.orchestrator_id, op.project_id, op.role, op.created_at,
                   p.name AS project_name, p.status AS project_status
            FROM orchestrator_projects op
            JOIN projects p ON p.id = op.project_id
            WHERE op.orchestrator_id IN ({placeholders})
            ORDER BY p.name""",
        orchestrator_ids,
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(item.pop("orchestrator_id"), []).append(item)
    return grouped


def _models(db: sqlite3.Connection, orchestrator_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not orchestrator_ids:
        return {}
    placeholders = ",".join("?" for _ in orchestrator_ids)
    rows = db.execute(
        f"""SELECT oms.orchestrator_id, oms.provider_id, oms.model,
                   lp.name AS provider_name, lp.status AS provider_status
            FROM orchestrator_model_selection oms
            JOIN llm_providers lp ON lp.id = oms.provider_id
            WHERE oms.orchestrator_id IN ({placeholders})""",
        orchestrator_ids,
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(item.pop("orchestrator_id"), []).append(item)
    return grouped


def list_orchestrators(
    db: sqlite3.Connection, status: str | None = None, project_id: str | None = None
) -> list[dict[str, Any]]:
    query = f"SELECT DISTINCT {PREFIXED_FIELDS} FROM orchestrators o"
    params: list[Any] = []
    if project_id:
        query += " JOIN orchestrator_projects op ON op.orchestrator_id = o.id AND op.project_id = ?"
        params.append(project_id)
    if status:
        query += " WHERE o.status = ?"
        params.append(status)
    query += " ORDER BY o.created_at DESC"
    rows = db.execute(query, params).fetchall()
    items = [_decode(row) for row in rows]
    ids = [item["id"] for item in items]
    caps, projects, models = _capabilities(db, ids), _projects(db, ids), _models(db, ids)
    for item in items:
        item["capabilities"] = caps.get(item["id"], [])
        item["projects"] = projects.get(item["id"], [])
        item["model_selection"] = models.get(item["id"], [])
    return items


def get_orchestrator(db: sqlite3.Connection, orchestrator_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {BASE_FIELDS} FROM orchestrators WHERE id=?", (orchestrator_id,)).fetchone()
    if not row:
        return None
    item = _decode(row)
    item["capabilities"] = _capabilities(db, [orchestrator_id]).get(orchestrator_id, [])
    item["projects"] = _projects(db, [orchestrator_id]).get(orchestrator_id, [])
    item["model_selection"] = _models(db, [orchestrator_id]).get(orchestrator_id, [])
    return item


def create_orchestrator(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    oid, stamp = str(uuid.uuid4()), now()
    db.execute(
        """INSERT INTO orchestrators(
            id,name,kind,description,endpoint,version,status,health_status,
            last_checked_at,config_json,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            oid,
            data["name"],
            data.get("kind", "local"),
            data.get("description", ""),
            data.get("endpoint", ""),
            data.get("version", ""),
            data.get("status", "active"),
            "unverified",
            None,
            json.dumps(data.get("config") or {}, ensure_ascii=False),
            stamp,
            stamp,
        ),
    )
    for capability in data.get("capabilities") or []:
        _insert_capability(db, oid, capability)
    db.commit()
    return get_orchestrator(db, oid) or {}


def _insert_capability(db: sqlite3.Connection, orchestrator_id: str, capability: dict[str, Any]) -> None:
    db.execute(
        """INSERT OR IGNORE INTO orchestrator_capabilities(
            id,orchestrator_id,capability_id,level,detail,created_at
        ) VALUES(?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            orchestrator_id,
            capability.get("capability_id", ""),
            capability.get("level", "standard"),
            capability.get("detail", ""),
            now(),
        ),
    )


def add_capability(db: sqlite3.Connection, orchestrator_id: str, capability: dict[str, Any]) -> dict[str, Any] | None:
    _insert_capability(db, orchestrator_id, capability)
    db.commit()
    return get_orchestrator(db, orchestrator_id)


def remove_capability(db: sqlite3.Connection, orchestrator_id: str, capability_id: str) -> dict[str, Any] | None:
    db.execute(
        "DELETE FROM orchestrator_capabilities WHERE orchestrator_id=? AND capability_id=?",
        (orchestrator_id, capability_id),
    )
    db.commit()
    return get_orchestrator(db, orchestrator_id)


def update_orchestrator(db: sqlite3.Connection, orchestrator_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    current = get_orchestrator(db, orchestrator_id)
    if current is None:
        return None
    allowed: dict[str, Any] = {}
    for key in ("name", "kind", "description", "endpoint", "version", "status"):
        if changes.get(key) is not None:
            allowed[key] = changes[key]
    if changes.get("config") is not None:
        allowed["config_json"] = json.dumps(changes["config"], ensure_ascii=False)
    if allowed:
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(
            f"UPDATE orchestrators SET {assignments}, updated_at=? WHERE id=?",
            (*allowed.values(), now(), orchestrator_id),
        )
        db.commit()
    return get_orchestrator(db, orchestrator_id)


def set_health(
    db: sqlite3.Connection,
    orchestrator_id: str,
    health_status: str,
) -> dict[str, Any] | None:
    db.execute(
        "UPDATE orchestrators SET health_status=?, last_checked_at=?, updated_at=? WHERE id=?",
        (health_status, now(), now(), orchestrator_id),
    )
    db.commit()
    return get_orchestrator(db, orchestrator_id)


def disable_orchestrator(db: sqlite3.Connection, orchestrator_id: str) -> dict[str, Any] | None:
    """Désactivation logique : la fiche est conservée pour l'historique."""
    return update_orchestrator(db, orchestrator_id, {"status": "disabled"})


def link_project(db: sqlite3.Connection, orchestrator_id: str, project_id: str, role: str) -> bool:
    cursor = db.execute(
        """INSERT OR IGNORE INTO orchestrator_projects(orchestrator_id,project_id,role,created_at)
           VALUES(?,?,?,?)""",
        (orchestrator_id, project_id, role, now()),
    )
    db.commit()
    return cursor.rowcount > 0


def unlink_project(db: sqlite3.Connection, orchestrator_id: str, project_id: str) -> bool:
    cursor = db.execute(
        "DELETE FROM orchestrator_projects WHERE orchestrator_id=? AND project_id=?",
        (orchestrator_id, project_id),
    )
    db.commit()
    return cursor.rowcount > 0


def set_model_selection(
    db: sqlite3.Connection, orchestrator_id: str, provider_id: str, model: str
) -> dict[str, Any] | None:
    stamp = now()
    db.execute(
        """INSERT INTO orchestrator_model_selection(
            orchestrator_id,provider_id,model,created_at,updated_at
        ) VALUES(?,?,?,?,?)
        ON CONFLICT(orchestrator_id,provider_id)
        DO UPDATE SET model=excluded.model, updated_at=excluded.updated_at""",
        (orchestrator_id, provider_id, model, stamp, stamp),
    )
    db.commit()
    return get_orchestrator(db, orchestrator_id)
