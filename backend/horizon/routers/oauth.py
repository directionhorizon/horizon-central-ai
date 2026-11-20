"""Routes du flux OAuth des connecteurs (Meta, TikTok).

- GET /api/v1/integrations/oauth/providers           → état des fournisseurs
- GET /api/v1/integrations/oauth/{provider}/start    → URL d'autorisation
- GET /api/v1/integrations/oauth/{provider}/callback → retour du fournisseur

Aucun jeton n'est jamais renvoyé : seul un identifiant de connexion l'est. Le
jeton est stocké localement (fichier hors base), jamais exposé ni journalisé.
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import oauth_connectors as oauth
from ..auth import require_admin
from ..db import connect
from ..repositories import integrations as repo
from ..repositories import operations

router = APIRouter(prefix="/api/v1/integrations/oauth", tags=["integrations"])

_STATES: dict[str, dict[str, Any]] = {}
_STATE_TTL_S = 600


def _purge_states() -> None:
    now = time.time()
    expired = [s for s, v in _STATES.items() if now - v.get("created", 0) > _STATE_TTL_S]
    for state in expired:
        _STATES.pop(state, None)


@router.get("/providers")
def oauth_providers() -> dict[str, Any]:
    """État des fournisseurs OAuth (configurés ou non), sans aucune valeur secrète."""
    return {"items": oauth.provider_status()}


@router.get("/{provider}/start")
def oauth_start(
    provider: str,
    name: str = Query(default=""),
    actor: str = Depends(require_admin),
) -> dict[str, Any]:
    """Renvoie l'URL d'autorisation à ouvrir dans le navigateur."""
    _purge_states()
    state = oauth.new_state()
    try:
        url = oauth.build_authorize_url(provider, state)
    except oauth.OAuthError as exc:
        raise HTTPException(400, str(exc)) from exc
    _STATES[state] = {"provider": provider, "name": name, "created": time.time()}
    return {"provider": provider, "authorize_url": url, "state": state}


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
) -> dict[str, Any]:
    """Retour du fournisseur : échange le code, enregistre la connexion.

    Le `state` (généré par HORIZON) sert de protection CSRF. Aucun jeton n'est
    renvoyé ; la réponse ne contient que l'identifiant de la connexion.
    """
    entry = _STATES.pop(state, None)
    if entry is None or entry.get("provider") != provider:
        raise HTTPException(400, "État OAuth invalide ou expiré. Relancez la connexion.")
    try:
        token = await oauth.exchange_code(provider, code)
    except oauth.OAuthError as exc:
        raise HTTPException(400, str(exc)) from exc
    label = oauth.PROVIDERS.get(provider, {}).get("label", provider)
    name = entry.get("name") or f"{label} (OAuth)"
    with connect() as db:
        item = repo.create_integration(
            db,
            {
                "name": name,
                "category": "communication",
                "method": "oauth2",
                "endpoint": "",
                "status": "connected",
                "permissions": oauth.PROVIDERS.get(provider, {}).get("scope", ""),
                "capabilities": "publish",
                "api_key_env": f"secret:{provider}",
                "config": {"provider": provider},
            },
        )
        oauth.store_secret(item["id"], provider, token)
        operations.log(
            db, actor="oauth", action="integration.oauth", target_type="integration",
            target_id=item["id"], result="success", detail=f"{provider} connecté par OAuth.",
        )
    return {"connected": True, "integration_id": item["id"], "name": name, "provider": provider}
