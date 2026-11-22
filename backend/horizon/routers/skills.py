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
    "gitlab.com",
    "raw.gitlab.com",
    "bitbucket.org",
    "openai.com",
    "platform.openai.com",
    "anthropic.com",
    "docs.anthropic.com",
}

#: Sources externes proposées à l'utilisateur (host + libellé + type).
#: Aucune URL n'est inventée : ce sont des hôtes publics connus. L'utilisateur
#: fournit le lien exact du fichier JSON de compétences.
SKILL_SOURCES = (
    {"id": "github", "label": "GitHub", "host": "raw.githubusercontent.com", "kind": "url"},
    {"id": "gist", "label": "GitHub Gist", "host": "gist.githubusercontent.com", "kind": "url"},
    {"id": "gitlab", "label": "GitLab", "host": "gitlab.com", "kind": "url"},
    {"id": "bitbucket", "label": "Bitbucket", "host": "bitbucket.org", "kind": "url"},
    {"id": "huggingface", "label": "Hugging Face", "host": "huggingface.co", "kind": "url"},
    {"id": "openai", "label": "OpenAI", "host": "platform.openai.com", "kind": "url"},
    {"id": "anthropic", "label": "Anthropic", "host": "docs.anthropic.com", "kind": "url"},
    {"id": "npm", "label": "Paquet npm", "host": "registry.npmjs.org", "kind": "package"},
    {"id": "pypi", "label": "Paquet PyPI", "host": "pypi.org", "kind": "package"},
)


def _detect_origin(url: str) -> str:
    """Déduit la provenance d'une URL de compétences, sans jamais deviner le contenu."""
    host = (urlparse(url).hostname or "").lower()
    if "gist" in host:
        return "gist"
    if "github" in host:
        return "github"
    if "gitlab" in host:
        return "gitlab"
    if "bitbucket" in host:
        return "bitbucket"
    if "huggingface" in host or host.endswith("hf.co"):
        return "huggingface"
    if "openai" in host:
        return "openai"
    if "anthropic" in host:
        return "anthropic"
    return "external"
MAX_IMPORT_BYTES = 1_000_000

#: Registres de paquets pris en charge (hôtes fixes, jamais fournis par l'utilisateur).
NPM_REGISTRY = "https://registry.npmjs.org"
PYPI_REGISTRY = "https://pypi.org/pypi"


async def _fetch_json(url: str, label: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "horizon-skill-import"})
    except httpx.HTTPError as error:
        raise HTTPException(502, f"Téléchargement impossible : {type(error).__name__}.")
    if response.status_code >= 400:
        raise HTTPException(502, f"{label} introuvable (HTTP {response.status_code}).")
    if len(response.content) > MAX_IMPORT_BYTES:
        raise HTTPException(413, "Réponse trop volumineuse (1 Mo maximum).")
    try:
        data = response.json()
    except ValueError:
        raise HTTPException(400, f"Réponse {label} illisible.")
    return data if isinstance(data, dict) else {}


def _package_entry(package: str, description: str, home: str, source: str) -> dict:
    return {
        "id": f"{source}-{package}",
        "name": package,
        "category": "Intégrations et outils",
        "subcategory": f"Paquet {source}",
        "description": description or f"Paquet {source} importé comme outil/compétence.",
        "level": "standard",
        "tags": f"{source},package,outil",
        "origin": source,
        "source_url": home,
        "author": "",
        "license": "",
    }


async def _fetch_package(source: str, package: str) -> tuple[dict, str]:
    """Récupère les métadonnées d'un paquet npm ou PyPI (aucun code exécuté)."""
    if source == "npm":
        url = f"{NPM_REGISTRY}/{package}"
        data = await _fetch_json(url, "Paquet npm")
        latest = str((data.get("dist-tags") or {}).get("latest") or "")
        version = (data.get("versions") or {}).get(latest, {}) or {}
        description = str(data.get("description") or version.get("description") or "")
        home = str(data.get("homepage") or version.get("homepage") or f"https://www.npmjs.com/package/{package}")
        return _package_entry(package, description, home, "npm"), url
    url = f"{PYPI_REGISTRY}/{package}/json"
    data = await _fetch_json(url, "Paquet PyPI")
    info = data.get("info") or {}
    description = str(info.get("summary") or "")
    home = str(info.get("home_page") or info.get("project_url") or f"https://pypi.org/project/{package}/")
    return _package_entry(package, description, home, "pypi"), url


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


@router.get("/sources")
def list_sources():
    """Sources externes autorisées pour l'import de compétences."""
    return {"items": list(SKILL_SOURCES)}


@router.get("/category-map")
def category_map():
    """Catégories de compétences et outils recommandés par catégorie."""
    from ..skills_categories import category_catalog

    return {"items": category_catalog()}


@router.post("/import")
async def import_skills(payload: SkillImportRequest, actor: str = Depends(require_admin)):
    """Importe des compétences — depuis un bundle JSON ou une URL d'une source autorisée.

    Sources acceptées : GitHub et Hugging Face (voir ALLOWED_IMPORT_HOSTS). Sécurité :
    HTTPS uniquement, taille bornée, contenu JSON en liste, métadonnées déclaratives
    seulement (aucun code exécuté). L'import ne remplace jamais une compétence existante.
    """
    items = list(payload.bundle or [])
    source_ref = ""
    origin = payload.origin
    source = (payload.source or "").strip().lower()
    package = (payload.package or "").strip()

    if source in ("npm", "pypi"):
        if not package:
            raise HTTPException(400, "Nom de paquet requis pour cette source.")
        entry, source_ref = await _fetch_package(source, package)
        items = [entry]
        origin = source
    elif payload.url:
        parsed = urlparse(payload.url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMPORT_HOSTS:
            raise HTTPException(
                400,
                "Source non autorisée : utilisez une URL HTTPS GitHub, GitLab, Bitbucket "
                "ou Hugging Face.",
            )
        # La provenance est déduite de l'hôte réel (jamais devinée).
        origin = _detect_origin(payload.url)
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
        result = skills.import_skills(db, items, origin=origin, source_ref=source_ref)
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
