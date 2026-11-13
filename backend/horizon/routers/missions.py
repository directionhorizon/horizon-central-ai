"""Routes des missions, étapes et points de contrôle."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..models import CheckpointCreate, MissionCreate, MissionStepCreate, MissionStepUpdate, MissionUpdate
from ..repositories import missions, operations, projects, sync

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])


@router.get("")
def list_missions(
    project_id: str | None = None, status: str | None = None, orchestrator_id: str | None = None
):
    with connect() as db:
        items = missions.list_missions(
            db, project_id=project_id, status=status, orchestrator_id=orchestrator_id
        )
    return {"items": items}


@router.post("", status_code=201)
def create_mission(payload: MissionCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        if projects.get_project(db, payload.project_id) is None:
            raise HTTPException(404, "Projet introuvable.")
        item = missions.create_mission(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="mission.create", target_type="mission",
            target_id=item.get("id"), detail=f"Mission créée : {payload.title}",
        )
        sync.enqueue(db, "missions", item.get("id") or "", "create", item)
    return item


@router.get("/{mission_id}")
def read_mission(mission_id: str):
    with connect() as db:
        item = missions.get_mission(db, mission_id)
        if item is None:
            raise HTTPException(404, "Mission introuvable.")
    return item


@router.patch("/{mission_id}")
def update_mission(mission_id: str, payload: MissionUpdate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = missions.update_mission(db, mission_id, payload.model_dump(exclude_unset=True))
        if item is None:
            raise HTTPException(404, "Mission introuvable.")
        operations.log(
            db, actor=actor, action="mission.update", target_type="mission",
            target_id=mission_id, detail="Mission modifiée.",
        )
        sync.enqueue(db, "missions", mission_id, "update", item)
    return item


@router.post("/{mission_id}/steps", status_code=201)
def add_step(mission_id: str, payload: MissionStepCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = missions.add_step(db, mission_id, payload.model_dump())
        if item is None:
            raise HTTPException(404, "Mission introuvable.")
        operations.log(
            db, actor=actor, action="mission.step.add", target_type="mission",
            target_id=mission_id, detail=f"Étape ajoutée : {payload.title}",
        )
    return item


@router.patch("/{mission_id}/steps/{step_id}")
def update_step(
    mission_id: str, step_id: str, payload: MissionStepUpdate, actor: str = Depends(require_admin)
):
    with connect() as db:
        item = missions.update_step(db, mission_id, step_id, payload.model_dump(exclude_unset=True))
        if item is None:
            raise HTTPException(404, "Étape introuvable pour cette mission.")
        operations.log(
            db, actor=actor, action="mission.step.update", target_type="mission",
            target_id=mission_id, detail=f"Étape mise à jour : {step_id}",
        )
    return item


@router.get("/{mission_id}/checkpoints")
def list_checkpoints(mission_id: str):
    with connect() as db:
        if missions.get_mission(db, mission_id) is None:
            raise HTTPException(404, "Mission introuvable.")
        items = missions.list_checkpoints(db, mission_id)
    return {"items": items}


@router.post("/{mission_id}/checkpoints", status_code=201)
def add_checkpoint(mission_id: str, payload: CheckpointCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = missions.add_checkpoint(db, mission_id, payload.model_dump())
        if item is None:
            raise HTTPException(404, "Mission introuvable.")
        operations.log(
            db, actor=actor, action="mission.checkpoint.add", target_type="mission",
            target_id=mission_id, detail=f"Point de contrôle : {payload.label}",
        )
    return item
