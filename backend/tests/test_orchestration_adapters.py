"""Tests de la couche d'abstraction d'orchestration (Universal Manager).

Objectif : garantir que l'exécution n'est plus codée en dur sur Hermes.
HORIZON choisit un système par son `kind` ; un type inconnu est refusé
proprement, et un branchement non activé ne fabrique aucune disponibilité.
"""
from __future__ import annotations

from horizon.adapters import available_kinds, get_adapter


def test_registre_expose_hermes_et_natif():
    kinds = {item["kind"] for item in available_kinds()}
    assert "hermes" in kinds
    assert "horizon" in kinds


def test_kind_inconnu_non_resolu():
    assert get_adapter("inexistant") is None
    assert get_adapter("") is None


def test_route_kinds(client):
    response = client.get("/api/v1/orchestrators/kinds")
    assert response.status_code == 200
    kinds = {item["kind"] for item in response.json()["items"]}
    assert "hermes" in kinds


def test_dispatch_refuse_un_kind_inconnu(client):
    project = client.post("/api/v1/projects", json={"name": "Projet UOIM"}).json()
    system = client.post(
        "/api/v1/orchestrators",
        json={"name": "Systeme exotique", "kind": "exotique"},
    ).json()
    mission = client.post(
        "/api/v1/missions",
        json={
            "project_id": project["id"],
            "title": "Mission UOIM",
            "orchestrator_id": system["id"],
        },
    ).json()

    response = client.post(f"/api/v1/missions/{mission['id']}/dispatch", json={})
    assert response.status_code == 409
    assert "non pris en charge" in response.json()["detail"]


def test_dispatch_vers_natif_horizon_reste_honnete(client):
    project = client.post("/api/v1/projects", json={"name": "Projet natif"}).json()
    system = client.post(
        "/api/v1/orchestrators",
        json={"name": "Systeme interne", "kind": "horizon"},
    ).json()
    mission = client.post(
        "/api/v1/missions",
        json={
            "project_id": project["id"],
            "title": "Mission native",
            "orchestrator_id": system["id"],
        },
    ).json()

    response = client.post(f"/api/v1/missions/{mission['id']}/dispatch", json={})
    assert response.status_code == 502
    assert "interne" in response.json()["detail"]
