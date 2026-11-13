"""Authentification Google (OpenID Connect) pour un propriétaire unique.

Modèle retenu : **un seul utilisateur (le propriétaire), plusieurs appareils**.

Fonctionnement :

1. Le frontend obtient un jeton d'identité Google via Google Identity Services
   (aucun secret client n'est nécessaire : seul l'identifiant client public est
   utilisé).
2. Le backend vérifie ce jeton auprès de Google (endpoint ``tokeninfo``) :
   signature, audience, émetteur, expiration, adresse vérifiée.
3. Le backend émet ensuite **son propre jeton de session** signé en HMAC-SHA256
   (stdlib uniquement), révocable, tracé en base locale dans ``auth_sessions``.

Le jeton de session remplace le jeton statique ``HORIZON_ADMIN_TOKEN`` pour les
opérations d'écriture : il identifie l'appareil et permet la révocation à
distance (perte ou vol d'un appareil).

Aucune dépendance externe hors ``httpx`` (déjà présent pour la synchronisation).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .db import DB_PATH, connect, now

CLIENT_ID_ENV = "HORIZON_GOOGLE_CLIENT_ID"
OWNER_EMAIL_ENV = "HORIZON_OWNER_EMAIL"
SECRET_ENV = "HORIZON_AUTH_SECRET"
LOCAL_LOGIN_ENV = "HORIZON_ALLOW_LOCAL_LOGIN"
TTL_ENV = "HORIZON_AUTH_TOKEN_TTL_S"

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
TIMEOUT_S = 10.0
DEFAULT_TTL_S = 30 * 24 * 3600  # 30 jours


class AuthError(RuntimeError):
    """Erreur d'authentification. Le message ne contient aucun secret."""


def _ttl() -> int:
    raw = os.getenv(TTL_ENV, "").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_TTL_S
    return value if value > 0 else DEFAULT_TTL_S


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _secret_path() -> Path:
    return DB_PATH.parent / ".auth_secret"


def _secret() -> bytes:
    """Secret de signature : variable d'environnement, sinon fichier local persistant.

    Le fichier est créé au premier démarrage avec des droits restreints. Il n'est
    jamais exposé par une API ni journalisé.
    """
    configured = os.getenv(SECRET_ENV, "").strip()
    if configured:
        return configured.encode("utf-8")
    path = _secret_path()
    if path.is_file():
        stored = path.read_bytes().strip()
        if stored:
            return stored
    path.parent.mkdir(parents=True, exist_ok=True)
    generated = secrets.token_urlsafe(48).encode("ascii")
    path.write_bytes(generated)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return generated


