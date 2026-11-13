"""Routes de la mémoire documentaire centrale.

Mémoire centrale distincte des mémoires spécialisées : les documents sont
rattachés à un projet, consultables et recherchables par mots-clés. Aucun
contenu n'est écrasé silencieusement (archivage logique uniquement).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..models import DocumentCreate, DocumentUpdate
from ..repositories import documents, operations, projects, sync

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("")
def list_documents(
    project_id: str | None = None, q: str | None = None, limit: int = 200
):
    with connect() as db:
        items = documents.list_documents(db, project_id=project_id, query=q, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("", status_code=201)
def create_document(payload: DocumentCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        if payload.project_id and projects.get_project(db, payload.project_id) is None:
            raise HTTPException(404, "Projet introuvable.")
        item = documents.create_document(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="document.create", target_type="document",
            target_id=item.get("id"), detail=f"Document créé : {payload.title}",
        )
        sync.enqueue(db, "documents", item.get("id") or "", "create", item)
    return item


@router.get("/{document_id}")
def read_document(document_id: str):
    with connect() as db:
        item = documents.get_document(db, document_id)
    if item is None:
        raise HTTPException(404, "Document introuvable.")
    return item


@router.patch("/{document_id}")
def update_document(
    document_id: str, payload: DocumentUpdate, actor: str = Depends(require_admin)
):
    changes = payload.model_dump(exclude_none=True)
    with connect() as db:
        item = documents.update_document(db, document_id, changes)
        if item is None:
            raise HTTPException(404, "Document introuvable.")
        operations.log(
            db, actor=actor, action="document.update", target_type="document",
            target_id=document_id, detail=f"Document modifié : {item.get('title')}",
        )
        sync.enqueue(db, "documents", document_id, "update", item)
    return item


@router.delete("/{document_id}")
def archive_document(document_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        item = documents.archive_document(db, document_id)
        if item is None:
            raise HTTPException(404, "Document introuvable.")
        operations.log(
            db, actor=actor, action="document.archive", target_type="document",
            target_id=document_id, detail=f"Document archivé : {item.get('title')}",
        )
        sync.enqueue(db, "documents", document_id, "delete", item)
    return item
