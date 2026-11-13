"""Routes du moteur HORIZON CORE : planification et routage.

Le cœur ne simule jamais une exécution : soit il produit un plan réel via un
fournisseur vérifié, soit il refuse explicitement avec le statut `no_model`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import core
from ..auth import require_admin
from ..db import connect
from ..repositories import llm as llm_repo
from ..repositories import missions, operations, orchestrators, projects

router = APIRouter(prefix="/api/v1/core", tags=["core"])


class PlanRequest(BaseModel):
    project_id: str = Field(min_length=1)
    request: str = Field(min_length=1, max_length=12000)
    orchestrator_id: str | None = None


@router.get("/route")
def route(capability: str | None = None):
    """Sélectionne un orchestrateur réel parmi les fiches enregistrées."""
    with connect() as db:
        candidates = orchestrators.list_orchestrators(db, status="active")
    chosen = core.select_orchestrator(candidates, capability)
    if chosen is None:
        return {
            "status": "no_orchestrator",
            "capability": capability,
            "detail": "Aucun orchestrateur actif enregistré.",
        }
    return {
        "status": "selected",
        "capability": capability,
        "orchestrator": {
            "id": chosen["id"],
            "name": chosen["name"],
            "health_status": chosen["health_status"],
            "capabilities": [cap["capability_id"] for cap in chosen.get("capabilities", [])],
        },
    }


@router.post("/plan")
async def plan(payload: PlanRequest, actor: str = Depends(require_admin)):
    with connect() as db:
        project = projects.get_project(db, payload.project_id)
        if project is None:
            raise HTTPException(404, "Projet introuvable.")
        candidates = orchestrators.list_orchestrators(db, status="active")
        if payload.orchestrator_id:
            candidates = [item for item in candidates if item["id"] == payload.orchestrator_id]
        provider, model = llm_repo.resolve_for_use(db, payload.orchestrator_id)

    if provider is None or not model:
        with connect() as db:
            operations.log(
                db, actor=actor, action="core.plan", target_type="project",
                target_id=payload.project_id, result="no_model",
                detail="Planification refusée : aucun fournisseur LLM vérifié.",
            )
        return {
            "status": "no_model",
            "detail": "Aucun fournisseur LLM vérifié n'est disponible. Configurez-en un dans /models.",
            "project_id": payload.project_id,
            "orchestrator_id": payload.orchestrator_id,
        }

    try:
        built = await core.build_plan(provider, model, payload.request, candidates, project["name"])
    except core.PlanningError as error:
        with connect() as db:
            operations.log(
                db, actor=actor, action="core.plan", target_type="project",
                target_id=payload.project_id, result="failed", detail=str(error),
            )
        raise HTTPException(502, f"Planification impossible : {error}") from error

    with connect() as db:
        mission = missions.create_mission(
            db,
            {
                "project_id": payload.project_id,
                "title": built["title"],
                "description": built["summary"] or payload.request,
                "status": "planned",
                "priority": "normal",
                "orchestrator_id": payload.orchestrator_id,
            },
        )
        for step in built["steps"]:
            chosen = core.select_orchestrator(candidates, step["capability"])
            missions.add_step(
                db,
                mission["id"],
                {
                    "title": step["title"],
                    "assigned_orchestrator_id": chosen["id"] if chosen else payload.orchestrator_id,
                },
            )
        operations.log(
            db, actor=actor, action="core.plan", target_type="mission",
            target_id=mission["id"], result="success",
            detail=f"Plan créé ({len(built['steps'])} étapes) via {built.get('provider_id')}.",
        )
        stored = missions.get_mission(db, mission["id"])

    return {
        "status": "planned",
        "mission": stored,
        "plan": built,
        "execution": {
            "status": "planned",
            "provider_id": built.get("provider_id"),
            "model_id": built.get("model"),
            "fallback_used": False,
        },
    }
