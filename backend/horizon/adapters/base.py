"""Contrat commun des adaptateurs d'orchestration (UOIM).

Un adaptateur traduit le langage d'HORIZON (missions, exécutions, contrôles)
vers celui d'un système d'orchestration concret. HORIZON reste le décideur :
il choisit le système et l'adaptateur se contente d'exécuter la demande.

Règles :
- aucun secret n'est stocké ni journalisé : seuls des noms de variables
  d'environnement circulent ;
- aucune réponse n'est inventée : un échec lève une erreur explicite.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class AdapterError(RuntimeError):
    """Erreur d'adaptateur, message lisible et sans secret."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class DispatchResult:
    """Résultat neutre d'un envoi de mission à un système d'orchestration."""

    run_id: str
    status: str
    replayed: bool = False


@dataclass(frozen=True)
class HealthResult:
    """Résultat neutre d'une vérification de disponibilité."""

    status: str
    detail: str = ""
    version: str = ""
    target: str = ""


class OrchestratorAdapter(ABC):
    """Interface que tout branchement d'orchestration doit implémenter."""

    #: Identifiant technique du type de système (colonne `orchestrators.kind`).
    kind: str = ""
    #: Libellé lisible affiché dans l'interface (jamais technique).
    label: str = ""

    @abstractmethod
    async def health(self, row: dict[str, Any]) -> HealthResult:
        ...

    @abstractmethod
    async def dispatch(
        self,
        row: dict[str, Any],
        *,
        mission: dict[str, Any],
        step: dict[str, Any] | None,
        idempotency_key: str,
    ) -> DispatchResult:
        ...

    @abstractmethod
    async def status(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def map_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def stop(self, row: dict[str, Any], run_ref: str) -> dict[str, Any]:
        ...

    @abstractmethod
    async def approval(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, choice: str
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def clarify(
        self, row: dict[str, Any], run_ref: str, request_id: str, generation: int, answer: str
    ) -> dict[str, Any]:
        ...

    @staticmethod
    def new_idempotency_key() -> str:
        return f"horizon-run-{uuid.uuid4()}"

    @staticmethod
    def mission_session_id(mission_id: str) -> str:
        return f"horizon-mission-{mission_id}"
