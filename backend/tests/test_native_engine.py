"""Tests du moteur d'exécution natif de HORIZON (FIRST AGENTIC SYSTEM).

Objectif : une mission confiée au système natif est réellement exécutée de bout
en bout par son agent orchestrateur, via le fournisseur LLM configuré, et le
résultat est persisté. Le fournisseur est simulé : aucun appel réseau réel.
"""
from __future__ import annotations

import pytest

from horizon import llm
from horizon.schema import FAS_SEED


def _clear_providers(client) -> None:
    for item in client.get("/api/v1/models").json()["items"]:
        client.delete(f"/api/v1/models/{item['id']}")


@pytest.fixture()
def provider(client):
    created = client.post(
        "/api/v1/models",
        json={
            "name": "Fournisseur de test",
            "base_url": "http://127.0.0.1:9/v1",
            "default_model": "modele-test",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def _fake_chat(response_text):
    async def _chat(row, messages, *, model=None, temperature=0.2, timeout_s=60.0):
        return {
            "content": response_text,
            "model": model or "modele-test",
            "provider_id": row.get("id"),
            "provider_name": row.get("name"),
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }

    return _chat


def test_fas_est_enregistre_avec_ses_agents(client):
    systems = client.get("/api/v1/orchestrators").json()["items"]
    fas = next((item for item in systems if item["id"] == FAS_SEED["id"]), None)
    assert fas is not None
    assert fas["name"] == "FIRST AGENTIC SYSTEM"
    assert fas["kind"] == "horizon"

    agents = client.get(
        "/api/v1/agents", params={"orchestrator_id": FAS_SEED["id"]}
    ).json()["items"]
    roles = {agent["role"] for agent in agents}
    assert "orchestrator" in roles
    assert len(agents) >= 4


def test_mission_native_executee_de_bout_en_bout(client, provider, monkeypatch):
    monkeypatch.setattr(llm, "chat", _fake_chat("Résultat natif de test."))
    project = client.post("/api/v1/projects", json={"name": "Projet FAS"}).json()
    mission = client.post(
        "/api/v1/missions",
        json={
            "project_id": project["id"],
            "title": "Mission native",
            "description": "Produire un résultat vérifiable.",
            "orchestrator_id": FAS_SEED["id"],
        },
    ).json()

    response = client.post(f"/api/v1/missions/{mission['id']}/dispatch", json={})
    assert response.status_code == 202, response.text
    run = response.json()["run"]
    assert run["status"] == "completed"
    assert run["output"] == "Résultat natif de test."
    assert run["run_id"].startswith("native-")

    mission_after = client.get(f"/api/v1/missions/{mission['id']}").json()
    assert mission_after["status"] == "completed"


def test_competences_injectees_dans_le_prompt_native(client, provider, monkeypatch):
    """Les compétences du système et de l'agent sont réellement injectées."""
    captured: dict = {}

    async def _capture(row, messages, *, model=None, temperature=0.2, timeout_s=60.0):
        captured["messages"] = messages
        return {
            "content": "ok",
            "model": model or "modele-test",
            "provider_id": row.get("id"),
            "provider_name": row.get("name"),
            "usage": {},
        }

    monkeypatch.setattr(llm, "chat", _capture)

    skill = client.post(
        "/api/v1/skills",
        json={"name": "Redaction de synthese", "category": "Analyse", "description": "Synthese claire."},
    ).json()
    client.post(f"/api/v1/orchestrators/{FAS_SEED['id']}/skills", json={"skill_id": skill["id"]})

    project = client.post("/api/v1/projects", json={"name": "Projet skills"}).json()
    mission = client.post(
        "/api/v1/missions",
        json={
            "project_id": project["id"],
            "title": "Mission avec competences",
            "orchestrator_id": FAS_SEED["id"],
        },
    ).json()
    response = client.post(f"/api/v1/missions/{mission['id']}/dispatch", json={})
    assert response.status_code == 202, response.text

    system = captured["messages"][0]["content"]
    assert "Redaction de synthese" in system
    assert "Compétences disponibles" in system


def test_mission_native_sans_fournisseur_refuse(client):
    _clear_providers(client)
    project = client.post("/api/v1/projects", json={"name": "Projet FAS sans modèle"}).json()
    mission = client.post(
        "/api/v1/missions",
        json={
            "project_id": project["id"],
            "title": "Mission sans modèle",
            "orchestrator_id": FAS_SEED["id"],
        },
    ).json()

    response = client.post(f"/api/v1/missions/{mission['id']}/dispatch", json={})
    assert response.status_code == 502
    assert "fournisseur" in response.json()["detail"].lower()
