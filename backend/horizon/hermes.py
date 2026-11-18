"""Adaptateur de l'API server Hermes (orchestrateur d'exécution pilote).

Principes (contrat CORE ↔ Hermes v1.0) :
- le secret n'est jamais lu depuis la base : seul le NOM de la variable
  d'environnement est stocké (`config.api_key_env`) ;
- chaque dispatch porte une clé d'idempotence UUIDv4 préfixée `horizon-run-` ;
- en P0, le listener par défaut est utilisé : base `http://127.0.0.1:8642`,
  routes `/v1/...`, profil `default` ;
- aucune réponse n'est fabriquée : en cas d'échec, une `HermesError`
  explicite et non sensible est levée ;
- aucunaperçu brut d'outil ni secret n'est journalisé.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_ENDPOINT = "http://127.0.0.1:8642"
DEFAULT_TIMEOUT_S = 30.0
MAX_ATTEMPTS = 3
RETRYABLE_STATUS = {429, 503}

INSTRUCTIONS = (
    "Tu es Hermes, orchestrateur d'exécution pour HORIZON CENTRAL AI. "
    "Réponds en français. Produis un livrable structuré : objectif, actions "
    "réalisées, résultats, bloquants, prochaines étapes. N'exécute aucun "
    "paiement sans validation humaine explicite. Si une information manque, "
    "signale-la au lieu d'inventer."
)

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "interrupted", "unknown"}


class HermesError(RuntimeError):
    """Erreur Hermes, avec un message lisible et sans secret."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class HermesConfig:
    endpoint: str
    api_key_env: str
    profile: str

    @property
    def base_url(self) -> str:
        return self.endpoint.strip().rstrip("/")

    @property
    def api_key(self) -> str:
        name = self.api_key_env.strip()
        value = os.getenv(name, "").strip() if name else ""
        if not value:
            raise HermesError(
                f"Secret Hermes absent : définissez la variable d'environnement {name or '(non configurée)'}."
            )
        return value

    @property
    def run_prefix(self) -> str:
        """Préfixe de route : listener par défaut en P0."""
        return "/v1"


def build_config(row: dict[str, Any]) -> HermesConfig:
    """Construit la configuration d'appel depuis une ligne `orchestrators`."""
    raw_config = row.get("config") or row.get("config_json") or "{}"
    if isinstance(raw_config, str):
        try:
            config = json.loads(raw_config) if raw_config.strip() else {}
        except ValueError:
            config = {}
    else:
        config = dict(raw_config)
    return HermesConfig(
        endpoint=str(row.get("endpoint") or DEFAULT_ENDPOINT),
        api_key_env=str(config.get("api_key_env") or "HERMES_API_SERVER_KEY"),
        profile=str(config.get("profile") or "default"),
    )


def new_idempotency_key() -> str:
    return f"horizon-run-{uuid.uuid4()}"


def mission_session_id(mission_id: str) -> str:
    return f"horizon-mission-{mission_id}"


def format_mission_input(mission: dict[str, Any], step: dict[str, Any] | None = None) -> str:
    """Formate une mission/étape en texte, sans jamais inclure de secret."""
    lines = [
        "Mission HORIZON",
        f"- mission_id: {mission.get('id', '')}",
        f"- titre: {mission.get('title', '')}",
    ]
    if step:
        lines.append(f"- step_id: {step.get('id', '')}")
        lines.append(f"- étape: {step.get('title', '')}")
    lines.append(f"- priorité: {mission.get('priority', 'normal')}")
    lines.extend(
        [
            "",
            "Description:",
            str(mission.get("description") or "(aucune description)"),
            "",
            "Livrable attendu:",
            "Objectif, actions réalisées, résultats, bloquants, prochaines étapes.",
            "",
            "Contraintes:",
            "- répondre en français;",
            "- ne pas effectuer de paiement sans validation humaine;",
            "- signaler explicitement tout bloquant.",
        ]
    )
    return "\n".join(lines)


