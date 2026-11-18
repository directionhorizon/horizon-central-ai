"""Routes des missions, étapes, points de contrôle et exécutions Hermes."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from .. import hermes
from ..auth import require_admin
from ..db import connect, now
from ..models import (
    ApprovalRequest, CheckpointCreate, ClarifyRequest, DispatchRequest,
    MissionCreate, MissionStepCreate, MissionStepUpdate, MissionUpdate,
)
from ..repositories import missions, operations, orchestrators, projects, runs, sync
from ..schema import HERMES_SEED

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])

NON_TERMINAL = {
    "queued", "started", "running", "waiting_for_approval", "stopping", "dispatching", "unknown"
}


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


# --- Exécution réelle CORE ↔ Hermes ----------------------------------------

def _safe_status_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Ne conserve que des références : jamais d'output brut ni d'aperçu d'outil."""
    pending = payload.get("pending_controls")
    safe_pending: list[dict[str, Any]] = []
    if isinstance(pending, list):
        for item in pending[:20]:
            if isinstance(item, dict):
                safe_pending.append(
                    {
                        key: item[key]
                        for key in ("request_id", "prompt_id", "execution_generation", "kind", "type")
                        if key in item
                    }
                )
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    return {
        "status": payload.get("status"),
        "model": payload.get("model"),
        "turn_exit_reason": payload.get("turn_exit_reason"),
        "pending_controls": safe_pending,
        "runtime": {
            key: runtime[key]
            for key in ("provider", "model", "route_source")
            if key in runtime
        },
    }


def _config_for(db, orchestrator_id: str) -> hermes.HermesConfig:
    row = orchestrators.get_orchestrator(db, orchestrator_id)
    if row is None:
        raise HTTPException(404, "Orchestrateur d'exécution introuvable.")
    if row.get("status") == "disabled":
        raise HTTPException(409, "Cet orchestrateur est désactivé.")
    return hermes.build_config(row)


def _find_step(mission: dict[str, Any], step_id: str | None) -> dict[str, Any] | None:
    if not step_id:
        return None
    for step in mission.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise HTTPException(404, "Étape introuvable pour cette mission.")


def _checkpoint_once(db, mission_id: str, label: str, state: dict[str, Any]) -> None:
    for item in missions.list_checkpoints(db, mission_id):
        if item.get("label") == label and (item.get("state") or {}).get("run_id") == state.get("run_id"):
            return
    missions.add_checkpoint(db, mission_id, {"label": label, "state": state})


def _apply_mapping(db, run: dict[str, Any], mapped: dict[str, Any]) -> dict[str, Any]:
    """Persiste le statut Hermes dans la ligne de run, la mission et l'étape."""
    updates: dict[str, Any] = {
        "status": mapped["hermes_status"],
        "output": mapped["output"],
        "error": mapped["error"],
        "usage": mapped["usage"],
        "runtime": mapped["runtime"],
        "raw_status": mapped["raw_status"],
        "phase": mapped["mission_status"],
    }
    if mapped["terminal"]:
        updates["finished_at"] = now()
    updated = runs.update_run(db, run["id"], updates) or run

    missions.update_mission(db, run["mission_id"], {"status": mapped["mission_status"]})
    if run.get("step_id"):
        missions.update_step(
            db, run["mission_id"], run["step_id"],
            {"status": mapped["step_status"], "error": mapped["error"]},
        )
    checkpoint = mapped["checkpoint"]
    if checkpoint:
        _checkpoint_once(
            db, run["mission_id"], checkpoint,
            {"run_id": run.get("run_id", ""), "status": mapped["hermes_status"]},
        )
    return updated


