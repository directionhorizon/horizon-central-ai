"""Planificateur minimal : exécute les tâches planifiées arrivées à échéance.

Une tâche planifiée désigne une main branchée et ses paramètres. Le
planificateur ne fabrique rien : il exécute réellement la main, puis marque la
tâche `done` ou `failed`.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from . import tool_runtime
from .db import connect, now
from .repositories import tools

INTERVAL_S = 15


async def run_loop() -> None:
    while True:
        try:
            await tick()
        except Exception:  # pragma: no cover - le planificateur ne doit jamais s'arrêter
            pass
        await asyncio.sleep(INTERVAL_S)


async def tick() -> int:
    """Exécute les tâches dues et renvoie leur nombre."""
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM scheduled_tasks WHERE status='pending' AND run_at<=? ORDER BY run_at",
            (now(),),
        ).fetchall()
    tasks = [dict(row) for row in rows]
    for task in tasks:
        await _execute(task)
    return len(tasks)


async def _execute(task: dict[str, Any]) -> None:
    with connect() as db:
        tool = tools.get_tool(db, task["tool_id"])
        if tool is None:
            _mark(task["id"], "failed", "Outil introuvable.")
            return
        try:
            params = json.loads(task["params_json"] or "{}")
        except ValueError:
            params = {}
        try:
            result = await tool_runtime.run_tool(db, tool, params)
            _mark(task["id"], "done", json.dumps(result, ensure_ascii=False)[:4000])
        except tool_runtime.ToolError as error:
            _mark(task["id"], "failed", str(error)[:4000])


def _mark(task_id: str, status: str, result: str) -> None:
    with connect() as db:
        db.execute(
            "UPDATE scheduled_tasks SET status=?, executed_at=?, result=? WHERE id=?",
            (status, now(), result, task_id),
        )
        db.commit()


def list_tasks(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM scheduled_tasks ORDER BY run_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
