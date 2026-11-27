"""Branchement natif HORIZON : le moteur d'exécution interne de HORIZON.

Ce branchement exécute réellement les missions dans HORIZON, sans dépendre d'un
logiciel externe : l'agent orchestrateur du système prend la mission en charge
via le fournisseur LLM configuré. Aucune disponibilité n'est inventée : sans
modèle configuré, l'exécution échoue avec un message explicite.
"""
from __future__ import annotations

from typing import Any

from .. import native_engine, orchestrator_engine
from ..db import connect, now
from ..repositories import runs
from .base import AdapterError, DispatchResult, HealthResult, OrchestratorAdapter


class NativeHorizonAdapter(OrchestratorAdapter):
    """Branchement pour un système d'orchestration interne à HORIZON."""

    kind = "horizon"
    label = "HORIZON (interne)"

    async def health(self, row: dict[str, Any]) -> HealthResult:
        return HealthResult(
            status="available",
            detail="Moteur d'exécution natif HORIZON actif.",
            target="horizon://native",
        )

    async def dispatch(
        self,
        row: dict[str, Any],
        *,
        mission: dict[str, Any],
        step: dict[str, Any] | None,
        idempotency_key: str,
    ) -> DispatchResult:
        with connect() as db:
            try:
                if orchestrator_engine.is_enabled(row):
                    # Moteur multi-agents : plan -> agents -> consolidation.
                    result = await orchestrator_engine.execute(db, row, mission)
                else:
                    result = await native_engine.run_mission(db, row, mission, step)
            except orchestrator_engine.OrchestrationError as error:
                raise AdapterError(str(error)) from error
            except native_engine.NativeEngineError as error:
                raise AdapterError(str(error)) from error
        # Persiste le résultat dans la ligne de dispatch (retrouvée par clé d'idempotence).
        with connect() as db:
            run = runs.get_by_idempotency(db, idempotency_key)
            if run is not None:
                runs.update_run(
                    db,
                    run["id"],
                    {
                        "run_id": result["run_id"],
                        "status": "completed",
                        "phase": "completed",
                        "output": result["output"],
                        "usage": result["usage"],
                        "runtime": result["runtime"],
                        "finished_at": now(),
                    },
                )
        return DispatchResult(run_id=result["run_id"], status="completed", replayed=False)

    async def status(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        with connect() as db:
            run = runs.get_by_hermes_run(db, run_ref)
        if run is None:
            return {"status": "unknown", "output": "", "error": ""}
        return {
            "status": run.get("status") or "unknown",
            "output": run.get("output") or "",
            "error": run.get("error") or "",
            "usage": run.get("usage") or {},
            "runtime": run.get("runtime") or {},
        }

    def map_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        status = str(payload.get("status") or "unknown")
        if status == "completed":
            mission_status, step_status, terminal = "completed", "completed", True
        elif status == "failed":
            mission_status, step_status, terminal = "failed", "failed", True
        elif status == "cancelled":
            mission_status, step_status, terminal = "cancelled", "skipped", True
        else:
            mission_status, step_status, terminal = "running", "running", False
        return {
            "provider_status": status,
            "mission_status": mission_status,
            "step_status": step_status,
            "checkpoint": None,
            "recoverable": False,
            "output": payload.get("output") or "",
            "error": payload.get("error") or "",
            "usage": payload.get("usage") or {},
            "runtime": payload.get("runtime") or {},
            "pending_controls": None,
            "terminal": terminal,
            "raw_status": payload,
        }

    async def stop(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        raise AdapterError(
            "Le moteur natif exécute les missions de façon synchrone : l'arrêt n'est pas applicable."
        )

    async def approval(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, choice: str
    ) -> dict[str, Any]:
        raise AdapterError("Aucune approbation en attente pour le moteur natif.")

    async def clarify(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, answer: str
    ) -> dict[str, Any]:
        raise AdapterError("Aucune clarification en attente pour le moteur natif.")
