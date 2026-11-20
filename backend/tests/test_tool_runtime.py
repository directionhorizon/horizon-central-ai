"""Tests de l'exécution des mains (outils).

Objectif : les mains branchées s'exécutent réellement dans l'espace de travail
autorisé, une main non branchée refuse honnêtement, et une main n'est utilisable
par un agent que si elle lui a été attribuée.
"""
from __future__ import annotations

from horizon.schema import FAS_SEED


def test_main_fichier_ecrire_lire_lister(client):
    written = client.post(
        "/api/v1/tools/tool-file-write/run",
        json={"params": {"path": "note.txt", "content": "bonjour"}},
    )
    assert written.status_code == 200, written.text

    read = client.post(
        "/api/v1/tools/tool-file-read/run", json={"params": {"path": "note.txt"}}
    )
    assert read.json()["result"]["content"] == "bonjour"

    listed = client.post("/api/v1/tools/tool-file-list/run", json={"params": {"path": "."}})
    assert "note.txt" in listed.json()["result"]["items"]


def test_main_fichier_refuse_hors_espace(client):
    response = client.post(
        "/api/v1/tools/tool-file-read/run", json={"params": {"path": "../../secret.txt"}}
    )
    assert response.status_code == 400
    assert "espace de travail" in response.json()["detail"]


def test_main_code_python(client):
    response = client.post(
        "/api/v1/tools/tool-code-python/run", json={"params": {"code": "print(2 + 3)"}}
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["stdout"].strip() == "5"


def test_main_non_branchee_refuse(client):
    response = client.post("/api/v1/tools/tool-phone-call/run", json={"params": {}})
    assert response.status_code == 501
    assert "pas encore branchée" in response.json()["detail"]


def test_permission_par_agent(client):
    agent = client.get(
        "/api/v1/agents",
        params={"orchestrator_id": FAS_SEED["id"], "role": "orchestrator"},
    ).json()["items"][0]

    refused = client.post(
        "/api/v1/tools/tool-file-list/run",
        json={"agent_id": agent["id"], "params": {"path": "."}},
    )
    assert refused.status_code == 403

    client.post(f"/api/v1/agents/{agent['id']}/tools/tool-file-list")
    allowed = client.post(
        "/api/v1/tools/tool-file-list/run",
        json={"agent_id": agent["id"], "params": {"path": "."}},
    )
    assert allowed.status_code == 200


def test_liste_indique_executable(client):
    body = client.get("/api/v1/tools").json()
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id["tool-file-read"]["executable"] is True
    assert by_id["tool-phone-call"]["executable"] is False
