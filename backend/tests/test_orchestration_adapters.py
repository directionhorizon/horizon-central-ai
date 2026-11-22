"""Tests de la couche d'abstraction d'orchestration (Universal Manager).

Objectif : garantir que l'exécution n'est plus codée en dur sur Hermes.
HORIZON choisit un système par son `kind` ; un type inconnu est refusé
proprement. L'exécution native (kind `horizon`) est couverte par
`test_native_engine.py`.
"""
from __future__ import annotations

from horizon.adapters import available_kinds, get_adapter


def test_registre_expose_hermes_et_natif():
    kinds = {item["kind"] for item in available_kinds()}
    assert "hermes" in kinds
    assert "horizon" in kinds


def test_aucune_fiche_hermes_dans_le_registre(client):
    """Hermes n'est pas un système d'orchestration : aucune fiche ne doit le nommer."""
    items = client.get("/api/v1/orchestrators").json()["items"]
    ids = {item["id"] for item in items}
    assert "orchestrator-hermes" not in ids
    assert "system-first-agentic" in ids


def test_le_fas_est_le_systeme_de_repli(client):
    """Une mission sans orchestrateur explicite part vers le FAS, jamais vers Hermes."""
    from horizon.schema import DEFAULT_ORCHESTRATOR_ID

    assert DEFAULT_ORCHESTRATOR_ID == "system-first-agentic"


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


# La couverture de l'exécution native est dans test_native_engine.py.
