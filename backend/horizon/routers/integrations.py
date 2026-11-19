"""Routes du registre des connexions et intégrations.

Sécurité : aucun secret n'est stocké, renvoyé ni journalisé. Seul le *nom* de la
variable d'environnement porteuse de la clé (`api_key_env`) est manipulé, et la
réponse indique uniquement si cette variable est présente (`secret_present`).

Une intégration n'est déclarée « connectée » qu'après un test réel (TCP ou HTTP)
déclenché explicitement par l'utilisateur.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import connect
from ..repositories import integrations as repo
from ..repositories import operations

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

CATEGORY_LABELS = {
    "orchestrator": "Orchestrateurs externes",
    "app": "Applications et services",
    "llm_provider": "Fournisseurs IA",
    "model": "Modèles IA",
    "mcp": "Serveurs MCP",
    "api": "API externes",
    "machine": "Machines et environnements",
    "storage": "Services de stockage",
    "communication": "Services de communication",
}

METHOD_LABELS = {
    "oauth2": "OAuth 2.0",
    "api_key": "Clé API",
    "bearer": "Jeton Bearer",
    "endpoint": "Endpoint personnalisé",
    "mcp": "MCP",
    "rest": "API REST",
    "cli": "CLI / adaptateur local",
    "webhook": "Webhook",
}

STATUS_LABELS = {
    "connected": "Connecté",
    "not_configured": "Non configuré",
    "pending": "En attente d’autorisation",
    "expired": "Autorisation expirée",
    "unavailable": "Indisponible",
    "error": "Erreur",
    "partial": "Connexion partielle",
}


def _is_safe_host(host: str) -> bool:
    """Anti-SSRF : n'autorise que des hôtes résolvant vers des adresses publiques.

    Refuse les adresses privées, la boucle locale, les adresses lien-local
    (métadonnées cloud 169.254.x.x), réservées, multicast et non spécifiées.
    """
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def _probe(endpoint: str) -> tuple[bool, str]:
    """Test réel et borné : HTTP(S) ou TCP. Aucune donnée sensible renvoyée.

    Sécurité (anti-SSRF) : l'hôte fourni par l'appelant est refusé s'il résout
    vers une adresse interne — le serveur ne peut pas être détourné vers le
    réseau privé ou les métadonnées cloud.
    """
    target = endpoint.strip()
    if not target:
        return False, "aucun endpoint renseigné"
    if target.startswith(("http://", "https://")):
        host = urlsplit(target).hostname or ""
        if not _is_safe_host(host):
            return False, "endpoint interne ou invalide refusé"
        try:
            response = httpx.get(target, timeout=4.0, follow_redirects=False)
        except httpx.HTTPError as exc:
            return False, f"échec réseau ({type(exc).__name__})"
        if response.status_code >= 500:
            return False, f"HTTP {response.status_code}"
        return True, f"HTTP {response.status_code}"
    host, _, port = target.partition(":")
    if not _is_safe_host(host):
        return False, "hôte interne ou invalide refusé"
    try:
        with socket.create_connection((host, int(port or "443")), timeout=3.0):
            return True, "connexion TCP établie"
    except (OSError, ValueError) as exc:
        return False, f"échec réseau ({type(exc).__name__})"


def _endpoint_host(endpoint: str) -> str:
    """Hôte seul : jamais le chemin complet dans une réponse d'interface."""
    raw = endpoint.strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return urlsplit(raw).hostname or ""
    return raw.partition(":")[0]


def _secret_present(env_name: str) -> bool:
    return bool(env_name) and bool(os.getenv(env_name, "").strip())


def _public(item: dict[str, Any]) -> dict[str, Any]:
    """Vue sûre : endpoint masqué, jamais de valeur secrète."""
    view = dict(item)
    view["endpoint_host"] = _endpoint_host(view.get("endpoint", ""))
    view.pop("endpoint", None)
    view["secret_present"] = _secret_present(view.get("api_key_env", ""))
    return view


def _validate(payload: dict[str, Any]) -> None:
    if payload.get("category") and payload["category"] not in repo.CATEGORIES:
        raise HTTPException(422, "Catégorie inconnue.")
    if payload.get("method") and payload["method"] not in repo.METHODS:
        raise HTTPException(422, "Méthode de connexion inconnue.")
    if payload.get("status") and payload["status"] not in repo.STATUSES:
        raise HTTPException(422, "État inconnu.")


