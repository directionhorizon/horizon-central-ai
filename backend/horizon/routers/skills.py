"""Routes de la bibliothèque de skills (compétences).

Catalogue générique et recherchable. Aucune compétence n'est codée en dur :
l'utilisateur ajoute, modifie ou désactive librement les entrées.
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..models import SkillCreate, SkillImportRequest, SkillUpdate
from ..repositories import operations, skills

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

#: Hôtes autorisés pour l'import depuis une URL (sécurité : jamais d'URL arbitraire).
#: Plusieurs sources sont acceptées (GitHub, Hugging Face). En ajouter une se fait
#: ici, sans toucher au reste du code.
ALLOWED_IMPORT_HOSTS = {
    "raw.githubusercontent.com",
    "github.com",
    "gist.githubusercontent.com",
    "huggingface.co",
    "hf.co",
}
MAX_IMPORT_BYTES = 1_000_000


@router.get("")
def list_skills(q: str | None = None, category: str | None = None, status: str | None = None):
    with connect() as db:
        items = skills.list_skills(db, q=q, category=category, status=status)
    return {"items": items, "count": len(items)}


@router.get("/categories")
def list_categories():
    with connect() as db:
        items = skills.categories(db)
    return {"items": items}


@router.post("/import")
async def import_skills(payload: SkillImportRequest, actor: str = Depends(require_admin)):
    """Importe des compétences — depuis un bundle JSON ou une URL d'une source autorisée.

    Sources acceptées : GitHub et Hugging Face (voir ALLOWED_IMPORT_HOSTS). Sécurité :
    HTTPS uniquement, taille bornée, contenu JSON en liste, métadonnées déclaratives
    seulement (aucun code exécuté). L'import ne remplace jamais une compétence existante.
    """
    items = list(payload.bundle or [])
    source_ref = ""

    if payload.url:
        parsed = urlparse(payload.url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMPORT_HOSTS:
            raise HTTPException(
                400, "Source non autorisée : seules les URL GitHub en HTTPS sont acceptées."
            )
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(
                    payload.url, headers={"User-Agent": "horizon-skill-import"}
                )
        except httpx.HTTPError as error:
            raise HTTPException(502, f"Téléchargement impossible : {type(error).__name__}.")
        if response.status_code >= 400:
            raise HTTPException(502, f"Source distante en erreur (HTTP {response.status_code}).")
        if len(response.content) > MAX_IMPORT_BYTES:
            raise HTTPException(413, "Fichier trop volumineux (1 Mo maximum).")
        try:
            data = response.json()
        except ValueError:
            raise HTTPException(400, "Le fichier distant n'est pas un JSON valide.")
        if not isinstance(data, list):
            raise HTTPException(400, "Format attendu : une liste de compétences.")
        items = data
        source_ref = payload.url

    if not items:
        raise HTTPException(400, "Aucune compétence à importer.")

    with connect() as db:
        result = skills.import_skills(db, items, origin=payload.origin, source_ref=source_ref)
        operations.log(
            db, actor=actor, action="skill.import", target_type="skill",
            detail=f"Import de compétences : {result['created']} ajoutée(s), {result['skipped']} ignorée(s).",
        )
    return {"status": "ok", **result}


@router.post("", status_code=201)
def create_skill(payload: SkillCreate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = skills.create_skill(db, payload.model_dump())
        operations.log(
            db, actor=actor, action="skill.create", target_type="skill",
            target_id=item.get("id"), detail=f"Compétence ajoutée : {payload.name}",
        )
    return item


@router.get("/{skill_id}")
def read_skill(skill_id: str):
    with connect() as db:
        item = skills.get_skill(db, skill_id)
        if item is None:
            raise HTTPException(404, "Compétence introuvable.")
    return item


@router.patch("/{skill_id}")
def update_skill(skill_id: str, payload: SkillUpdate, actor: str = Depends(require_admin)):
    with connect() as db:
        item = skills.update_skill(db, skill_id, payload.model_dump(exclude_unset=True))
        if item is None:
            raise HTTPException(404, "Compétence introuvable.")
        operations.log(
            db, actor=actor, action="skill.update", target_type="skill",
            target_id=skill_id, detail="Compétence modifiée.",
        )
    return item


@router.delete("/{skill_id}")
def disable_skill(skill_id: str, actor: str = Depends(require_admin)):
    """Désactivation logique : la fiche est conservée."""
    with connect() as db:
        item = skills.disable_skill(db, skill_id)
        if item is None:
            raise HTTPException(404, "Compétence introuvable.")
        operations.log(
            db, actor=actor, action="skill.disable", target_type="skill",
            target_id=skill_id, detail="Compétence désactivée (aucune suppression).",
        )
    return item
