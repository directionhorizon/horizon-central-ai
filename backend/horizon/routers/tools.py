"""Routes du catalogue des mains (outils) des agents.

Les mains sont des capacités déclarées, organisées par familles. Elles ne sont
jamais codées en dur : le catalogue est la source de vérité, et une main n'est
« prête » que lorsqu'elle est réellement branchée.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..models import ToolRun
from ..repositories import operations, tools
from .. import tool_runtime

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("")
def list_tools(family: str | None = None, status: str | None = None, channel: str | None = None):
    with connect() as db:
        items = tools.list_tools(db, family=family, status=status, channel=channel)
        families = tools.list_families(db)
    for item in items:
        item["executable"] = tool_runtime.is_executable(item["id"])
    return {"items": items, "families": families}


@router.get("/families")
def list_families():
    with connect() as db:
        return {"items": tools.list_families(db)}


@router.get("/{tool_id}")
def read_tool(tool_id: str):
    with connect() as db:
        item = tools.get_tool(db, tool_id)
        if item is None:
            raise HTTPException(404, "Outil introuvable.")
    return item


@router.post("/{tool_id}/status")
def set_tool_status(tool_id: str, status: str, actor: str = Depends(require_admin)):
    if status not in ("planned", "ready", "disabled"):
        raise HTTPException(400, "Statut invalide.")
    with connect() as db:
        item = tools.set_status(db, tool_id, status)
        if item is None:
            raise HTTPException(404, "Outil introuvable.")
        operations.log(
            db, actor=actor, action="tool.status", target_type="tool",
            target_id=tool_id, detail=f"Statut outil : {status}",
        )
    return item


@router.post("/{tool_id}/run")
async def run_tool(tool_id: str, payload: ToolRun, actor: str = Depends(require_admin)):
    """Exécute une main branchée. Une main non branchée est refusée honnêtement."""
    with connect() as db:
        tool = tools.get_tool(db, tool_id)
        if tool is None:
            raise HTTPException(404, "Outil introuvable.")
        if tool.get("status") == "disabled":
            raise HTTPException(409, "Cet outil est désactivé.")
        if not tool_runtime.is_executable(tool_id):
            raise HTTPException(
                501,
                f"Cette main n'est pas encore branchée (mode : {tool.get('channel') or 'inconnu'}).",
            )
        if payload.agent_id:
            granted = tools.list_for_agent(db, payload.agent_id)
            if not any(item["id"] == tool_id for item in granted):
                raise HTTPException(403, "Cet agent ne dispose pas de cette main.")
        try:
            result = await tool_runtime.run_tool(db, tool, payload.params)
        except tool_runtime.ToolError as error:
            raise HTTPException(400, str(error)) from error
        operations.log(
            db, actor=actor, action="tool.run", target_type="tool",
            target_id=tool_id, detail="Exécution d'une main.",
        )
    return {"tool_id": tool_id, "result": result}
