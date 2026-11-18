"""Branchement natif HORIZON : systèmes d'orchestration créés dans HORIZON.

Ce branchement est volontairement honnête : tant que le moteur d'exécution
interne n'est pas activé, il ne fabrique aucune disponibilité. Il existe pour
que les futurs systèmes créés directement dans HORIZON disposent déjà de leur
place dans le registre, sans coder d'orchestrateur en dur.
"""
from __future__ import annotations

from typing import Any

from .base import AdapterError, DispatchResult, HealthResult, OrchestratorAdapter

_NOT_READY = (
    "Le moteur d'exécution interne d'HORIZON n'est pas encore activé : "
    "aucune exécution n'est lancée."
)


class NativeHorizonAdapter(OrchestratorAdapter):
    """Branchement pour un système d'orchestration interne à HORIZON."""

    kind = "horizon"
    label = "HORIZON (interne)"

    async def health(self, row: dict[str, Any]) -> HealthResult:
        return HealthResult(status="unverified", detail=_NOT_READY, target="")

    async def dispatch(
        self,
        row: dict[str, Any],
        *,
        mission: dict[str, Any],
        step: dict[str, Any] | None,
        idempotency_key: str,
    ) -> DispatchResult:
        raise AdapterError(_NOT_READY)

    async def status(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        raise AdapterError(_NOT_READY)

    def map_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider_status": "unknown",
            "mission_status": "paused",
            "step_status": "running",
            "checkpoint": "unknown_execution",
            "recoverable": False,
            "output": "",
            "error": _NOT_READY,
            "usage": {},
            "runtime": {},
            "pending_controls": None,
            "terminal": False,
        }

    async def stop(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        raise AdapterError(_NOT_READY)

    async def approval(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, choice: str
    ) -> dict[str, Any]:
        raise AdapterError(_NOT_READY)

    async def clarify(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, answer: str
    ) -> dict[str, Any]:
        raise AdapterError(_NOT_READY)
