"""Routes d'authentification (accès du propriétaire à l'application).

Contrat :

- ``GET  /api/v1/auth/config``   → configuration publique (client Google, mode)
- ``POST /api/v1/auth/google``   → vérifie un jeton Google, émet une session
- ``POST /api/v1/auth/local``    → session locale (si autorisée)
- ``GET  /api/v1/auth/me``       → identité de l'appareil courant
- ``POST /api/v1/auth/logout``   → révoque la session courante
- ``GET  /api/v1/auth/devices``  → appareils connectés
- ``POST /api/v1/auth/devices/{id}/revoke`` → révocation à distance

Aucun secret n'est jamais renvoyé : ni mot de passe, ni clé, ni jeton Google.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import _extract, require_admin
from ..auth_google import (
    AuthError,
    auth_status,
    issue_session_token,
    list_devices,
    local_login_enabled,
    revoke_device,
    revoke_session,
    verify_google_credential,
    verify_session_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class GoogleLogin(BaseModel):
    credential: str = Field(min_length=20, max_length=8192)
    device: str = Field(default="", max_length=120)


class LocalLogin(BaseModel):
    device: str = Field(default="", max_length=120)


def _token(authorization: str | None, x_horizon_token: str | None) -> str | None:
    return _extract(authorization) or _extract(x_horizon_token)


def _require_session(
    authorization: str | None = Header(default=None),
    x_horizon_token: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = verify_session_token(_token(authorization, x_horizon_token))
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session requise ou expirée.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


@router.get("/config")
def auth_config() -> dict[str, Any]:
    """Configuration publique : permet au frontend d'afficher le bon écran."""
    return auth_status()


@router.post("/google")
def auth_google(payload: GoogleLogin) -> dict[str, Any]:
    """Échange un jeton d'identité Google contre une session HORIZON."""
    try:
        identity = verify_google_credential(payload.credential)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    session = issue_session_token(
        identity["email"], subject=identity.get("sub", ""), device=payload.device
    )
    return {
        "token": session["token"],
        "expires_at": session["expires_at"],
        "user": {
            "email": identity["email"],
            "name": identity.get("name", ""),
            "picture": identity.get("picture", ""),
        },
    }


@router.post("/local")
def auth_local(payload: LocalLogin) -> dict[str, Any]:
    """Session locale sans Google (mode mono-poste).

    Désactivable avec ``HORIZON_ALLOW_LOCAL_LOGIN=0`` dès que Google est en place.
    """
    if not local_login_enabled():
        raise HTTPException(
            status_code=403, detail="Connexion locale désactivée sur cette instance."
        )
    session = issue_session_token("local-owner", subject="local", device=payload.device)
    return {
        "token": session["token"],
        "expires_at": session["expires_at"],
        "user": {"email": "local-owner", "name": "Propriétaire local", "picture": ""},
    }


@router.get("/me")
def auth_me(
    authorization: str | None = Header(default=None),
    x_horizon_token: str | None = Header(default=None),
) -> dict[str, Any]:
    payload = _require_session(authorization, x_horizon_token)
    return {
        "email": payload.get("email", ""),
        "subject": payload.get("sub", ""),
        "session_id": payload.get("jti", ""),
        "expires_at": payload.get("exp", 0),
    }


@router.post("/logout")
def auth_logout(
    authorization: str | None = Header(default=None),
    x_horizon_token: str | None = Header(default=None),
) -> dict[str, Any]:
    revoked = revoke_session(_token(authorization, x_horizon_token))
    return {"revoked": revoked}


@router.get("/devices")
def auth_devices(actor: str = Depends(require_admin)) -> dict[str, Any]:
    """Liste des appareils connectés.

    La liste contient des identifiants de session : elle exige donc le rôle
    administrateur, comme toute autre opération sensible.
    """
    return {"items": list_devices()}


@router.post("/devices/{session_id}/revoke")
def auth_revoke_device(
    session_id: str, actor: str = Depends(require_admin)
) -> dict[str, Any]:
    if not revoke_device(session_id):
        raise HTTPException(404, "Session introuvable ou déjà révoquée.")
    return {"revoked": True, "session_id": session_id}
