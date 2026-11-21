"""Adaptateur LLM unique, compatible OpenAI.

Un seul adaptateur couvre Ollama, LM Studio, llama.cpp, vLLM, OpenRouter,
OpenAI, Azure OpenAI et tout service exposant `/chat/completions`.

Principes :
- la clé API n'est jamais lue depuis la base : seul le NOM de la variable
  d'environnement est stocké (`api_key_env`) ;
- aucun fournisseur n'est réputé disponible avant un test réel ;
- en cas d'échec, une exception explicite est levée : jamais de réponse
  assistant fabriquée.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_TIMEOUT_S = 60.0
PROBE_TIMEOUT_S = 10.0


class LLMError(RuntimeError):
    """Erreur d'appel fournisseur, avec un message non sensible."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    name: str
    base_url: str
    model: str
    api_key: str | None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)


def _normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/")


#: Variable générique consultée en repli quand la fiche ne déclare aucune variable.
#: Volontairement limité à UN nom générique : avec plusieurs fournisseurs, chaque
#: fiche doit déclarer SA variable (HORIZON_<FOURNISSEUR>_API_KEY) pour éviter
#: qu'une clé d'un fournisseur soit utilisée pour un autre.
KEY_FALLBACK_ENVS = ("HORIZON_LLM_API_KEY",)


def resolve_api_key(key_env: str) -> str | None:
    """Retourne la clé du fournisseur : variable déclarée, puis replis connus."""
    for name in (key_env, *KEY_FALLBACK_ENVS):
        name = (name or "").strip()
        if not name:
            continue
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return None


def build_config(row: dict[str, Any]) -> ProviderConfig:
    """Construit la configuration d'appel à partir d'une ligne `llm_providers`."""
    key_env = (row.get("api_key_env") or "").strip()
    api_key = resolve_api_key(key_env)
    return ProviderConfig(
        id=row.get("id", ""),
        name=row.get("name", ""),
        base_url=_normalize_base_url(row.get("base_url", "")),
        model=(row.get("default_model") or "").strip(),
        api_key=api_key,
    )


def _headers(config: ProviderConfig) -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


async def test_connection(row: dict[str, Any]) -> dict[str, Any]:
    """Teste réellement le fournisseur.

    Essaie d'abord `GET {base_url}/models` (liste des modèles). Certains services
    compatibles OpenAI (Gemini, par exemple) n'exposent pas cette route : on
    retombe alors sur un appel réel `POST {base_url}/chat/completions` avec le
    modèle par défaut, ce qui vérifie la capacité réellement utilisée.

    Renvoie un dictionnaire honnête : `status` vaut `available`, `unavailable`
    ou `unconfigured`. Le message d'erreur ne contient jamais la clé.
    """
    config = build_config(row)
    if not config.configured:
        return {"status": "unconfigured", "detail": "URL de base ou modèle absent.", "models": []}
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
            response = await client.get(f"{config.base_url}/models", headers=_headers(config))
            if response.status_code < 400:
                payload = response.json()
                items = payload.get("data") if isinstance(payload, dict) else None
                models = (
                    [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
                    if isinstance(items, list)
                    else []
                )
                return {
                    "status": "available",
                    "detail": f"{len(models)} modèle(s) exposé(s).",
                    "models": models[:200],
                }
            # Repli : la liste des modèles n'est pas exposée (ex. Gemini).
            # On essaie les deux écritures du nom de modèle (« id » et « models/id »).
            candidates = [config.model]
            if config.model.startswith("models/"):
                candidates.append(config.model[len("models/"):])
            else:
                candidates.append(f"models/{config.model}")
            for candidate in candidates:
                probe = await client.post(
                    f"{config.base_url}/chat/completions",
                    headers=_headers(config),
                    json={
                        "model": candidate,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                )
                if probe.status_code != 404:
                    break
        if probe.status_code >= 400:
            detail = ""
            try:
                payload = probe.json()
                error = payload.get("error") if isinstance(payload, dict) else None
                if isinstance(error, dict) and error.get("message"):
                    detail = f" : {error['message']}"
                elif isinstance(error, str):
                    detail = f" : {error}"
            except ValueError:
                detail = ""
            return {
                "status": "unavailable",
                "detail": f"HTTP {probe.status_code} sur /chat/completions{detail}.",
                "models": [],
            }
        return {
            "status": "available",
            "detail": "Réponse du modèle reçue.",
            "models": [config.model],
        }
    except httpx.HTTPError as error:
        return {
            "status": "unavailable",
            "detail": f"Échec réseau : {type(error).__name__}.",
            "models": [],
        }


async def chat(
    row: dict[str, Any],
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Envoie une conversation au fournisseur et renvoie la réponse utile.

    Lève `LLMError` si le fournisseur n'est pas configuré ou échoue.
    """
    config = build_config(row)
    if not config.configured:
        raise LLMError("Fournisseur non configuré (URL ou modèle absent).")
    chosen_model = (model or config.model).strip()
    if not chosen_model:
        raise LLMError("Aucun modèle sélectionné pour ce fournisseur.")

    # Certains services (Gemini) exposent les modèles sous « models/<id> » tout en
    # attendant « <id> » à l'appel (ou l'inverse). On essaie les deux écritures.
    candidates = [chosen_model]
    if chosen_model.startswith("models/"):
        candidates.append(chosen_model[len("models/"):])
    else:
        candidates.append(f"models/{chosen_model}")

    response = None
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            for candidate in candidates:
                body = {
                    "model": candidate,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }
                response = await client.post(
                    f"{config.base_url}/chat/completions",
                    headers=_headers(config),
                    json=body,
                )
                if response.status_code != 404:
                    chosen_model = candidate
                    break
    except httpx.TimeoutException as error:
        raise LLMError(f"Délai dépassé après {timeout_s:.0f} s.") from error
    except httpx.HTTPError as error:
        raise LLMError(f"Échec réseau : {type(error).__name__}.") from error

    if response is None:
        raise LLMError("Aucune réponse du fournisseur.")

    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error_obj = payload.get("error")
                if isinstance(error_obj, dict) and error_obj.get("message"):
                    detail = str(error_obj["message"])[:300]
                elif isinstance(error_obj, str):
                    detail = error_obj[:300]
        except ValueError:
            detail = ""
        if not detail:
            # Corps non JSON : on remonte un extrait brut pour diagnostiquer
            # (aucune clé n'y figure, seulement le message d'erreur du service).
            raw = (response.text or "").strip().replace("\n", " ")
            if raw:
                detail = raw[:300]
        raise LLMError(
            f"HTTP {response.status_code} du fournisseur" + (f" : {detail}" if detail else "."),
            status_code=response.status_code,
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise LLMError("Réponse fournisseur illisible (JSON invalide).") from error

    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise LLMError("Réponse fournisseur sans contenu exploitable.")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMError("Réponse fournisseur vide.")

    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return {
        "content": content,
        "model": chosen_model,
        "provider_id": config.id,
        "provider_name": config.name,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    }
