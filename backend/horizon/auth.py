"""Authentification de l'accès à l'application (propriétaire unique).

Deux mécanismes coexistent, dans cet ordre de priorité :

1. **Session Google** (`auth_google.py`) : jeton de session signé, émis après
   vérification d'un jeton d'identité Google. C'est le mode normal dès que
   `HORIZON_GOOGLE_CLIENT_ID` est défini.
2. **Jeton statique** `HORIZON_ADMIN_TOKEN` : conservé comme solution de repli
   mono-poste (dépannage, scripts locaux).

Comportement :

- si aucun des deux n'est configuré, l'API reste ouverte sur `127.0.0.1`
  (usage mono-poste, comportement historique préservé) ;
- sinon, toute opération d'écriture exige `Authorization: Bearer <jeton>` ou
  `X-Horizon-Token: <jeton>` ;
- aucune valeur de jeton n'est jamais renvoyée par une réponse ou un journal.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status

from .auth_google import verify_session_token

TOKEN_ENV = "HORIZON_ADMIN_TOKEN"


def _configured_token() -> str | None:
    token = os.getenv(TOKEN_ENV, "").strip()
    return token or None


def auth_enabled() -> bool:
    """Indique si une authentification est réellement active."""
    return _configured_token() is not None


def _extract(header_value: str | None) -> str | None:
    if not header_value:
        return None
    value = header_value.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip() or None
    return value or None


def _authenticate(provided: str | None) -> str | None:
    """Renvoie l'identité de l'acteur pour un jeton fourni, ou None."""
    if not provided:
        return None
    payload = verify_session_token(provided)
    if payload is not None:
        return str(payload.get("email") or "owner")
    expected = _configured_token()
    if expected and secrets.compare_digest(provided, expected):
        return "local-admin"
    return None


def require_admin(
    authorization: str | None = Header(default=None),
    x_horizon_token: str | None = Header(default=None),
) -> str:
    """Dépendance FastAPI : renvoie l'identité de l'acteur ou lève 401.

    Sans aucun jeton configuré, renvoie `local-admin` (mode mono-poste).
    """
    provided = _extract(authorization) or _extract(x_horizon_token)
    if _configured_token() is None and provided is None:
        return "local-admin"
    actor = _authenticate(provided)
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton administrateur requis.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return actor


def token_status() -> dict[str, object]:
    """État non sensible de l'authentification, pour /capabilities."""
    return {
        "auth_enabled": auth_enabled(),
        "token_env": TOKEN_ENV,
        "mode": "single_admin" if auth_enabled() else "local_open",
    }
