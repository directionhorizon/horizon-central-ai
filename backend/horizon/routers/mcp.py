"""Routes des serveurs MCP enregistrés."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import require_admin
from ..db import connect
from ..models import MCPServerCreate
from ..repositories import mcp, operations

router = APIRouter(prefix="/api/v1/mcp/servers", tags=["mcp"])


@router.get("")
def list_servers():
    with connect() as db:
        return {"items": mcp.list_servers(db)}


@router.post("", status_code=201)
def create_server(payload: MCPServerCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = mcp.create_server(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="mcp.create", target_type="mcp_server",
            target_id=item.get("id"), detail=f"Serveur MCP : {payload.name}",
        )
    return item
