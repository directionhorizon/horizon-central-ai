"""Genere un jeton JWT Supabase pour un role en lecture seule, et l'ecrit dans un .env.

Usage :
    SUPABASE_JWT_SECRET=<secret> python scripts/make_supabase_jwt.py <env_path> <role> <ref> [jours]

Le secret est lu dans la variable d'environnement `SUPABASE_JWT_SECRET` : il n'est
jamais passe en argument (donc jamais visible dans l'historique du shell) et jamais
affiche. Seul le NOM de la variable ecrite est imprime, comme dans set_env.py.

Le jeton produit est signe en HS256 avec le secret JWT du projet Supabase
(Dashboard > Settings > API > JWT Settings > JWT Secret). Il porte le role demande,
ce qui permet a PostgREST d'appliquer les droits de ce role au lieu de ceux de
`anon` ou `service_role`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from set_env import upsert  # noqa: E402

DEFAULT_VAR = "HORIZON_MAYELA_SUPABASE_TOKEN"
DEFAULT_DAYS = 365


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_jwt(secret: str, role: str, ref: str, days: int) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "role": role,
        "iss": "supabase",
        "ref": ref,
        "iat": now,
        "exp": now + days * 86400,
    }
    signing_input = ".".join(
        _b64url(json.dumps(part, separators=(",", ":")).encode("utf-8"))
        for part in (header, payload)
    )
    signature = hmac.new(
        secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64url(signature)}"


def main(argv: list[str]) -> int:
    if len(argv) not in (4, 5):
        print("usage: make_supabase_jwt.py <env_path> <role> <ref> [jours]")
        return 2
    env_path, role, ref = Path(argv[1]), argv[2].strip(), argv[3].strip()
    try:
        days = int(argv[4]) if len(argv) == 5 else DEFAULT_DAYS
    except ValueError:
        print("jours invalide")
        return 2
    if not role or not ref:
        print("role et ref sont obligatoires")
        return 2
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not secret:
        print("SUPABASE_JWT_SECRET absent de l'environnement")
        return 2
    token = make_jwt(secret, role, ref, days)
    updated = upsert(env_path, {DEFAULT_VAR: token})
    print("Variables mises a jour : " + (", ".join(updated) if updated else "aucune"))
    print(f"Role : {role} | Projet : {ref} | Expiration : {days} jours")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
