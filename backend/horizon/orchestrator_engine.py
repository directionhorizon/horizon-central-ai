"""Moteur d'orchestration multi-agents (générique).

Un système natif (`kind = horizon`) peut activer l'orchestration multi-agents par sa
configuration : ``{"orchestration": "multi-agent", "max_steps": 6}``. Sinon, le
moteur natif mono-agent est utilisé (comportement inchangé).

Déroulé, générique pour tout système :
1. **Planifier** : le fournisseur LLM découpe la mission en étapes et désigne, pour
   chaque étape, un agent **du système** (validé ; jamais inventé) ;
2. **Router** : chaque étape est affectée à cet agent ;
3. **Exécuter** : chaque étape est exécutée par l'agent choisi (moteur natif) ;
4. **Suivre** : étapes (`mission_steps.assigned_agent_id`) et exécutions
   (`orchestrator_runs.agent_id`) sont persistées, par agent ;
5. **Consolider** : l'agent coordinateur produit la synthèse finale (statut honnête).

Aucune donnée n'est inventée : sans fournisseur LLM, une erreur explicite est levée.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from . import llm
from . import native_engine
from .db import now
from .repositories import agents as agents_repo
from .repositories import missions as missions_repo
from .repositories import runs as runs_repo

MAX_STEPS_HARD = 12


class OrchestrationError(RuntimeError):
    """Erreur d'orchestration lisible, sans secret."""


def _config(system: dict[str, Any]) -> dict[str, Any]:
    config = system.get("config")
    if isinstance(config, dict):
        return config
    if isinstance(config, str) and config.strip():
        try:
            parsed = json.loads(config)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def is_enabled(system: dict[str, Any]) -> bool:
    """Vrai si le système demande l'orchestration multi-agents."""
    return str(_config(system).get("orchestration") or "").strip().lower() == "multi-agent"


def _max_steps(system: dict[str, Any]) -> int:
    try:
        value = int(_config(system).get("max_steps") or 6)
    except (TypeError, ValueError):
        value = 6
    return max(2, min(value, MAX_STEPS_HARD))


PLAN_PROMPT = """Tu es le planificateur de HORIZON CENTRAL AI pour le système « {system} ».

Agents disponibles (identifiant | nom | rôle | spécialité) :
{agents}

Découpe la mission en {min_steps} à {max_steps} étapes utiles.
Réponds UNIQUEMENT par un objet JSON, sans texte autour :
{{"steps": [{{"title": "...", "agent_id": "..."}}]}}

Règles :
- "agent_id" doit être EXACTEMENT l'un des identifiants ci-dessus ;
- chaque étape décrit ce qui doit être fait, pas un résultat ;
- n'invente aucun agent, outil, source ni ressource ;
- ne prétends jamais qu'une action a été exécutée.
"""

FINAL_PROMPT = """Tu es l'agent coordinateur du système « {system} ».

Mission : {title}
Description : {description}

Contributions des agents :
{contributions}

Produis le résultat final : synthèse, points clés, contradictions éventuelles,
limites et prochaines étapes. Distingue explicitement fait, estimation et hypothèse.
N'invente aucune donnée et ne prétends pas avoir réalisé une action externe.
"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.strip().startswith("```")
        ).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise OrchestrationError("Le planificateur n'a pas renvoyé de JSON exploitable.")
    try:
        payload = json.loads(cleaned[start : end + 1])
    except ValueError as error:
        raise OrchestrationError("Plan JSON invalide renvoyé par le fournisseur.") from error
    if not isinstance(payload, dict):
        raise OrchestrationError("Le plan n'est pas un objet JSON.")
    return payload


def _agent_catalog(agents: list[dict[str, Any]]) -> str:
    lines = []
    for agent in agents:
        spec = " ".join((agent.get("description") or "").split())[:180]
        lines.append(f"- {agent['id']} | {agent.get('name')} | {agent.get('role')} | {spec}")
    return "\n".join(lines)


def _select_steps(payload: dict[str, Any], agents: list[dict[str, Any]], limit: int) -> list[dict[str, str]]:
    """Valide les étapes du plan : titre + agent appartenant réellement au système."""
    by_id = {agent["id"]: agent for agent in agents}
    coordinator = next((a for a in agents if a.get("role") == "orchestrator"), agents[0])
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise OrchestrationError("Plan sans étape exploitable.")
    steps: list[dict[str, str]] = []
    for raw in raw_steps[:limit]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        agent_id = str(raw.get("agent_id") or "").strip()
        if agent_id not in by_id:
            agent_id = coordinator["id"]
        steps.append({"title": title[:300], "agent_id": agent_id})
    if not steps:
        raise OrchestrationError("Plan sans étape valide.")
    return steps


async def _chat(provider: dict[str, Any], system_prompt: str, user_text: str) -> dict[str, Any]:
    try:
        return await llm.chat(
            provider,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0.2,
        )
    except llm.LLMError as error:
        raise OrchestrationError(str(error)) from error


def _merge_usage(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Additionne les compteurs d'usage numériques, sans inventer de clé."""
    merged: dict[str, Any] = {}
    for item in items:
        for key, value in (item or {}).items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                merged[key] = merged.get(key, 0) + value
    return merged


