"""Verifie une cle SasPay sans risque : aucune transaction reelle en bac a sable.

Usage :
    python scripts/check_saspay.py [--live]

Par defaut, le script vise le **bac a sable** (`sandbox-api.saspay.me`). Il
refuse de viser la production sans le drapeau `--live`, pour eviter qu'un test
d'integration ne cree une vraie session de paiement par inadvertance.

Ce qu'il fait :
1. lit `HORIZON_SASPAY_API_KEY` et `HORIZON_SASPAY_BASE_URL` dans `backend/.env` ;
2. appelle `GET /countries/` (public) pour verifier que l'API repond ;
3. cree une session de checkout d'un montant symbolique et affiche l'URL obtenue.

Aucune valeur secrete n'est imprimee : seuls les noms de variables et les
identifiants publics renvoyes par SasPay le sont.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "backend" / ".env"

LIVE_BASE = "https://api.saspay.me/api/v1"
SANDBOX_BASE = "https://sandbox-api.saspay.me/api/v1"

#: Montant symbolique du test, en XAF (devise sans decimale).
TEST_AMOUNT = "100.00"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verification d'une cle SasPay.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="autorise explicitement la production (cree une vraie session)",
    )
    args = parser.parse_args(argv[1:])

    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH)
    else:
        print(f"note : {ENV_PATH} introuvable, lecture de l'environnement seul")

    key = (os.getenv("HORIZON_SASPAY_API_KEY") or "").strip()
    configured_base = (os.getenv("HORIZON_SASPAY_BASE_URL") or "").strip()
    if not key:
        print("HORIZON_SASPAY_API_KEY absente : rien a verifier.")
        return 2

    base = (configured_base or LIVE_BASE).rstrip("/")
    live = base == LIVE_BASE.rstrip("/")
    print(f"Base visee : {base}")
    if live and not args.live:
        print(
            "Refus : la base est la production. Relancez avec --live si c'est "
            "vraiment voulu (une session reelle serait creee)."
        )
        return 2

    try:
        countries = httpx.get(f"{base}/countries/", timeout=20.0)
    except httpx.HTTPError as error:
        print(f"API injoignable ({type(error).__name__}).")
        return 1
    print(f"GET /countries/ -> HTTP {countries.status_code}")
    if countries.status_code < 400:
        try:
            items = countries.json()
            noms = [str(item.get("name") or "") for item in items if isinstance(item, dict)]
            congo = [nom for nom in noms if "congo" in nom.lower()]
            print(f"  pays disponibles : {len(noms)} | Congo : {congo or 'aucun'}")
        except ValueError:
            print("  reponse illisible")

    body = {
        "amount": TEST_AMOUNT,
        "currency": "XAF",
        "description": "Test de connectivite HORIZON",
        "customer_email": "test@horizon.local",
        "customer_name": "Test HORIZON",
    }
    try:
        response = httpx.post(
            f"{base}/checkout-sessions/",
            json=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=25.0,
        )
    except httpx.HTTPError as error:
        print(f"Creation injoignable ({type(error).__name__}).")
        return 1
    print(f"POST /checkout-sessions/ -> HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        print("  reponse illisible")
        return 1
    if response.status_code >= 400 or payload.get("success") is False:
        print("  refus : " + json.dumps(payload.get("error") or {}, ensure_ascii=False))
        return 1
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    print("  id           : " + str(data.get("id") or ""))
    print("  statut       : " + str(data.get("status") or ""))
    print("  checkout_url : " + str(data.get("checkout_url") or data.get("url") or ""))
    print("Cle acceptee. Rien n'a ete debite : une session ne debite qu'une fois payee.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
