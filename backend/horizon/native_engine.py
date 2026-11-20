"""Moteur d'exécution natif de HORIZON.

Exécute une mission directement dans HORIZON, sans dépendre d'un logiciel
externe : l'agent orchestrateur du système choisi prend la mission en charge,
raisonne via le fournisseur LLM configuré et produit un résultat vérifiable.

Aucune réponse n'est fabriquée : sans fournisseur LLM configuré, une erreur
explicite est levée (`NativeEngineError`), jamais un résultat inventé.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from . import llm
from .repositories import agents as agents_repo
from .repositories import llm as llm_repo


class NativeEngineError(RuntimeError):
    """Erreur du moteur natif, message lisible et sans secret."""


def _build_prompt(
    agent: dict[str, Any], mission: dict[str, Any], step: dict[str, Any] | None
) -> str:
    lines = [
        f"Mission : {mission.get('title', '')}",
        f"Description : {mission.get('description', '')}",
        f"Priorité : {mission.get('priority', 'normal')}",
    ]
    if step:
        lines.append(f"Étape à traiter : {step.get('title', '')}")
    lines.append("")
    lines.append(
        "Traite la mission et livre un résultat clair, structuré et vérifiable. "
        "Signale explicitement tout bloquant ou toute information manquante."
    )
    return "\n".join(lines)


def choose_provider(db: sqlite3.Connection) -> dict[str, Any]:
    """Renvoie le premier fournisseur LLM réellement configuré (URL + modèle)."""
    for row in llm_repo.list_providers(db):
        if (row.get("base_url") or "").strip() and (row.get("default_model") or "").strip():
            return row
    raise NativeEngineError(
        "Aucun fournisseur LLM configuré : enregistrez un modèle (local ou en ligne) "
        "avant de lancer une mission native."
    )


def pick_agent(db: sqlite3.Connection, orchestrator_id: str) -> dict[str, Any]:
    """Renvoie l'agent coordinateur du système, ou à défaut le premier agent actif."""
    coordinators = agents_repo.list_agents(
        db, orchestrator_id=orchestrator_id, role="orchestrator", status="active"
    )
    if coordinators:
        return coordinators[0]
    actives = agents_repo.list_agents(db, orchestrator_id=orchestrator_id, status="active")
    if actives:
        return actives[0]
    raise NativeEngineError("Ce système d'orchestration n'a aucun agent actif pour exécuter la mission.")


async def run_mission(
    db: sqlite3.Connection,
    orchestrator: dict[str, Any],
    mission: dict[str, Any],
    step: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Exécute une mission via l'agent coordinateur (ou un agent désigné)."""
    if agent_id:
        agent = agents_repo.get_agent(db, agent_id)
        if agent is None:
            raise NativeEngineError("Agent introuvable pour cette délégation.")
    else:
        agent = pick_agent(db, orchestrator["id"])
    provider = choose_provider(db)
    system_prompt = agent.get("spec") or (
        "Tu es un agent de HORIZON CENTRAL AI. Livre un résultat clair et vérifiable."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _build_prompt(agent, mission, step)},
    ]
    try:
        result = await llm.chat(provider, messages, temperature=0.2)
    except llm.LLMError as error:
        raise NativeEngineError(str(error)) from error
    return {
        "run_id": f"native-{uuid.uuid4()}",
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "provider_id": result.get("provider_id"),
        "model": result.get("model"),
        "output": result.get("content", ""),
        "usage": result.get("usage") or {},
        "runtime": {
            "engine": "horizon-native",
            "agent": agent["name"],
            "provider": result.get("provider_name"),
            "model": result.get("model"),
        },
    }
