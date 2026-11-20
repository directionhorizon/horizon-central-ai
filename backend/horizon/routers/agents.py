"""Routes du registre des agents.

Le concept d'agent est générique et vaut pour tous les systèmes d'orchestration.
HORIZON CORE supervise les systèmes ; chaque système garde son agent
orchestrateur (coordinateur) et ses agents spécialisés.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..models import AgentCreate, AgentUpdate
from ..repositories import agents, operations, orchestrators, tools

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("")
def list_agents(
    orchestrator_id: str | None = None, role: str | None = None, status: str | None = None
):
    with connect() as db:
        items = agents.list_agents(db, orchestrator_id=orchestrator_id, role=role, status=status)
    return {"items": items}


@router.post("", status_code=201)
def create_agent(payload: AgentCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        if orchestrators.get_orchestrator(db, payload.orchestrator_id) is None:
            raise HTTPException(404, "Système d'orchestration introuvable.")
        item = agents.create_agent(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="agent.create", target_type="agent",
            target_id=item.get("id"), detail=f"Agent enregistré : {payload.name}",
        )
    return item


@router.get("/{agent_id}")
def read_agent(agent_id: str):
    with connect() as db:
        item = agents.get_agent(db, agent_id)
        if item is None:
            raise HTTPException(404, "Agent introuvable.")
    return item


@router.patch("/{agent_id}")
def update_agent(agent_id: str, payload: AgentUpdate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = agents.update_agent(db, agent_id, payload.model_dump(exclude_none=True))
        if item is None:
            raise HTTPException(404, "Agent introuvable.")
        operations.log(
            db, actor=actor, action="agent.update", target_type="agent",
            target_id=agent_id, detail="Agent modifié.",
        )
    return item


# --- Mains (outils) attribuées à l'agent ------------------------------------

@router.get("/{agent_id}/tools")
def list_agent_tools(agent_id: str):
    with connect() as db:
        if agents.get_agent(db, agent_id) is None:
            raise HTTPException(404, "Agent introuvable.")
        items = tools.list_for_agent(db, agent_id)
    return {"items": items}


@router.post("/{agent_id}/tools/{tool_id}")
def attach_agent_tool(agent_id: str, tool_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        if agents.get_agent(db, agent_id) is None:
            raise HTTPException(404, "Agent introuvable.")
        if tools.get_tool(db, tool_id) is None:
            raise HTTPException(404, "Outil introuvable.")
        tools.attach(db, agent_id, tool_id)
        item = agents.get_agent(db, agent_id)
        operations.log(
            db, actor=actor, action="agent.tool.attach", target_type="agent",
            target_id=agent_id, detail=f"Outil attribué : {tool_id}",
        )
    return item


@router.delete("/{agent_id}/tools/{tool_id}")
def detach_agent_tool(agent_id: str, tool_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        if agents.get_agent(db, agent_id) is None:
            raise HTTPException(404, "Agent introuvable.")
        tools.detach(db, agent_id, tool_id)
        item = agents.get_agent(db, agent_id)
        operations.log(
            db, actor=actor, action="agent.tool.detach", target_type="agent",
            target_id=agent_id, detail=f"Outil retiré : {tool_id}",
        )
    return item