def _mapping_from_payload(payload: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    mapped = hermes.map_status(payload)
    mapped["raw_status"] = snapshot
    return mapped


def _require_run(db, mission_id: str, run_id: str) -> dict[str, Any]:
    if missions.get_mission(db, mission_id) is None:
        raise HTTPException(404, "Mission introuvable.")
    run = runs.get_run(db, run_id)
    if run is None or run.get("mission_id") != mission_id:
        raise HTTPException(404, "Exécution introuvable pour cette mission.")
    return run


async def _refresh(db, run: dict[str, Any]) -> dict[str, Any]:
    """Interroge Hermes et met à jour la ligne locale. Retourne la ligne à jour."""
    config = _config_for(db, run.get("orchestrator_id") or HERMES_SEED["id"])
    payload = await hermes.get_status(config, run["run_id"])
    snapshot = _safe_status_snapshot(payload)
    mapped = _mapping_from_payload(payload, snapshot)
    return _apply_mapping(db, run, mapped)


@router.post("/{mission_id}/dispatch", status_code=202)
async def dispatch_mission(
    mission_id: str, payload: DispatchRequest, actor: str = Depends(require_admin)
):
    """Lance réellement la mission via Hermes. Idempotent : une exécution active par mission."""
    with connect() as db:
        mission = missions.get_mission(db, mission_id)
        if mission is None:
            raise HTTPException(404, "Mission introuvable.")
        step = _find_step(mission, payload.step_id)

        # Idempotence applicative : une seule exécution non terminale par mission.
        for existing in runs.list_runs(db, mission_id):
            if existing.get("status") in NON_TERMINAL and existing.get("run_id"):
                return {"run": existing, "replayed": True, "detail": "Exécution déjà en cours."}

        orchestrator_id = payload.orchestrator_id or mission.get("orchestrator_id") or HERMES_SEED["id"]
        config = _config_for(db, orchestrator_id)
        key = hermes.new_idempotency_key()
        session_id = hermes.mission_session_id(mission_id)
        run = runs.create_run(
            db,
            {
                "mission_id": mission_id,
                "step_id": step.get("id") if step else None,
                "orchestrator_id": orchestrator_id,
                "session_id": session_id,
                "idempotency_key": key,
                "status": "dispatching",
                "phase": "dispatching",
            },
        )

    try:
        result = await hermes.dispatch(config, mission=mission, step=step, idempotency_key=key)
    except (hermes.HermesError, httpx.HTTPError) as error:
        message = str(error)
        with connect() as db:
            runs.update_run(
                db,
                run["id"],
                {
                    "status": "failed",
                    "phase": "error",
                    "error": message[:4000],
                    "finished_at": now(),
                },
            )
            missions.update_mission(db, mission_id, {"status": "failed"})
            operations.log(
                db, actor=actor, action="mission.dispatch", target_type="mission",
                target_id=mission_id, result="error", detail=f"Échec dispatch Hermes : {message[:300]}",
            )
        raise HTTPException(502, f"Exécution impossible : {message}")

    with connect() as db:
        updated = runs.update_run(
            db,
            run["id"],
            {
                "run_id": result["run_id"],
                "status": result["status"],
                "phase": "running" if result["status"] in NON_TERMINAL else result["status"],
                "replayed_count": 1 if result["replayed"] else 0,
                "started_at": now(),
            },
        )
        missions.update_mission(db, mission_id, {"status": "running"})
        if step:
            missions.update_step(db, mission_id, step["id"], {"status": "running"})
        operations.log(
            db, actor=actor, action="mission.dispatch", target_type="mission",
            target_id=mission_id, detail=f"Dispatch Hermes {result['run_id'][:40]}{' (rejoué)' if result['replayed'] else ''}",
        )
        sync.enqueue(db, "missions", mission_id, "update", {"status": "running"})
    return {"run": updated, "replayed": bool(result["replayed"]), "detail": "Exécution lancée."}


@router.get("/{mission_id}/runs")
def list_runs_route(mission_id: str):
    with connect() as db:
        if missions.get_mission(db, mission_id) is None:
            raise HTTPException(404, "Mission introuvable.")
        items = runs.list_runs(db, mission_id)
    return {"items": items}


@router.get("/{mission_id}/runs/{run_id}")
async def get_run_route(mission_id: str, run_id: str, refresh: bool = True):
    """Retourne l'exécution ; `refresh=1` interroge Hermes pour l'état courant."""
    with connect() as db:
        run = _require_run(db, mission_id, run_id)
        if not refresh or not run.get("run_id"):
            return run
        return await _refresh(db, run)


@router.post("/{mission_id}/runs/{run_id}/stop")
async def stop_run_route(
    mission_id: str, run_id: str, actor: str = Depends(require_admin)
):
    with connect() as db:
        run = _require_run(db, mission_id, run_id)
        config = _config_for(db, run.get("orchestrator_id") or HERMES_SEED["id"])
    try:
        response = await hermes.stop(config, run["run_id"])
    except (hermes.HermesError, httpx.HTTPError) as error:
        raise HTTPException(502, f"Arrêt impossible : {error}")
    with connect() as db:
        _checkpoint_once(
            db, mission_id, "stop_requested",
            {"run_id": run.get("run_id", ""), "status": str(response.get("status", ""))},
        )
        operations.log(
            db, actor=actor, action="mission.run.stop", target_type="orchestrator_run",
            target_id=run_id, detail="Arrêt demandé à Hermes.",
        )
    return {"status": "stopping", "run": run}


def _pending_control(payload: dict[str, Any], request_id: str, generation: int) -> dict[str, Any]:
    """Vérifie que l'identité de la demande correspond à un contrôle en attente."""
    raw = payload.get("raw_status") or {}
    controls = raw.get("pending_controls") or []
    for control in controls if isinstance(controls, list) else []:
        if not isinstance(control, dict):
            continue
        cid = str(control.get("request_id") or control.get("prompt_id") or "")
        gen = control.get("execution_generation")
        if cid == request_id and (gen is None or int(gen) == generation):
            return control
    raise HTTPException(
        409,
        "Demande de contrôle introuvable ou génération obsolète : rafraîchissez le statut avant de réessayer.",
    )


async def _control_route(
    mission_id: str,
    run_id: str,
    request_id: str,
    generation: int,
    action: str,
    actor: str,
    answer: str = "",
):
    with connect() as db:
        run = _require_run(db, mission_id, run_id)
        current = await _refresh(db, run)
        config = _config_for(db, run.get("orchestrator_id") or HERMES_SEED["id"])
    _pending_control(current, request_id, generation)
    try:
        if action == "approval_once":
            result = await hermes.approval(config, run["run_id"], request_id, generation, "once")
        elif action == "approval_deny":
            result = await hermes.approval(config, run["run_id"], request_id, generation, "deny")
        else:
            result = await hermes.clarify(config, run["run_id"], request_id, generation, answer)
    except (hermes.HermesError, httpx.HTTPError) as error:
        raise HTTPException(502, f"Contrôle impossible : {error}")
    with connect() as db:
        operations.log(
            db, actor=actor, action=f"mission.run.{action}", target_type="orchestrator_run",
            target_id=run_id, detail=f"Contrôle {action} transmis à Hermes.",
        )
    return {"status": "accepted", "response": result}


@router.post("/{mission_id}/runs/{run_id}/approval")
async def approval_route(
    mission_id: str, run_id: str, payload: ApprovalRequest, actor: str = Depends(require_admin)
):
    action = "approval_once" if payload.choice == "once" else "approval_deny"
    return await _control_route(
        mission_id, run_id, payload.request_id, payload.execution_generation, action, actor
    )


@router.post("/{mission_id}/runs/{run_id}/clarify")
async def clarify_route(
    mission_id: str, run_id: str, payload: ClarifyRequest, actor: str = Depends(require_admin)
):
    return await _control_route(
        mission_id, run_id, payload.request_id, payload.execution_generation,
        "clarify", actor, answer=payload.answer,
    )
