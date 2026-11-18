"""Routes du registre des orchestrateurs."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..hermes import build_config, check_health as check_hermes_health
from ..models import (
    CapabilityCreate,
    OrchestratorCreate,
    OrchestratorModelSelection,
    OrchestratorProjectLink,
    OrchestratorUpdate,
)
from ..repositories import operations, orchestrators, projects, sync

router = APIRouter(prefix="/api/v1/orchestrators", tags=["orchestrators"])


@router.get("")
def list_orchestrators(status: str | None = None, project_id: str | None = None):
    with connect() as db:
        items = orchestrators.list_orchestrators(db, status=status, project_id=project_id)
    return {"items": items}


@router.post("", status_code=201)
def create_orchestrator(payload: OrchestratorCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = orchestrators.create_orchestrator(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="orchestrator.create", target_type="orchestrator",
            target_id=item.get("id"), detail=f"Orchestrateur enregistré : {payload.name}",
        )
        sync.enqueue(db, "orchestrators", item.get("id") or "", "create", item)
    return item


@router.get("/{orchestrator_id}")
def read_orchestrator(orchestrator_id: str):
    with connect() as db:
        item = orchestrators.get_orchestrator(db, orchestrator_id)
        if item is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
    return item


@router.patch("/{orchestrator_id}")
def update_orchestrator(
    orchestrator_id: str, payload: OrchestratorUpdate, actor: str = Depends(require_admin)
):
    with connect() as db:
        item = orchestrators.update_orchestrator(db, orchestrator_id, payload.model_dump(exclude_none=True))
        if item is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        operations.log(
            db, actor=actor, action="orchestrator.update", target_type="orchestrator",
            target_id=orchestrator_id, detail="Orchestrateur modifié.",
        )
        sync.enqueue(db, "orchestrators", orchestrator_id, "update", item)
    return item


@router.delete("/{orchestrator_id}")
def disable_orchestrator(orchestrator_id: str, actor: str = Depends(require_admin)):
    """Désactivation logique : la fiche est conservée."""
    with connect() as db:
        item = orchestrators.disable_orchestrator(db, orchestrator_id)
        if item is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        operations.log(
            db, actor=actor, action="orchestrator.disable", target_type="orchestrator",
            target_id=orchestrator_id, detail="Orchestrateur désactivé (aucune suppression).",
        )
        sync.enqueue(db, "orchestrators", orchestrator_id, "delete", item)
    return item


@router.post("/{orchestrator_id}/capabilities")
def add_capability(
    orchestrator_id: str, payload: CapabilityCreate, actor: str = Depends(require_admin)
):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        item = orchestrators.add_capability(db, orchestrator_id, payload.model_dump())
        operations.log(
            db, actor=actor, action="orchestrator.capability.add", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Capacité ajoutée : {payload.capability_id}",
        )
    return item


@router.delete("/{orchestrator_id}/capabilities/{capability_id}")
def remove_capability(orchestrator_id: str, capability_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        item = orchestrators.remove_capability(db, orchestrator_id, capability_id)
        operations.log(
            db, actor=actor, action="orchestrator.capability.remove", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Capacité retirée : {capability_id}",
        )
    return item


@router.post("/{orchestrator_id}/projects")
def link_project(orchestrator_id: str, payload: OrchestratorProjectLink, actor: str = Depends(require_admin)):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        if projects.get_project(db, payload.project_id) is None:
            raise HTTPException(404, "Projet introuvable.")
        orchestrators.link_project(db, orchestrator_id, payload.project_id, payload.role)
        item = orchestrators.get_orchestrator(db, orchestrator_id)
        operations.log(
            db, actor=actor, action="orchestrator.project.link", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Projet associé : {payload.project_id}",
        )
    return item


@router.delete("/{orchestrator_id}/projects/{project_id}")
def unlink_project(orchestrator_id: str, project_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        orchestrators.unlink_project(db, orchestrator_id, project_id)
        item = orchestrators.get_orchestrator(db, orchestrator_id)
        operations.log(
            db, actor=actor, action="orchestrator.project.unlink", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Projet dissocié : {project_id}",
        )
    return item


@router.put("/{orchestrator_id}/model")
def set_model(orchestrator_id: str, payload: OrchestratorModelSelection, actor: str = Depends(require_admin)):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Orchestrateur introuvable.")
        item = orchestrators.set_model_selection(db, orchestrator_id, payload.provider_id, payload.model)
        operations.log(
            db, actor=actor, action="orchestrator.model.set", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Modèle associé : {payload.provider_id}/{payload.model}",
        )
    return item


@router.post("/{orchestrator_id}/check")
async def check_orchestrator(orchestrator_id: str, actor: str = Depends(require_admin)):
    """Teste réellement la disponibilité de l'endpoint déclaré.

    Hermes utilise son adaptateur dédié : le statut, la version et le détail
    viennent de `/health`, sans jamais lire ni journaliser le secret.
    Sans endpoint configuré, la vérification reste `unverified` : aucune
    disponibilité n'est inventée.
    """
    with connect() as db:
        item = orchestrators.get_orchestrator(db, orchestrator_id)
        if item is None:
            raise HTTPException(404, "Orchestrateur introuvable.")

    endpoint = (item.get("endpoint") or "").strip()
    if not endpoint:
        with connect() as db:
            orchestrators.set_health(db, orchestrator_id, "unverified")
        return {
            "id": orchestrator_id,
            "health_status": "unverified",
            "detail": "Aucun endpoint déclaré : vérification impossible.",
        }

    is_hermes = str(item.get("kind") or "").strip().lower() == "hermes"
    if is_hermes:
        config = build_config(item)
        health = await check_hermes_health(config)
        health_status = str(health["status"])
        detail = str(health["detail"])
        version = str(health.get("version") or "")
        target = f"{config.base_url}/health"
        with connect() as db:
            orchestrators.set_health(db, orchestrator_id, health_status)
            if version and version != (item.get("version") or ""):
                orchestrators.update_orchestrator(db, orchestrator_id, {"version": version})
            operations.log(
                db, actor=actor, action="orchestrator.check", target_type="orchestrator",
                target_id=orchestrator_id, result=health_status,
                detail=f"{detail} Version : {version or 'inconnue'}.",
            )
        return {
            "id": orchestrator_id,
            "health_status": health_status,
            "detail": detail,
            "target": target,
            "version": version,
        }

    base = endpoint.rstrip("/")
    target = base if base.endswith("/health") else f"{base}/health"
    health_status, detail = "unavailable", ""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(target)
        health_status = "available" if response.status_code < 400 else "degraded"
        detail = f"HTTP {response.status_code} sur {target}."
    except httpx.HTTPError as error:
        detail = f"Échec réseau : {type(error).__name__}."

    with connect() as db:
        orchestrators.set_health(db, orchestrator_id, health_status)
        operations.log(
            db, actor=actor, action="orchestrator.check", target_type="orchestrator",
            target_id=orchestrator_id, result=health_status, detail=detail,
        )
    return {"id": orchestrator_id, "health_status": health_status, "detail": detail, "target": target}