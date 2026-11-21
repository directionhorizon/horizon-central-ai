"""Test de bout en bout d'une mission HORIZON sur une instance réelle.

Ce script vérifie le parcours complet : création de la mission, ajout d'une
étape, dispatch vers le système d'orchestration choisi, puis suivi de
l'exécution jusqu'à un état terminal. Il affiche l'état final et un extrait de
la sortie produite.

Aucun secret n'est affiché : le jeton est lu dans l'environnement ou passé en
argument, jamais écrit sur la console.

Usage :
    python tools/run_mission.py --project-id project-default \\
        --title "Test de bout en bout" --description "Vérifie le parcours complet."

Variables d'environnement :
    HORIZON_ADMIN_TOKEN   jeton d'administration (obligatoire pour écrire)
    HORIZON_BASE_URL      URL de l'instance (défaut : https://horizon.mayela-crm.com)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

TERMINAL = {"completed", "failed", "cancelled", "stopped"}


def _request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Appelle l'API HORIZON et renvoie la réponse JSON décodée."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("X-Horizon-Token", token)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body or "{}")


def _fail(message: str) -> None:
    print("ECHEC : " + message)
    raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("HORIZON_BASE_URL", "https://horizon.mayela-crm.com"))
    parser.add_argument("--token", default=os.getenv("HORIZON_ADMIN_TOKEN", ""))
    parser.add_argument("--project-id", default="project-default")
    parser.add_argument("--title", default="Test de bout en bout")
    parser.add_argument("--description", default="Vérifie le parcours complet : création, dispatch, exécution, mémoire.")
    parser.add_argument("--orchestrator-id", default="")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--interval", type=float, default=3.0)
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    token = (args.token or "").strip()
    if not token:
        _fail("aucun jeton fourni (HORIZON_ADMIN_TOKEN ou --token).")

    mission: dict[str, Any] | None = None
    try:
        mission = _request(
            "POST",
            base + "/api/v1/missions",
            token,
            {
                "project_id": args.project_id,
                "title": args.title,
                "description": args.description,
                "orchestrator_id": args.orchestrator_id or None,
            },
        )
        mission_id = mission.get("id") or mission.get("mission_id")
        if not mission_id:
            _fail("réponse de création sans identifiant de mission.")
        print("mission créée : " + mission_id)

        _request(
            "POST",
            base + "/api/v1/missions/" + mission_id + "/steps",
            token,
            {"title": "Exécuter la mission demandée", "position": 0},
        )
        print("étape ajoutée")

        dispatch = _request(
            "POST",
            base + "/api/v1/missions/" + mission_id + "/dispatch",
            token,
            {"orchestrator_id": args.orchestrator_id or None},
        )
        run = dispatch.get("run") or {}
        run_id = run.get("id")
        if not run_id:
            _fail("dispatch sans identifiant d'exécution : " + json.dumps(dispatch)[:300])
        print("dispatch accepté (run " + str(run_id) + ")")

        deadline = time.time() + args.timeout
        current = run
        while time.time() < deadline:
            status = str(current.get("status") or "")
            if status in TERMINAL:
                break
            time.sleep(args.interval)
            current = _request(
                "GET",
                base + "/api/v1/missions/" + mission_id + "/runs/" + str(run_id) + "?refresh=1",
                token,
            )

        status = str(current.get("status") or "")
        print("statut final : " + (status or "(inconnu)"))
        output = current.get("output")
        if isinstance(output, (dict, list)):
            preview = json.dumps(output, ensure_ascii=False)[:800]
        else:
            preview = str(output or "")[:800]
        if preview:
            print("sortie : " + preview)
        error = current.get("error")
        if error:
            print("erreur : " + str(error)[:800])

        if status not in TERMINAL:
            _fail("délai dépassé avant un état terminal (dernier statut : " + (status or "inconnu") + ").")
        if status != "completed":
            _fail("la mission ne s'est pas terminée correctement (statut : " + status + ").")
        print("OK : mission exécutée de bout en bout.")
        return 0
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:600]
        _fail("HTTP " + str(error.code) + " : " + detail)
    except urllib.error.URLError as error:
        _fail("service injoignable : " + str(error.reason))
    return 1


if __name__ == "__main__":
    sys.exit(main())
