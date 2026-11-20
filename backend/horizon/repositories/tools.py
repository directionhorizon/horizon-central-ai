"""Dépôt du catalogue des mains (outils) et des attributions aux agents.

Les mains sont déclarées dans un catalogue versionné (fichiers JSON) puis
stockées ici. Chaque agent reçoit un sous-ensemble : un agent ne dispose que
des outils qui lui sont explicitement attribués.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..db import now

FIELDS = "id,family,name,description,risk,channel,status,created_at,updated_at"


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def list_tools(
    db: sqlite3.Connection,
    *,
    family: str | None = None,
    status: str | None = None,
    channel: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if family:
        clauses.append("family=?")
        params.append(family)
    if status:
        clauses.append("status=?")
        params.append(status)
    if channel:
        clauses.append("channel=?")
        params.append(channel)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"SELECT {FIELDS} FROM tools{where} ORDER BY family, name", params
    ).fetchall()
    return [dict(row) for row in rows]


def get_tool(db: sqlite3.Connection, tool_id: str) -> dict[str, Any] | None:
    return _row(db.execute(f"SELECT {FIELDS} FROM tools WHERE id=?", (tool_id,)).fetchone())


def list_families(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT family, COUNT(*) AS count FROM tools GROUP BY family ORDER BY family"
    ).fetchall()
    return [dict(row) for row in rows]


def set_status(db: sqlite3.Connection, tool_id: str, status: str) -> dict[str, Any] | None:
    if get_tool(db, tool_id) is None:
        return None
    db.execute("UPDATE tools SET status=?, updated_at=? WHERE id=?", (status, now(), tool_id))
    db.commit()
    return get_tool(db, tool_id)


def list_for_agent(db: sqlite3.Connection, agent_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        """SELECT t.id,t.family,t.name,t.description,t.risk,t.channel,t.status,
                  t.created_at,t.updated_at
           FROM agent_tools at
           JOIN tools t ON t.id = at.tool_id
           WHERE at.agent_id=?
           ORDER BY t.family, t.name""",
        (agent_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def attach(db: sqlite3.Connection, agent_id: str, tool_id: str) -> None:
    db.execute(
        "INSERT OR IGNORE INTO agent_tools(agent_id,tool_id,created_at) VALUES(?,?,?)",
        (agent_id, tool_id, now()),
    )
    db.commit()


def detach(db: sqlite3.Connection, agent_id: str, tool_id: str) -> None:
    db.execute("DELETE FROM agent_tools WHERE agent_id=? AND tool_id=?", (agent_id, tool_id))
    db.commit()
