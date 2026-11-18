"""Universal Integration & Orchestration Manager — registre des adaptateurs.

HORIZON choisit un système d'orchestration par son `kind` ; le registre rend
l'adaptateur correspondant. Aucun orchestrateur n'est codé en dur : ajouter un
système = enregistrer un adaptateur. HORIZON reste le décideur.
"""
from __future__ import annotations

from .base import AdapterError, DispatchResult, HealthResult, OrchestratorAdapter

_ADAPTERS: dict[str, OrchestratorAdapter] = {}


def register(adapter: OrchestratorAdapter) -> OrchestratorAdapter:
    """Enregistre un branchement. Le dernier enregistré pour un `kind` gagne."""
    _ADAPTERS[adapter.kind] = adapter
    return adapter


def get_adapter(kind: str) -> OrchestratorAdapter | None:
    """Retourne l'adaptateur d'un type de système, ou None si inconnu."""
    return _ADAPTERS.get((kind or "").strip().lower())


def available_kinds() -> list[dict[str, str]]:
    """Liste des types de systèmes pris en charge (kind + libellé lisible)."""
    return [{"kind": adapter.kind, "label": adapter.label} for adapter in _ADAPTERS.values()]


def _load_builtins() -> None:
    from .hermes_adapter import HermesAdapter
    from .native_adapter import NativeHorizonAdapter

    register(HermesAdapter())
    register(NativeHorizonAdapter())


_load_builtins()

__all__ = [
    "AdapterError",
    "DispatchResult",
    "HealthResult",
    "OrchestratorAdapter",
    "register",
    "get_adapter",
    "available_kinds",
]
