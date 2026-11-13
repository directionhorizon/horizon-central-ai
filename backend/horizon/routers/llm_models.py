"""Routes du gestionnaire de modèles IA et de la sélection par orchestrateur.

Aucune clé n'est exposée : la réponse contient uniquement le nom de la
variable d'environnement (`api_key_env`) et un indicateur de présence.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..llm import LLMError, chat, test_connection
from ..models import ModelSelectionUpdate, ProviderCreate, ProviderUpdate
from ..repositories import llm as llm_repo
from ..repositories import operations

router = APIRouter(prefix="/api/v1", tags=["models"])


def _decorate(row: dict) -> dict:
    key_env = (row.get("api_key_env") or "").strip()
    row["api_key_configured"] = bool(key_env and os.getenv(key_env))
    row["api_key_env"] = key_env
    return row


@router.get("/models")
def list_models():
    with connect() as db:
        providers = [_decorate(row) for row in llm_repo.list_providers(db)]
        selection = llm_repo.get_selection(db)
    return {"items": providers, "selection": selection}


@router.post("/models", status_code=201)
def create_model(payload: ProviderCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = llm_repo.create_provider(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="model.create", target_type="llm_provider",
            target_id=item.get("id"), detail=f"Fournisseur enregistré : {payload.name}",
        )
    return _decorate(item)


@router.patch("/models/{provider_id}")
def update_model(provider_id: str, payload: ProviderUpdate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = llm_repo.update_provider(db, provider_id, payload.model_dump(exclude_none=True))
        if item is None:
            raise HTTPException(404, "Fournisseur introuvable.")
        operations.log(
            db, actor=actor, action="model.update", target_type="llm_provider",
            target_id=provider_id, detail="Configuration modifiée (vérification invalidée).",
        )
    return _decorate(item)


@router.delete("/models/{provider_id}")
def delete_model(provider_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        item = llm_repo.get_provider(db, provider_id)
        if item is None:
            raise HTTPException(404, "Fournisseur introuvable.")
        llm_repo.delete_provider(db, provider_id)
        operations.log(
            db, actor=actor, action="model.delete", target_type="llm_provider",
            target_id=provider_id, detail="Configuration fournisseur supprimée.",
        )
    return {"id": provider_id, "status": "deleted"}


@router.post("/models/{provider_id}/test")
async def test_model(provider_id: str, actor: str = Depends(require_admin)):
    """Test réel de connexion. Aucun fournisseur n'est déclaré disponible sans ce test."""
    with connect() as db:
        row = llm_repo.get_provider(db, provider_id)
        if row is None:
            raise HTTPException(404, "Fournisseur introuvable.")

    result = await test_connection(row)
    with connect() as db:
        llm_repo.set_health(db, provider_id, result["status"], result["detail"])
        operations.log(
            db, actor=actor, action="model.test", target_type="llm_provider",
            target_id=provider_id, result=result["status"], detail=result["detail"],
        )
    return {"id": provider_id, **result}


@router.get("/settings/model-selection")
def read_selection():
    with connect() as db:
        return llm_repo.get_selection(db)


@router.put("/settings/model-selection")
def update_selection(payload: ModelSelectionUpdate, actor: str = Depends(require_admin)):
    with connect() as db:
        if payload.provider_id:
            provider = llm_repo.get_provider(db, payload.provider_id)
            if provider is None:
                raise HTTPException(404, "Fournisseur introuvable.")
            if payload.mode == "manual" and not (payload.model or provider.get("default_model")):
                raise HTTPException(422, "Sélection manuelle : un modèle est requis.")
        selection = llm_repo.set_selection(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="model.selection.update", target_type="settings",
            target_id="model_selection", detail=f"Mode : {selection['mode']}",
        )
    return selection


@router.post("/models/chat-test")
async def chat_test(payload: dict, actor: str = Depends(require_admin)):
    """Appel de test réel à un fournisseur vérifié.

    Refuse explicitement si aucun fournisseur n'est disponible : aucune
    réponse assistant n'est fabriquée.
    """
    provider_id = str(payload.get("provider_id") or "")
    message = str(payload.get("message") or "").strip()
    if not provider_id or not message:
        raise HTTPException(422, "provider_id et message sont requis.")

    with connect() as db:
        row = llm_repo.get_provider(db, provider_id)
        if row is None:
            raise HTTPException(404, "Fournisseur introuvable.")
        if row.get("status") != "available":
            raise HTTPException(409, "Fournisseur non vérifié : lancez d'abord /models/{id}/test.")

    try:
        result = await chat(row, [{"role": "user", "content": message}])
    except LLMError as error:
        with connect() as db:
            operations.log(
                db, actor=actor, action="model.chat_test", target_type="llm_provider",
                target_id=provider_id, result="failed", detail=str(error),
            )
        raise HTTPException(502, str(error)) from error

    with connect() as db:
        operations.log(
            db, actor=actor, action="model.chat_test", target_type="llm_provider",
            target_id=provider_id, result="success",
            detail=f"Réponse reçue ({len(result['content'])} caractères).",
        )
    return result
