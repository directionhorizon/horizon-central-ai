"""Routes du catalogue des mains (outils) des agents.

Les mains sont des capacités déclarées, organisées par familles. Elles ne sont
jamais codées en dur : le catalogue est la source de vérité, et une main n'est
« prête » que lorsqu'elle est réellement branchée.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..repositories import operations, tools

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("")
def list_tools(family: str | None = None, status: str | None = None, channel: str | None = None):
    with connect() as db:
        items = tools.list_tools(db, family=family, status=status, channel=channel)
        families = tools.list_families(db)
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
