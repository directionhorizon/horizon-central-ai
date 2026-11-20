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


def _configure_provider(client):
    created = client.post(
        "/api/v1/models",
        json={"name": "Fournisseur test", "base_url": "http://127.0.0.1:9/v1", "default_model": "m"},
    )
    assert created.status_code == 201, created.text


def _fake_chat(text):
    async def _chat(row, messages, *, model=None, temperature=0.2, timeout_s=60.0):
        return {
            "content": text,
            "model": model or "m",
            "provider_id": row.get("id"),
            "provider_name": row.get("name"),
            "usage": {},
        }

    return _chat


def test_main_planifier(client, monkeypatch):
    from horizon import llm

    _configure_provider(client)
    monkeypatch.setattr(llm, "chat", _fake_chat('{"title":"Plan","steps":[{"title":"Étape"}]}'))
    response = client.post(
        "/api/v1/tools/tool-plan/run", json={"params": {"request": "Construire une page"}}
    )
    assert response.status_code == 200, response.text
    assert "Plan" in response.json()["result"]["plan"]


def test_main_deleguer(client, monkeypatch):
    from horizon import llm
    from horizon.schema import FAS_SEED

    _configure_provider(client)
    monkeypatch.setattr(llm, "chat", _fake_chat("Travail délégué terminé."))
    response = client.post(
        "/api/v1/tools/tool-delegate/run",
        json={"params": {"system_id": FAS_SEED["id"], "task": "Rédiger un résumé"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["output"] == "Travail délégué terminé."
    assert response.json()["result"]["agent"]
