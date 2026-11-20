"""Connexion AUTOMATIQUE des réseaux sociaux par OAuth (Meta, TikTok).

Aucun jeton n'est saisi à la main : l'utilisateur autorise une fois dans son
navigateur, le jeton est récupéré, stocké dans un fichier local (jamais en base,
jamais exposé par l'API, jamais journalisé) puis réutilisé par les mains.

Important : Facebook/Instagram utilisent **OAuth Meta** et TikTok **OAuth TikTok**
(Login Kit). Google ne sert pas à ces plateformes.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from .db import DB_PATH

TIMEOUT_S = 20.0
GRAPH = "https://graph.facebook.com/v21.0"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

PROVIDERS: dict[str, dict[str, Any]] = {
    "meta": {
        "label": "Facebook / Instagram (Meta)",
        "authorize_url": "https://www.facebook.com/v21.0/dialog/oauth",
        "client_id_env": "HORIZON_META_APP_ID",
        "client_secret_env": "HORIZON_META_APP_SECRET",
        "redirect_env": "HORIZON_META_REDIRECT_URI",
        "scope": (
            "pages_show_list,pages_manage_posts,pages_read_engagement,"
            "instagram_basic,instagram_content_publish"
        ),
    },
    "tiktok": {
        "label": "TikTok",
        "authorize_url": "https://www.tiktok.com/v2/auth/authorize/",
        "client_id_env": "HORIZON_TIKTOK_CLIENT_KEY",
        "client_secret_env": "HORIZON_TIKTOK_CLIENT_SECRET",
        "redirect_env": "HORIZON_TIKTOK_REDIRECT_URI",
        "scope": "user.info.basic,video.publish",
    },
    "google": {
        "label": "Gmail (Google)",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "client_id_env": "HORIZON_GOOGLE_CLIENT_ID",
        "client_secret_env": "HORIZON_GOOGLE_CLIENT_SECRET",
        "redirect_env": "HORIZON_GOOGLE_REDIRECT_URI",
        "scope": "https://www.googleapis.com/auth/gmail.send",
        "extra": {"access_type": "offline", "prompt": "consent"},
    },
}


class OAuthError(RuntimeError):
    """Erreur de connexion OAuth, message lisible et sans secret."""


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def new_state() -> str:
    return secrets.token_urlsafe(24)


def secret_store_path() -> Path:
    return DB_PATH.parent / "connector_secrets.json"


def _load_store() -> dict[str, Any]:
    path = secret_store_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_store(store: dict[str, Any]) -> None:
    path = secret_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def store_secret(integration_id: str, provider: str, payload: dict[str, Any]) -> None:
    store = _load_store()
    store[integration_id] = {
        "provider": provider,
        "stored_at": int(time.time()),
        **payload,
    }
    _save_store(store)


def load_secret(integration_id: str) -> dict[str, Any] | None:
    return _load_store().get(integration_id)


def provider_status() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, cfg in PROVIDERS.items():
        result[key] = {
            "label": cfg["label"],
            "configured": bool(_env(cfg["client_id_env"]) and _env(cfg["client_secret_env"])),
            "redirect_uri": _env(cfg["redirect_env"]),
            "scope": cfg["scope"],
        }
    return result


def build_authorize_url(provider: str, state: str) -> str:
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise OAuthError("Fournisseur OAuth inconnu.")
    client_id = _env(cfg["client_id_env"])
    redirect = _env(cfg["redirect_env"])
    if not client_id or not redirect:
        raise OAuthError(f"{cfg['label']} n'est pas configuré (app et URL de redirection).")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "state": state,
        "scope": cfg["scope"],
        "response_type": "code",
    }
    params.update(cfg.get("extra") or {})
    return f"{cfg['authorize_url']}?{urlencode(params)}"


async def exchange_code(provider: str, code: str) -> dict[str, Any]:
    """Échange le code d'autorisation contre un jeton (appel réseau réel)."""
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        raise OAuthError("Fournisseur OAuth inconnu.")
    client_id = _env(cfg["client_id_env"])
    client_secret = _env(cfg["client_secret_env"])
    redirect = _env(cfg["redirect_env"])
    if not client_id or not client_secret or not redirect:
        raise OAuthError(f"{cfg['label']} n'est pas configuré.")
    if not code:
        raise OAuthError("Code d'autorisation manquant.")
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        if provider == "meta":
            response = await client.get(
                f"{GRAPH}/oauth/access_token",
                params={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect,
                    "code": code,
                },
            )
        elif provider == "google":
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect,
                    "grant_type": "authorization_code",
                },
            )
        else:
            response = await client.post(
                TIKTOK_TOKEN_URL,
                data={
                    "client_key": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect,
                },
            )
    if response.status_code >= 400:
        raise OAuthError(f"{cfg['label']} a refusé l'échange (HTTP {response.status_code}).")
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise OAuthError(f"{cfg['label']} n'a pas renvoyé de jeton.")
    return {
        "access_token": token,
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "open_id": data.get("open_id"),
    }