def _ensure_table() -> None:
    with connect() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                device TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )"""
        )
        db.commit()


def _sign(body: str) -> str:
    digest = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest()
    return _b64url(digest)


def google_configured() -> bool:
    return bool(os.getenv(CLIENT_ID_ENV, "").strip())


def local_login_enabled() -> bool:
    """Connexion locale sans Google (mode mono-poste / dépannage).

    Activée par défaut : l'application reste utilisable avant que le client
    Google ne soit créé. Désactiver avec ``HORIZON_ALLOW_LOCAL_LOGIN=0``.
    """
    raw = os.getenv(LOCAL_LOGIN_ENV, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def owner_email() -> str | None:
    value = os.getenv(OWNER_EMAIL_ENV, "").strip().lower()
    return value or None


def issue_session_token(email: str, subject: str = "", device: str = "") -> dict[str, Any]:
    """Émet un jeton de session signé et l'enregistre (révocable)."""
    _ensure_table()
    session_id = uuid.uuid4().hex
    issued = int(time.time())
    expires = issued + _ttl()
    payload = {
        "jti": session_id,
        "sub": subject,
        "email": email.strip().lower(),
        "iat": issued,
        "exp": expires,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    token = f"{body}.{_sign(body)}"
    with connect() as db:
        db.execute(
            "INSERT INTO auth_sessions(id,email,subject,device,created_at,expires_at)"
            " VALUES(?,?,?,?,?,?)",
            (session_id, payload["email"], subject, device.strip()[:120], now(), _iso(expires)),
        )
        db.commit()
    return {"token": token, "expires_at": _iso(expires), "session_id": session_id}


def verify_session_token(token: str | None) -> dict[str, Any] | None:
    """Vérifie signature + expiration + révocation. Renvoie la charge utile ou None."""
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    try:
        expected = _sign(body)
    except (ValueError, UnicodeEncodeError):
        return None
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64url_decode(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        expires = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return None
    if expires < int(time.time()):
        return None
    session_id = str(payload.get("jti", ""))
    if not session_id:
        return None
    try:
        _ensure_table()
        with connect() as db:
            row = db.execute(
                "SELECT revoked_at FROM auth_sessions WHERE id=?", (session_id,)
            ).fetchone()
    except Exception:  # base indisponible : on refuse plutôt que d'ouvrir
        return None
    if row is None or row["revoked_at"]:
        return None
    return payload


def revoke_session(token: str | None) -> bool:
    """Révoque un jeton (déconnexion ou perte d'appareil)."""
    payload = verify_session_token(token)
    if payload is None:
        return False
    with connect() as db:
        db.execute(
            "UPDATE auth_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (now(), payload["jti"]),
        )
        db.commit()
    return True


def list_devices() -> list[dict[str, Any]]:
    _ensure_table()
    with connect() as db:
        rows = db.execute(
            "SELECT id,email,device,created_at,expires_at,revoked_at FROM auth_sessions"
            " ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return [dict(row) for row in rows]


def revoke_device(session_id: str) -> bool:
    _ensure_table()
    with connect() as db:
        cursor = db.execute(
            "UPDATE auth_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
            (now(), session_id),
        )
        db.commit()
        return cursor.rowcount > 0


def verify_google_credential(credential: str) -> dict[str, Any]:
    """Vérifie un jeton d'identité Google et renvoie l'identité du propriétaire."""
    client_id = os.getenv(CLIENT_ID_ENV, "").strip()
    if not client_id:
        raise AuthError("Google n'est pas configuré : HORIZON_GOOGLE_CLIENT_ID est absent.")
    if not credential.strip():
        raise AuthError("Jeton Google manquant.")
    try:
        response = httpx.get(
            TOKENINFO_URL, params={"id_token": credential.strip()}, timeout=TIMEOUT_S
        )
    except httpx.HTTPError as exc:
        raise AuthError(f"Vérification Google injoignable ({type(exc).__name__}).") from exc
    if response.status_code >= 400:
        raise AuthError("Jeton Google refusé par Google.")
    try:
        data = response.json()
    except ValueError as exc:
        raise AuthError("Réponse Google illisible.") from exc
    if not isinstance(data, dict):
        raise AuthError("Réponse Google inattendue.")
    if str(data.get("aud", "")) != client_id:
        raise AuthError("Jeton Google émis pour une autre application.")
    issuer = str(data.get("iss", ""))
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise AuthError("Émetteur Google invalide.")
    try:
        expires = int(data.get("exp", 0))
    except (TypeError, ValueError) as exc:
        raise AuthError("Expiration Google illisible.") from exc
    if expires < int(time.time()):
        raise AuthError("Jeton Google expiré.")
    if str(data.get("email_verified", "")).strip().lower() not in {"true", "1"}:
        raise AuthError("Adresse Google non vérifiée.")
    email = str(data.get("email", "")).strip().lower()
    if not email:
        raise AuthError("Adresse Google absente du jeton.")
    allowed = owner_email()
    if allowed and email != allowed:
        raise AuthError("Ce compte Google n'est pas le propriétaire de cette instance.")
    return {
        "email": email,
        "sub": str(data.get("sub", "")),
        "name": str(data.get("name", "")),
        "picture": str(data.get("picture", "")),
    }


def auth_status() -> dict[str, Any]:
    """État non sensible de l'authentification, exposé au frontend."""
    client_id = os.getenv(CLIENT_ID_ENV, "").strip()
    return {
        "google_enabled": bool(client_id),
        "client_id": client_id or None,
        "owner_email": owner_email(),
        "local_login_enabled": local_login_enabled(),
        "token_ttl_s": _ttl(),
        "mode": "google" if client_id else "local",
    }
