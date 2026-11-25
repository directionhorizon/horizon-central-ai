"""Applique le correctif de rapprochement par nom aux Edge Functions MAYELA.

Contexte : la synchronisation publicitaire cherche une campagne existante par
`org_id` + `source` + `nom`. Le filtre `source` empêche de rejoindre une
campagne saisie à la main, ce qui crée un doublon au même nom. On aligne les
deux fonctions sur la regle `org_id` + `plateforme` + `nom`.

Usage :
    $env:SUPABASE_ACCESS_TOKEN='sbp_...'
    python scripts/fix_mayela_function_lookup.py            # diagnostic seul
    python scripts/fix_mayela_function_lookup.py --apply    # ecrit si possible

Le jeton d'acces (Personal Access Token Supabase) est lu dans l'environnement :
il n'est jamais passe en argument, jamais ecrit sur disque, jamais affiche.

Le script :
1. lit la liste des fonctions du projet ;
2. telecharge le corps de chaque fonction visee et le **sauvegarde** ;
3. verifie que la chaine a remplacer est presente **exactement une fois** ;
4. affiche la correction, sans ecrire (mode diagnostic par defaut) ;
5. avec `--apply`, refuse d'ecrire si le corps recu n'est pas du source pur.

ATTENTION : l'API renvoie un conteneur **ESZIP** (source suivi du bundle des
dependances). Le renvoyer tel quel corrompt la fonction : d'ou le refus.
La correction se fait donc au numero de ligne, dans le tableau de bord.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://api.supabase.com"
PROJECT_REF = "ymqdmfsqtkmlmwffqskt"
TOKEN_ENV = "SUPABASE_ACCESS_TOKEN"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "backups" / "functions"

#: (slug, libelle, chaine attendue, chaine corrigee)
FIXES: list[tuple[str, str, str, str]] = [
    (
        "social-facebook",
        "Meta — rattrapage par nom",
        '.eq("org_id", orgId).eq("source", "meta").eq("plateforme", "facebook").eq("nom", nom)',
        '.eq("org_id", orgId).eq("plateforme", "facebook").eq("nom", nom)',
    ),
    (
        "social-tiktok",
        "TikTok — rattrapage par nom",
        '.eq("org_id", orgId).eq("source", "tik").eq("nom", nom)',
        '.eq("org_id", orgId).eq("plateforme", "tiktok").eq("nom", nom)',
    ),
]


def _headers() -> dict[str, str]:
    token = (os.getenv(TOKEN_ENV) or "").strip()
    if not token:
        raise SystemExit(f"{TOKEN_ENV} absent de l'environnement.")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _metadata(client: httpx.Client, slug: str) -> dict:
    r = client.get(f"{API}/v1/projects/{PROJECT_REF}/functions/{slug}")
    if r.status_code >= 400:
        raise SystemExit(f"{slug} : lecture des metadonnees refusee (HTTP {r.status_code}).")
    data = r.json()
    return data if isinstance(data, dict) else {}


def _body(client: httpx.Client, slug: str) -> str:
    r = client.get(f"{API}/v1/projects/{PROJECT_REF}/functions/{slug}/body")
    if r.status_code >= 400:
        raise SystemExit(f"{slug} : lecture du code refusee (HTTP {r.status_code}).")
    try:
        payload = r.json()
    except ValueError:
        return r.text
    if isinstance(payload, dict):
        return str(payload.get("body") or payload.get("code") or "")
    return r.text


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Corrige le rapprochement par nom des Edge Functions MAYELA."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="ecrit la correction (refuse si le corps recu n'est pas du source pur)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"dossier des sauvegardes (defaut : {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv[1:])

    headers = _headers()
    out_dir = Path(args.out)
    stamp = _stamp()
    print(f"Projet : {PROJECT_REF}")
    print(f"Sauvegardes : {out_dir}")

    changed = 0
    problems = 0
    with httpx.Client(timeout=60.0, headers=headers) as client:
        for slug, label, old, new in FIXES:
            print(f"\n=== {slug} — {label} ===")
            try:
                meta = _metadata(client, slug)
                code = _body(client, slug)
            except SystemExit as error:
                print(f"  {error}")
                problems += 1
                continue
            if not code.strip():
                print("  code vide : fonction ignoree.")
                problems += 1
                continue

            out_dir.mkdir(parents=True, exist_ok=True)
            backup = out_dir / f"{slug}_{stamp}.ts"
            backup.write_text(code, encoding="utf-8")
            print(f"  sauvegarde      : {backup}")
            print(f"  taille du code  : {len(code)} caracteres")

            count = code.count(old)
            print(f"  occurrences a corriger : {count}")
            if count == 0:
                problems += 1
                print("  AUCUNE CORRESPONDANCE — voici le code reel autour de la recherche par nom :")
                print(_context(code, old))
                continue
            if count > 1:
                problems += 1
                print("  plusieurs correspondances : correction annulee pour cette fonction.")
                continue

            fixed = code.replace(old, new)
            if not args.apply:
                print("  mode diagnostic (defaut) : aucune ecriture envoyee.")
                continue
            # Le corps renvoye par l'API est un conteneur ESZIP (code source suivi
            # du bundle des dependances). Le renvoyer tel quel CORROMPT la fonction.
            # On refuse donc d'ecrire tant que le corps ne ressemble pas a du
            # source pur : c'est un garde-fou, pas une precaution de style.
            longues = [line for line in code.splitlines() if len(line) > 400]
            if "ESZIP" in code[:64] or longues:
                problems += 1
                print(
                    "  ECRITURE REFUSEE : le corps recu n'est pas du source pur "
                    f"({len(longues)} ligne(s) > 400 caracteres, en-tete ESZIP="
                    f"{'oui' if 'ESZIP' in code[:64] else 'non'})."
                )
                print("  -> utiliser le numero de ligne dans le tableau de bord Supabase.")
                continue

            payload: dict[str, object] = {"name": meta.get("name") or slug, "body": fixed}
            if "verify_jwt" in meta:
                payload["verify_jwt"] = bool(meta.get("verify_jwt"))
            response = client.patch(
                f"{API}/v1/projects/{PROJECT_REF}/functions/{slug}", json=payload
            )
            if response.status_code >= 400:
                problems += 1
                print(f"  ECHEC de l'envoi (HTTP {response.status_code}) : {response.text[:300]}")
                continue

            after = _body(client, slug)
            ok = new in after and old not in after
            print(f"  envoi HTTP {response.status_code} — verification : {'OK' if ok else 'A VERIFIER'}")
            if ok:
                changed += 1
            else:
                problems += 1

    print(f"\nResume : {changed} fonction(s) corrigee(s), {problems} point(s) a examiner.")
    if not args.apply:
        print("Mode diagnostic : rien n'a ete ecrit. Utiliser --apply pour tenter l'ecriture.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