def _contributions_text(outputs: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(outputs, start=1):
        body = (item.get("output") or "").strip()
        if not body:
            body = f"(aucune sortie : {item.get('error') or 'vide'})"
        blocks.append(f"[{index}] Étape « {item['step']} » — agent {item['agent']}\n{body}")
    return "\n\n".join(blocks) if blocks else "(aucune contribution)"


async def plan_steps(
    provider: dict[str, Any], system: dict[str, Any], mission: dict[str, Any], agents: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Décompose la mission et route chaque étape vers un agent du système."""
    limit = _max_steps(system)
    prompt = PLAN_PROMPT.format(
        system=system.get("name") or system.get("id"),
        agents=_agent_catalog(agents),
        min_steps=2,
        max_steps=limit,
    )
    request = (
        f"Mission : {mission.get('title')}\n"
        f"Description : {mission.get('description') or '(aucune)'}"
    )
    result = await _chat(provider, prompt, request)
    return _select_steps(_extract_json(result.get("content") or ""), agents, limit)


async def consolidate(
    provider: dict[str, Any],
    system: dict[str, Any],
    mission: dict[str, Any],
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    """L'agent coordinateur produit la synthèse finale des contributions."""
    prompt = FINAL_PROMPT.format(
        system=system.get("name") or system.get("id"),
        title=mission.get("title"),
        description=mission.get("description") or "(aucune)",
        contributions=_contributions_text(outputs),
    )
    result = await _chat(provider, prompt, "Produis le résultat final consolidé.")
    return {
        "content": result.get("content") or "",
        "usage": result.get("usage") or {},
        "model": result.get("model"),
        "provider": result.get("provider_name"),
    }


async def execute(db: sqlite3.Connection, system: dict[str, Any], mission: dict[str, Any]) -> dict[str, Any]:
    """Exécute une mission en multi-agents : plan -> agents -> consolidation.

    Lève `OrchestrationError` avec un message explicite si un prérequis manque
    (aucun agent actif, aucun fournisseur configuré, plan inexploitable).
    """
    agents = agents_repo.list_agents(db, orchestrator_id=system["id"], status="active")
    if not agents:
        raise OrchestrationError("Ce système n'a aucun agent actif : orchestration impossible.")
    coordinator = next((a for a in agents if a.get("role") == "orchestrator"), agents[0])
    try:
        provider = native_engine.choose_provider(db)
    except native_engine.NativeEngineError as error:
        raise OrchestrationError(str(error)) from error

    steps = await plan_steps(provider, system, mission, agents)
    for index, step in enumerate(steps):
        missions_repo.add_step(
            db,
            mission["id"],
            {
                "title": step["title"],
                "position": index,
                "assigned_orchestrator_id": system["id"],
                "assigned_agent_id": step["agent_id"],
            },
        )
    fresh = missions_repo.get_mission(db, mission["id"]) or {}
    rows = [row for row in (fresh.get("steps") or []) if (row.get("status") or "pending") == "pending"]

    outputs: list[dict[str, Any]] = []
    usage_items: list[dict[str, Any]] = [{"steps": len(rows)}]
    failures = 0
    for row in rows:
        agent = next((a for a in agents if a["id"] == row.get("assigned_agent_id")), coordinator)
        missions_repo.update_step(db, mission["id"], row["id"], {"status": "running"})
        run = runs_repo.create_run(
            db,
            {
                "mission_id": mission["id"],
                "step_id": row["id"],
                "orchestrator_id": system["id"],
                "agent_id": agent["id"],
                "idempotency_key": f"step-{row['id']}",
                "status": "running",
                "phase": "executing",
                "started_at": now(),
            },
        )
        try:
            result = await native_engine.run_mission(
                db, system, mission, {"id": row["id"], "title": row["title"]}, agent["id"]
            )
        except (native_engine.NativeEngineError, OrchestrationError) as error:
            message = str(error)[:2000]
            runs_repo.update_run(
                db, run["id"], {"status": "failed", "phase": "error", "error": message, "finished_at": now()}
            )
            missions_repo.update_step(db, mission["id"], row["id"], {"status": "failed", "error": message})
            outputs.append(
                {"step": row["title"], "agent": agent["name"], "agent_id": agent["id"], "error": message}
            )
            failures += 1
            continue
        usage_items.append(result.get("usage") or {})
        runs_repo.update_run(
            db,
            run["id"],
            {
                "run_id": result.get("run_id") or "",
                "status": "completed",
                "phase": "completed",
                "output": result.get("output") or "",
                "usage": result.get("usage") or {},
                "runtime": result.get("runtime") or {},
                "finished_at": now(),
            },
        )
        missions_repo.update_step(db, mission["id"], row["id"], {"status": "completed"})
        outputs.append(
            {
                "step": row["title"],
                "agent": agent["name"],
                "agent_id": agent["id"],
                "output": result.get("output") or "",
            }
        )

    final = await consolidate(provider, system, mission, outputs)
    usage_items.append(final.get("usage") or {})
    return {
        "run_id": f"native-orch-{uuid.uuid4()}",
        "status": "completed" if failures == 0 else "completed_with_errors",
        "output": final["content"],
        "usage": _merge_usage(usage_items),
        "runtime": {
            "engine": "horizon-orchestrator",
            "mode": "multi-agent",
            "agent": coordinator["name"],
            "provider": final.get("provider"),
            "model": final.get("model"),
            "steps": len(rows),
            "failures": failures,
            "agents": sorted({item["agent"] for item in outputs}),
            "detail": [
                {"step": item["step"], "agent": item["agent"], "ok": "error" not in item}
                for item in outputs
            ],
        },
        "steps": outputs,
    }

