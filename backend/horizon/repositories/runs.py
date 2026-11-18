"""Dépôt des exécutions confiées aux orchestrateurs (`orchestrator_runs`).

Chaque ligne correspond à un dispatch réel : une clé d'idempotence, un run_id
Hermes, un statut, et le résultat persisté. Aucun champ ne contient de secret :
les jetons et clés ne sont jamais stockés ici.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..db import now

RUN_FIELDS = (
    "id,mission_id,step_id,orchestrator_id,run_id,session_id,idempotency_key,status,phase,"
    "replayed_count,requested_at,started_at,finished_at,output,error,usage_json,runtime_json,raw_status_json"
)

JSON_FIELDS = ("usage_json", "runtime_json", "raw_status_json")


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for key in JSON_FIELDS:
        raw = item.pop(key, "{}")
        try:
            item[key.replace("_json", "")] = json.loads(raw) if raw else {}
        except ValueError:
            item[key.replace("_json", "")] = {}
    return item


def get_run(db: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    return _row(db.execute(f"SELECT {RUN_FIELDS} FROM orchestrator_runs WHERE id=?", (run_id,)).fetchone())


def get_by_hermes_run(db: sqlite3.Connection, hermes_run_id: str) -> dict[str, Any] | None:
    return _row(
        db.execute(
            f"SELECT {RUN_FIELDS} FROM orchestrator_runs WHERE run_id=? ORDER BY requested_at DESC LIMIT 1",
            (hermes_run_id,),
        ).fetchone()
    )


def get_by_idempotency(db: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    return _row(
        db.execute(f"SELECT {RUN_FIELDS} FROM orchestrator_runs WHERE idempotency_key=?", (key,)).fetchone()
    )


def list_runs(db: sqlite3.Connection, mission_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        f"SELECT {RUN_FIELDS} FROM orchestrator_runs WHERE mission_id=? ORDER BY requested_at DESC",
        (mission_id,),
    ).fetchall()
    return [item for row in rows if (item := _row(row)) is not None]


def create_run(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    """Crée une ligne de dispatch. La clé d'idempotence garantit l'unicité."""
    rid, stamp = str(uuid.uuid4()), now()
    db.execute(
        """INSERT INTO orchestrator_runs(
            id,mission_id,step_id,orchestrator_id,run_id,session_id,idempotency_key,status,phase,
            replayed_count,requested_at,started_at,finished_at,output,error,usage_json,runtime_json,raw_status_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            rid,
            data["mission_id"],
            data.get("step_id"),
            data.get("orchestrator_id"),
            data.get("run_id", ""),
            data.get("session_id", ""),
            data["idempotency_key"],
            data.get("status", "started"),
            data.get("phase", "dispatching"),
            int(data.get("replayed_count", 0)),
            stamp,
            data.get("started_at"),
            data.get("finished_at"),
            data.get("output", ""),
            data.get("error", ""),
            json.dumps(data.get("usage") or {}, ensure_ascii=False),
            json.dumps(data.get("runtime") or {}, ensure_ascii=False),
            json.dumps(data.get("raw_status") or {}, ensure_ascii=False),
        ),
    )
    db.commit()
    return get_run(db, rid) or {}


def update_run(db: sqlite3.Connection, run_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    if get_run(db, run_id) is None:
        return None
    column_map = {
        "status": "status",
        "phase": "phase",
        "run_id": "run_id",
        "session_id": "session_id",
        "output": "output",
        "error": "error",
        "started_at": "started_at",
        "finished_at": "finished_at",
        "replayed_count": "replayed_count",
    }
    assignments: dict[str, Any] = {}
    for key, column in column_map.items():
        if key in changes:
            assignments[column] = changes[key]
    for key in ("usage", "runtime", "raw_status"):
        if key in changes:
            assignments[f"{key}_json"] = json.dumps(changes[key] or {}, ensure_ascii=False)
    if assignments:
        clause = ", ".join(f"{column}=?" for column in assignments)
        db.execute(
            f"UPDATE orchestrator_runs SET {clause} WHERE id=?",
            (*assignments.values(), run_id),
        )
        db.commit()
    return get_run(db, run_id)
