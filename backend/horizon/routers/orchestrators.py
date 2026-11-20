"""Routes du registre des orchestrateurs."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ..adapters import AdapterError, available_kinds, get_adapter
from ..auth import require_admin
from ..db import connect
from ..models import (
    CapabilityCreate,
    OrchestratorCreate,
    OrchestratorModelSelection,
    OrchestratorProjectLink,
    OrchestratorUpdate,
    SkillAttach,
)
from ..repositories import operations, orchestrators, projects, skills, sync

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


@router.get("/kinds")
def list_supported_kinds():
    """Types de systèmes d'orchestration pris en charge (Universal Manager).

    L'interface s'en sert pour proposer les branchements disponibles lorsqu'on
    enregistre un nouveau système. Aucun type n'est imposé : la liste est
    construite depuis le registre d'adaptateurs.
    """
    return {"items": available_kinds()}


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

    L'adaptateur du système (UOIM) fournit le statut, la version et le détail,
    sans jamais lire ni journaliser de secret. Sans endpoint configuré, la
    vérification reste `unverified` : aucune disponibilité n'est inventée.
    """
    with connect() as db:
        item = orchestrators.get_orchestrator(db, orchestrator_id)
        if item is None:
            raise HTTPException(404, "Orchestrateur introuvable.")

    adapter = get_adapter(str(item.get("kind") or ""))
    if adapter is not None:
        try:
            health = await adapter.health(item)
            health_status = health.status
            detail = health.detail
            version = health.version
            target = health.target
        except AdapterError as error:
            health_status, detail, version, target = "unavailable", str(error), "", ""
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

    endpoint = (item.get("endpoint") or "").strip()
    if not endpoint:
        with connect() as db:
            orchestrators.set_health(db, orchestrator_id, "unverified")
        return {
            "id": orchestrator_id,
            "health_status": "unverified",
            "detail": "Aucun endpoint déclaré : vérification impossible.",
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


# --- Compétences associées (bibliothèque de skills) -------------------------

@router.get("/{orchestrator_id}/skills")
def list_orchestrator_skills(orchestrator_id: str):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Système d'orchestration introuvable.")
        items = skills.list_for_orchestrator(db, orchestrator_id)
    return {"items": items}


@router.post("/{orchestrator_id}/skills")
def attach_orchestrator_skill(
    orchestrator_id: str, payload: SkillAttach, actor: str = Depends(require_admin)
):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Système d'orchestration introuvable.")
        if skills.get_skill(db, payload.skill_id) is None:
            raise HTTPException(404, "Compétence introuvable.")
        skills.attach_skill(db, orchestrator_id, payload.skill_id)
        operations.log(
            db, actor=actor, action="orchestrator.skill.attach", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Compétence associée : {payload.skill_id}",
        )
        item = orchestrators.get_orchestrator(db, orchestrator_id)
    return item


@router.delete("/{orchestrator_id}/skills/{skill_id}")
def detach_orchestrator_skill(
    orchestrator_id: str, skill_id: str, actor: str = Depends(require_admin)
):
    with connect() as db:
        if orchestrators.get_orchestrator(db, orchestrator_id) is None:
            raise HTTPException(404, "Système d'orchestration introuvable.")
        skills.detach_skill(db, orchestrator_id, skill_id)
        operations.log(
            db, actor=actor, action="orchestrator.skill.detach", target_type="orchestrator",
            target_id=orchestrator_id, detail=f"Compétence retirée : {skill_id}",
        )
        item = orchestrators.get_orchestrator(db, orchestrator_id)
    return item