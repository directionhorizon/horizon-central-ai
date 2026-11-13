"""Routes des projets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..models import ProjectCreate, ProjectUpdate
from ..repositories import operations, projects, sync
from ..schema import DEFAULT_PROJECT_ID

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("")
def list_projects(status: str | None = None):
    with connect() as db:
        items = projects.list_projects(db, status=status)
        for item in items:
            item["mission_count"] = projects.count_missions(db, item["id"])
            item["orchestrator_count"] = projects.count_orchestrators(db, item["id"])
    return {"items": items, "default_project_id": DEFAULT_PROJECT_ID}


@router.post("", status_code=201)
def create_project(payload: ProjectCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = projects.create_project(db, payload.name, payload.description, payload.status)
        operations.log(
            db, actor=actor, action="project.create", target_type="project",
            target_id=item["id"], detail=f"Projet créé : {item['name']}",
        )
        sync.enqueue(db, "projects", item["id"], "create", item)
    return item


@router.get("/{project_id}")
def read_project(project_id: str):
    with connect() as db:
        item = projects.get_project(db, project_id)
        if item is None:
            raise HTTPException(404, "Projet introuvable.")
        item["mission_count"] = projects.count_missions(db, project_id)
        item["orchestrator_count"] = projects.count_orchestrators(db, project_id)
        orchestrators_rows = db.execute(
            """SELECT o.id,o.name,o.status,o.health_status,op.role
               FROM orchestrator_projects op
               JOIN orchestrators o ON o.id = op.orchestrator_id
               WHERE op.project_id=? ORDER BY o.name""",
            (project_id,),
        ).fetchall()
        missions_rows = db.execute(
            """SELECT id,title,status,priority,orchestrator_id,created_at,updated_at
               FROM missions WHERE project_id=? ORDER BY created_at DESC""",
            (project_id,),
        ).fetchall()
    item["orchestrators"] = [dict(row) for row in orchestrators_rows]
    item["missions"] = [dict(row) for row in missions_rows]
    return item


@router.patch("/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = projects.update_project(db, project_id, payload.model_dump(exclude_none=True))
        if item is None:
            raise HTTPException(404, "Projet introuvable.")
        operations.log(
            db, actor=actor, action="project.update", target_type="project",
            target_id=project_id, detail="Projet modifié.",
        )
        sync.enqueue(db, "projects", project_id, "update", item)
    return item


@router.delete("/{project_id}")
def archive_project(project_id: str, actor: str = Depends(require_admin)):
    """Archivage logique : le projet et ses données sont conservés."""
    with connect() as db:
        item = projects.archive_project(db, project_id)
        if item is None:
            raise HTTPException(404, "Projet introuvable.")
        operations.log(
            db, actor=actor, action="project.archive", target_type="project",
            target_id=project_id, detail="Projet archivé (aucune suppression).",
        )
        sync.enqueue(db, "projects", project_id, "delete", item)
    return item
