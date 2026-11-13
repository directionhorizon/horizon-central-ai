"""HORIZON CORE — planification et routage.

Le cœur transforme une demande en mission structurée :

1. sélectionne un orchestrateur réellement enregistré et disponible ;
2. demande un plan au fournisseur LLM configuré ;
3. valide strictement la réponse (JSON + schéma) ;
4. persiste la mission et ses étapes.

Sans fournisseur LLM vérifié, aucune mission n'est créée : le cœur renvoie un
refus explicite (`no_model`) au lieu de fabriquer un plan.
"""
from __future__ import annotations

import json
from typing import Any

from . import llm

PLAN_SYSTEM_PROMPT = """Tu es le planificateur de HORIZON CENTRAL AI.
Tu réponds UNIQUEMENT par un objet JSON valide, sans texte autour, au format :
{"title": "...", "summary": "...", "steps": [{"title": "...", "capability": "..."}]}
Contraintes :
- entre 2 et 12 étapes ;
- chaque étape a un titre court et une capacité technique en minuscules
  (ex. "code", "document", "analyse", "recherche", "automatisation") ;
- aucune étape ne doit prétendre avoir été exécutée ;
- le plan décrit ce qui doit être fait, pas un résultat.
"""


class PlanningError(RuntimeError):
    """Erreur de planification, avec message exploitable."""


def _extract_json(text: str) -> dict[str, Any]:
    """Extrait un objet JSON d'une réponse pouvant contenir des délimiteurs."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise PlanningError("Le fournisseur n'a pas renvoyé d'objet JSON exploitable.")
    try:
        payload = json.loads(cleaned[start : end + 1])
    except ValueError as error:
        raise PlanningError("JSON invalide renvoyé par le fournisseur.") from error
    if not isinstance(payload, dict):
        raise PlanningError("La réponse du fournisseur n'est pas un objet JSON.")
    return payload


def validate_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Valide et normalise un plan. Lève `PlanningError` si invalide."""
    title = str(payload.get("title") or "").strip()
    if not title:
        raise PlanningError("Plan sans titre.")
    steps_raw = payload.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise PlanningError("Plan sans étape.")
    if len(steps_raw) > 12:
        raise PlanningError("Plan trop long (12 étapes maximum).")
    steps: list[dict[str, str]] = []
    for index, raw in enumerate(steps_raw):
        if not isinstance(raw, dict):
            raise PlanningError(f"Étape {index + 1} invalide.")
        step_title = str(raw.get("title") or "").strip()
        if not step_title:
            raise PlanningError(f"Étape {index + 1} sans titre.")
        capability = str(raw.get("capability") or "general").strip().lower() or "general"
        steps.append({"title": step_title[:300], "capability": capability[:60]})
    return {
        "title": title[:200],
        "summary": str(payload.get("summary") or "")[:4000],
        "steps": steps,
    }


def select_orchestrator(
    orchestrators: list[dict[str, Any]], capability: str | None = None
) -> dict[str, Any] | None:
    """Choisit l'orchestrateur le plus adapté parmi les fiches réelles.

    Critères, dans l'ordre : capacité demandée, statut actif, santé vérifiée,
    puis nombre de capacités déclarées.
    """
    candidates = [item for item in orchestrators if item.get("status") == "active"]
    if not candidates:
        return None
    if capability:
        matching = [
            item
            for item in candidates
            if any(cap.get("capability_id") == capability for cap in item.get("capabilities", []))
        ]
        if matching:
            candidates = matching
    rank = {"available": 0, "degraded": 1, "unverified": 2, "unavailable": 3}
    candidates.sort(
        key=lambda item: (
            rank.get(item.get("health_status", "unverified"), 4),
            -len(item.get("capabilities", [])),
        )
    )
    return candidates[0]


async def build_plan(
    provider_row: dict[str, Any],
    model: str,
    request_text: str,
    orchestrators: list[dict[str, Any]],
    project_name: str,
) -> dict[str, Any]:
    """Demande un plan au fournisseur, le valide, et renvoie le plan normalisé."""
    capability_catalog = sorted(
        {
            cap.get("capability_id")
            for item in orchestrators
            for cap in item.get("capabilities", [])
            if cap.get("capability_id")
        }
    )
    context = (
        f"Projet : {project_name}\n"
        f"Orchestrateurs disponibles : {[o.get('name') for o in orchestrators]}\n"
        f"Capacités déclarées : {capability_catalog or 'aucune'}\n"
        f"Demande : {request_text}"
    )
    try:
        result = await llm.chat(
            provider_row,
            [
                {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            model=model,
            temperature=0.1,
        )
    except llm.LLMError as error:
        raise PlanningError(str(error)) from error

    plan = validate_plan(_extract_json(result["content"]))
    plan["provider_id"] = result.get("provider_id")
    plan["model"] = result.get("model")
    plan["usage"] = result.get("usage")
    return plan
