"""Applique et deploie le correctif de rapprochement par nom (fonctions MAYELA).

Lit le code source **local** (tel que telecharge depuis le tableau de bord
Supabase, donc identique a ce que montre l'editeur), applique la correction,
puis met a jour la fonction via la Management API.

Usage :
    $env:SUPABASE_ACCESS_TOKEN='sbp_...'
    python scripts/deploy_mayela_function_fix.py --dry-run
    python scripts/deploy_mayela_function_fix.py

Le jeton est lu dans l'environnement : jamais en argument, jamais affiche.

Pourquoi le code local et non celui de l'API : l'API renvoie un conteneur
ESZIP compile, inutilisable pour une modification fiable.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://api.supabase.com"
PROJECT_REF = "ymqdmfsqtkmlmwffqskt"
TOKEN_ENV = "SUPABASE_ACCESS_TOKEN"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backups" / "functions" / "src"
BACKUP = ROOT / "backups" / "functions" / "before_fix"

#: (slug, libelle, chaine attendue, chaine corrigee)
FIXES: list[tuple[str, str, str, str]] = [
    (
        "social-facebook",
        "Meta — rapprochement par nom",
        '.eq("org_id", orgId).eq("source", "meta").eq("plateforme", "facebook").eq("nom", nom)',
        '.eq("org_id", orgId).eq("plateforme", "facebook").eq("nom", nom)',
    ),
    (
        "social-tiktok",
        "TikTok — rapprochement par nom",
        '.eq("org_id", orgId).eq("source", "tik").eq("nom", nom)',
        '.eq("org_id", orgId).eq("plateforme", "tiktok").eq("nom", nom)',
    ),
]


def _headers() -> dict[str, str]:
    token = (os.getenv(TOKEN_ENV) or "").strip()
    if not token:
        raise SystemExit(f"{TOKEN_ENV} absent de l'environnement.")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _line_of(text: str, needle: str) -> int:
    for index, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return index
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Corrige et deploie les fonctions MAYELA.")
    parser.add_argument("--dry-run", action="store_true", help="n'envoie rien")
    args = parser.parse_args(argv[1:])

    headers = _headers()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    BACKUP.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=120.0, headers=headers) as client:
        for slug, label, old, new in FIXES:
            print(f"\n=== {slug} — {label} ===")
            source_file = SRC / slug / "index.ts"
            if not source_file.is_file():
                print(f"  source locale absente : {source_file}")
                continue
            code = source_file.read_text(encoding="utf-8")
            (BACKUP / f"{slug}_{stamp}.ts").write_text(code, encoding="utf-8")
            print(f"  source locale : {len(code.splitlines())} lignes")

            count = code.count(old)
            line = _line_of(code, old)
            print(f"  ligne concernee : {line}")
            print(f"  occurrences a corriger : {count}")
            if count != 1:
                print("  correction annulee : il faut exactement une occurrence.")
                continue

            fixed = code.replace(old, new)
            if args.dry_run:
                print("  --dry-run : rien n'est envoye.")
                continue

            meta = client.get(f"{API}/v1/projects/{PROJECT_REF}/functions/{slug}")
            meta_data = meta.json() if meta.status_code < 400 else {}
            payload: dict[str, object] = {
                "name": (meta_data or {}).get("name") or slug,
                "body": fixed,
            }
            if isinstance(meta_data, dict) and "verify_jwt" in meta_data:
                payload["verify_jwt"] = bool(meta_data.get("verify_jwt"))
            response = client.patch(
                f"{API}/v1/projects/{PROJECT_REF}/functions/{slug}", json=payload
            )
            if response.status_code >= 400:
                print(f"  ECHEC (HTTP {response.status_code}) : {response.text[:400]}")
                continue
            print(f"  envoi HTTP {response.status_code}")

            after = client.get(f"{API}/v1/projects/{PROJECT_REF}/functions/{slug}/body")
            blob = after.text
            ok_new = new in blob
            ok_old = old in blob
            print(f"  verification : nouvelle chaine presente={ok_new} | ancienne encore presente={ok_old}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
