"""Dépôt des serveurs MCP enregistrés (pont universel d'outils)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..db import now


def _decode(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    raw = item.pop("args_json", "[]")
    try:
        item["args"] = json.loads(raw) if raw else []
    except ValueError:
        item["args"] = []
    item["enabled"] = bool(item.get("enabled"))
    return item


def list_servers(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute("SELECT * FROM mcp_servers ORDER BY name").fetchall()
    return [_decode(row) for row in rows]


def get_server(db: sqlite3.Connection, server_id: str) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM mcp_servers WHERE id=?", (server_id,)).fetchone()
    return _decode(row) if row else None


def create_server(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    sid, stamp = str(uuid.uuid4()), now()
    db.execute(
        """INSERT INTO mcp_servers(id,name,command,args_json,enabled,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?)""",
        (
            sid,
            data["name"],
            data["command"],
            json.dumps(data.get("args") or [], ensure_ascii=False),
            1 if data.get("enabled", True) else 0,
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_server(db, sid) or {}
