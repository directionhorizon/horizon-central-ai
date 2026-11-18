"""Branchement Hermes : adapte l'API server Hermes au contrat d'adaptateur.

Premier branchement de l'UOIM. Il ne fait qu'envelopper le client `horizon.hermes`
sans jamais exposer ni journaliser de secret.
"""
from __future__ import annotations

from typing import Any

from .. import hermes
from .base import AdapterError, DispatchResult, HealthResult, OrchestratorAdapter


def _wrap(error: hermes.HermesError) -> AdapterError:
    return AdapterError(str(error), status_code=error.status_code, code=error.code)


class HermesAdapter(OrchestratorAdapter):
    """Système d'orchestration Hermes."""

    kind = "hermes"
    label = "Hermes"

    def _config(self, row: dict[str, Any]) -> hermes.HermesConfig:
        try:
            return hermes.build_config(row)
        except hermes.HermesError as error:
            raise _wrap(error) from error

    async def health(self, row: dict[str, Any]) -> HealthResult:
        config = self._config(row)
        result = await hermes.check_health(config)
        return HealthResult(
            status=str(result.get("status") or "unavailable"),
            detail=str(result.get("detail") or ""),
            version=str(result.get("version") or ""),
            target=f"{config.base_url}/health",
        )

    async def dispatch(
        self,
        row: dict[str, Any],
        *,
        mission: dict[str, Any],
        step: dict[str, Any] | None,
        idempotency_key: str,
    ) -> DispatchResult:
        config = self._config(row)
        try:
            result = await hermes.dispatch(
                config, mission=mission, step=step, idempotency_key=idempotency_key
            )
        except hermes.HermesError as error:
            raise _wrap(error) from error
        return DispatchResult(
            run_id=str(result.get("run_id") or ""),
            status=str(result.get("status") or "started"),
            replayed=bool(result.get("replayed")),
        )

    async def status(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        config = self._config(row)
        try:
            return await hermes.get_status(config, run_ref)
        except hermes.HermesError as error:
            raise _wrap(error) from error

    def map_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        mapped = hermes.map_status(payload)
        mapped["provider_status"] = mapped.pop("hermes_status", "unknown")
        return mapped

    async def stop(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        config = self._config(row)
        try:
            return await hermes.stop(config, run_ref)
        except hermes.HermesError as error:
            raise _wrap(error) from error

    async def approval(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, choice: str
    ) -> dict[str, Any]:
        config = self._config(row)
        try:
            return await hermes.approval(config, run_ref, request_id, generation, choice)
        except hermes.HermesError as error:
            raise _wrap(error) from error

    async def clarify(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, answer: str
    ) -> dict[str, Any]:
        config = self._config(row)
        try:
            return await hermes.clarify(config, run_ref, request_id, generation, answer)
        except hermes.HermesError as error:
            raise _wrap(error) from error