@router.get("/catalog")
def integrations_catalog():
    """Référentiel des catégories, méthodes et états (aucune donnée sensible)."""
    return {
        "categories": [{"id": key, "label": value} for key, value in CATEGORY_LABELS.items()],
        "methods": [{"id": key, "label": value} for key, value in METHOD_LABELS.items()],
        "statuses": [{"id": key, "label": value} for key, value in STATUS_LABELS.items()],
    }


@router.get("")
def list_integrations(category: str | None = None, include_archived: bool = False):
    with connect() as db:
        items = repo.list_integrations(db, category=category, include_archived=include_archived)
        counters = repo.stats(db)
    return {
        "items": [_public(item) for item in items],
        "count": len(items),
        "stats": counters,
    }


@router.get("/{integration_id}")
def read_integration(integration_id: str):
    with connect() as db:
        item = repo.get_integration(db, integration_id)
    if item is None:
        raise HTTPException(404, "Intégration introuvable.")
    return _public(item)


@router.post("", status_code=201)
def create_integration(payload: dict[str, Any], actor: str = Depends(require_admin)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(422, "Le nom du service est obligatoire.")
    _validate(payload)
    data = {
        "name": name[:120],
        "category": payload.get("category", "app"),
        "method": payload.get("method", "endpoint"),
        "endpoint": str(payload.get("endpoint", ""))[:500],
        "permissions": str(payload.get("permissions", ""))[:500],
        "capabilities": str(payload.get("capabilities", ""))[:500],
        "api_key_env": str(payload.get("api_key_env", ""))[:120],
        "config": payload.get("config") if isinstance(payload.get("config"), dict) else {},
    }
    with connect() as db:
        item = repo.create_integration(db, data)
        operations.log(
            db, actor=actor, action="integration.create", target_type="integration",
            target_id=item.get("id"), detail=f"{data['category']} · {data['method']} · {name}",
        )
    return _public(item)


@router.patch("/{integration_id}")
def update_integration(
    integration_id: str, payload: dict[str, Any], actor: str = Depends(require_admin)
):
    _validate(payload)
    allowed = {
        "name", "category", "method", "endpoint", "status",
        "permissions", "capabilities", "api_key_env", "config",
    }
    changes = {key: value for key, value in payload.items() if key in allowed}
    with connect() as db:
        item = repo.update_integration(db, integration_id, changes)
        if item is None:
            raise HTTPException(404, "Intégration introuvable.")
        operations.log(
            db, actor=actor, action="integration.update", target_type="integration",
            target_id=integration_id, detail="Fiche de connexion modifiée.",
        )
    return _public(item)


@router.delete("/{integration_id}")
def archive_integration(integration_id: str, actor: str = Depends(require_admin)):
    """Suppression logique : la fiche est conservée (archived=1)."""
    with connect() as db:
        item = repo.archive_integration(db, integration_id)
        if item is None:
            raise HTTPException(404, "Intégration introuvable.")
        operations.log(
            db, actor=actor, action="integration.archive", target_type="integration",
            target_id=integration_id, detail="Connexion archivée (aucune suppression).",
        )
    return _public(item)


@router.post("/{integration_id}/test")
def test_integration(integration_id: str, actor: str = Depends(require_admin)):
    """Test réel de la connexion. Aucune valeur de secret n'est renvoyée."""
    with connect() as db:
        item = repo.get_integration(db, integration_id)
        if item is None:
            raise HTTPException(404, "Intégration introuvable.")
        secret_env = item.get("api_key_env") or ""
        secret_present = _secret_present(secret_env)
        endpoint = item.get("endpoint") or ""

        if secret_env and not secret_present:
            status, detail = "not_configured", f"variable {secret_env} absente côté serveur"
        elif endpoint:
            ok, message = _probe(endpoint)
            status, detail = ("connected", message) if ok else ("unavailable", message)
        else:
            status, detail = "partial", "aucun endpoint testable : autorisation à vérifier manuellement"

        updated = repo.record_check(db, integration_id, status, "" if status == "connected" else detail)
        operations.log(
            db, actor=actor, action="integration.test", target_type="integration",
            target_id=integration_id, result="success" if status == "connected" else "failed",
            detail=f"{status} · {detail}",
        )
    return {
        "id": integration_id,
        "status": status,
        "detail": detail,
        "secret_present": secret_present,
        "endpoint_host": _endpoint_host(endpoint),
        "last_checked_at": (updated or {}).get("last_checked_at"),
        "verified": status == "connected",
    }