"""Lecture seule du flux MAYELA CRM (Supabase / PostgREST).

MAYELA reste propriétaire de ses données : HORIZON ne se connecte ni à Meta ni à
TikTok, il lit uniquement des **vues** en lecture seule exposées par MAYELA
(`horizon_feed_*`), à travers un rôle Postgres dédié et sans droit d'écriture.

Sécurité : aucun secret n'est journalisé ni renvoyé par l'API. Seuls les *noms*
des variables d'environnement sont connus du code, jamais leurs valeurs.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any

import httpx

BASE_ENV = "HORIZON_MAYELA_SUPABASE_URL"
ANON_ENV = "HORIZON_MAYELA_SUPABASE_ANON_KEY"
TOKEN_ENV = "HORIZON_MAYELA_SUPABASE_TOKEN"
ENV_VARS = (BASE_ENV, ANON_ENV, TOKEN_ENV)

# Vue lue et ordre d'affichage (le plus récent d'abord).
VIEWS: dict[str, tuple[str, str]] = {
    "posts": ("horizon_feed_posts", "created_at.desc"),
    "ads": ("horizon_feed_ads", "jour.desc"),
    "flux": ("horizon_feed_flux", "jour.desc"),
}

CARD_ID = "mayela-crm"
TIMEOUT_S = 15.0
MAX_LIMIT = 1000


class MayelaError(RuntimeError):
    """Erreur lisible : jamais de secret ni de détail d'infrastructure."""


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def missing_vars() -> list[str]:
    """Noms des variables absentes. Aucune valeur n'est lue ni renvoyée."""
    return [name for name in ENV_VARS if not _env(name)]


def configured() -> bool:
    return not missing_vars()


def fetch(view: str, limit: int = 200) -> list[dict[str, Any]]:
    """Lit une vue en lecture seule. Lève `MayelaError` si ce n'est pas possible."""
    if view not in VIEWS:
        raise MayelaError(f"vue inconnue : {view}")
    missing = missing_vars()
    if missing:
        raise MayelaError("configuration incomplète : " + ", ".join(missing))
    table, order = VIEWS[view]
    base = _env(BASE_ENV).rstrip("/")
    bounded = max(1, min(int(limit), MAX_LIMIT))
    try:
        response = httpx.get(
            f"{base}/rest/v1/{table}",
            headers={"apikey": _env(ANON_ENV), "Authorization": f"Bearer {_env(TOKEN_ENV)}"},
            params={"select": "*", "order": order, "limit": bounded},
            timeout=TIMEOUT_S,
        )
    except httpx.HTTPError as error:
        raise MayelaError(f"MAYELA injoignable ({type(error).__name__}).") from error
    if response.status_code >= 400:
        raise MayelaError(f"MAYELA a refusé la lecture (HTTP {response.status_code}).")
    try:
        payload = response.json()
    except ValueError as error:
        raise MayelaError("réponse MAYELA illisible.") from error
    if not isinstance(payload, list):
        raise MayelaError("réponse MAYELA inattendue.")
    return [row for row in payload if isinstance(row, dict)]


def summary() -> dict[str, Any]:
    """Compteurs par vue. Une vue vide n'est jamais une erreur."""
    counts: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for view in VIEWS:
        try:
            counts[view] = len(fetch(view, limit=MAX_LIMIT))
        except MayelaError as error:
            counts[view] = None
            errors[view] = str(error)
    if errors:
        counts["errors"] = errors
    return counts


def status() -> dict[str, Any]:
    """État lisible pour l'interface : configuré, joignable, compteurs."""
    missing = missing_vars()
    result: dict[str, Any] = {
        "configured": not missing,
        "env_vars": list(ENV_VARS),
        "missing": missing,
    }
    if missing:
        result["status"] = "not_configured"
        return result
    result.update(summary())
    reachable = all(result.get(view) is not None for view in VIEWS)
    result["status"] = "connected" if reachable else "partial"
    return result


def sync_registry(db: sqlite3.Connection) -> None:
    """Inscrit la fiche MAYELA au registre des connexions (idempotent, sans secret)."""
    from .repositories import integrations as repo

    repo.upsert_integration(
        db,
        CARD_ID,
        {
            "name": "MAYELA CRM (flux)",
            "category": "app",
            "method": "bearer",
            "endpoint": _env(BASE_ENV),
            "status": "partial" if configured() else "not_configured",
            "capabilities": ", ".join(("read", "publications", "campagnes", "flux")),
            "api_key_env": TOKEN_ENV,
        },
    )