def _headers(config: HermesConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _error_from_response(response: httpx.Response) -> HermesError:
    """Extrait un message d'erreur non sensible d'une réponse Hermes."""
    code = ""
    detail = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                code = str(err.get("code") or "")
                detail = str(err.get("message") or "")
            elif isinstance(err, str):
                detail = err
            code = code or str(payload.get("code") or "")
            detail = detail or str(payload.get("detail") or payload.get("message") or "")
    except ValueError:
        pass
    detail = detail[:300]
    messages = {
        400: "Requête invalide envoyée à Hermes.",
        401: "Authentification Hermes refusée : vérifiez la clé configurée.",
        403: "Accès Hermes refusé : vérifiez la configuration du listener.",
        404: "Exécution Hermes introuvable.",
        409: "Conflit Hermes : l'action demandée n'a pas été acceptée.",
        429: "Hermes temporairement surchargé.",
        503: "Hermes temporairement indisponible.",
    }
    base = messages.get(response.status_code, f"Erreur Hermes (HTTP {response.status_code}).")
    if code:
        base += f" Code : {code}."
    if detail and code not in detail:
        base += f" {detail}"
    return HermesError(base, status_code=response.status_code, code=code)


async def check_health(config: HermesConfig) -> dict[str, Any]:
    """Teste réellement `GET /health`. Renvoie un état honnête."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{config.base_url}/health")
    except httpx.HTTPError as error:
        return {
            "status": "unavailable",
            "detail": f"Échec réseau : {type(error).__name__}.",
            "version": "",
        }
    if response.status_code >= 400:
        return {"status": "unavailable", "detail": f"HTTP {response.status_code} sur /health.", "version": ""}
    try:
        payload = response.json()
    except ValueError:
        return {"status": "degraded", "detail": "Réponse /health illisible.", "version": ""}
    status = "available" if payload.get("status") == "ok" else "degraded"
    return {
        "status": status,
        "detail": f"Hermes {payload.get('version', 'version inconnue')} joignable.",
        "version": str(payload.get("version") or ""),
    }


async def dispatch(
    config: HermesConfig,
    *,
    mission: dict[str, Any],
    step: dict[str, Any] | None,
    idempotency_key: str,
) -> dict[str, Any]:
    """Crée un run Hermes. Renvoie run_id, statut initial et rejeu."""
    body = {
        "session_id": mission_session_id(str(mission.get("id", ""))),
        "instructions": INSTRUCTIONS,
        "input": format_mission_input(mission, step),
    }
    headers = _headers(config)
    headers["Idempotency-Key"] = idempotency_key
    url = f"{config.base_url}{config.run_prefix}/runs"

    last_error: HermesError | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
                response = await client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as error:
            last_error = HermesError("Délai dépassé lors de l'envoi à Hermes.") 
            setattr(last_error, "__cause__", error)
            if attempt == MAX_ATTEMPTS - 1:
                raise last_error
            continue
        except httpx.HTTPError as error:
            raise HermesError(f"Échec réseau : {type(error).__name__}.") from error

        if response.status_code == 202:
            try:
                payload = response.json()
            except ValueError as error:
                raise HermesError("Réponse Hermes illisible (JSON invalide).") from error
            run_id = str(payload.get("run_id") or "")
            if not run_id:
                raise HermesError("Réponse Hermes sans run_id.")
            return {
                "run_id": run_id,
                "status": str(payload.get("status") or "started"),
                "replayed": bool(payload.get("replayed") or response.headers.get("Idempotency-Replayed") == "true"),
                "request_body": body,
            }

        error = _error_from_response(response)
        if response.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS - 1:
            last_error = error
            continue
        raise error
    raise last_error or HermesError("Échec d'envoi à Hermes.")


async def get_status(config: HermesConfig, run_id: str) -> dict[str, Any]:
    """Interroge `GET /v1/runs/{run_id}` et renvoie le statut normalisé."""
    url = f"{config.base_url}{config.run_prefix}/runs/{run_id}"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
            response = await client.get(url, headers=_headers(config))
    except httpx.HTTPError as error:
        raise HermesError(f"Échec réseau : {type(error).__name__}.") from error
    if response.status_code >= 400:
        raise _error_from_response(response)
    try:
        payload = response.json()
    except ValueError as error:
        raise HermesError("Réponse de statut Hermes illisible.") from error
    if not isinstance(payload, dict):
        raise HermesError("Réponse de statut Hermes inattendue.")
    return payload


async def stop(config: HermesConfig, run_id: str) -> dict[str, Any]:
    url = f"{config.base_url}{config.run_prefix}/runs/{run_id}/stop"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
            response = await client.post(url, headers=_headers(config))
    except httpx.HTTPError as error:
        raise HermesError(f"Échec réseau : {type(error).__name__}.") from error
    if response.status_code >= 400:
        raise _error_from_response(response)
    try:
        payload = response.json()
    except ValueError:
        payload = {"status": "stopping"}
    return payload if isinstance(payload, dict) else {"status": "stopping"}


async def approval(
    config: HermesConfig, run_id: str, request_id: str, generation: int, choice: str
) -> dict[str, Any]:
    if choice not in ("once", "deny"):
        raise HermesError("Choix d'approbation invalide (once ou deny attendu).")
    return await _post_control(
        config,
        run_id,
        "approval",
        {"request_id": request_id, "execution_generation": int(generation), "choice": choice},
    )


async def clarify(
    config: HermesConfig, run_id: str, request_id: str, generation: int, answer: str
) -> dict[str, Any]:
    if not answer.strip():
        raise HermesError("La réponse de clarification ne peut pas être vide.")
    return await _post_control(
        config,
        run_id,
        "clarify",
        {
            "request_id": request_id,
            "execution_generation": int(generation),
            "answer": answer[:4000],
        },
    )


async def _post_control(
    config: HermesConfig, run_id: str, action: str, body: dict[str, Any]
) -> dict[str, Any]:
    url = f"{config.base_url}{config.run_prefix}/runs/{run_id}/{action}"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
            response = await client.post(url, headers=_headers(config), json=body)
    except httpx.HTTPError as error:
        raise HermesError(f"Échec réseau : {type(error).__name__}.") from error
    if response.status_code >= 400:
        raise _error_from_response(response)
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def map_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Traduit un statut Hermes en statuts métier HORIZON (contrat §7.4)."""
    hermes_status = str(payload.get("status") or "unknown").lower()
    partial = bool(payload.get("partial"))
    output = str(payload.get("output") or "")[:200000]
    exit_reason = str(payload.get("turn_exit_reason") or "")
    pending = payload.get("pending_controls")

    mission_status = "running"
    step_status = "running"
    checkpoint = ""
    recoverable = False
    error = ""

    if hermes_status in ("queued", "started", "running"):
        mission_status, step_status = "running", "running"
    elif hermes_status == "waiting_for_approval":
        mission_status, step_status, checkpoint = "paused", "running", "approval_required"
    elif hermes_status == "stopping":
        mission_status, step_status, checkpoint = "running", "running", "stop_requested"
    elif hermes_status == "completed" and not partial:
        mission_status, step_status = "completed", "completed"
    elif hermes_status == "failed" or (hermes_status == "completed" and partial):
        mission_status, step_status = "failed", "failed"
        error = exit_reason or "Échec de l'exécution Hermes."
    elif hermes_status == "cancelled":
        mission_status, step_status = "cancelled", "skipped"
    elif hermes_status == "interrupted":
        mission_status, step_status, recoverable = "failed", "failed", True
        error = "Exécution interrompue (redémarrage Hermes) : nouvelle tentative possible."
    else:  # unknown et tout statut non reconnu
        mission_status, step_status, checkpoint = "paused", "running", "unknown_execution"

    return {
        "hermes_status": hermes_status,
        "mission_status": mission_status,
        "step_status": step_status,
        "checkpoint": checkpoint,
        "recoverable": recoverable,
        "output": output,
        "error": error[:4000],
        "usage": payload.get("usage") if isinstance(payload.get("usage"), dict) else {},
        "runtime": payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {},
        "pending_controls": pending,
        "terminal": hermes_status in TERMINAL_STATUSES,
    }
