"""Tests du catalogue des mains (outils) des agents.

Objectif : les 6 familles (+ le contrôle) sont déclarées, une main est annoncée
honnêtement (état « planned » tant qu'elle n'est pas branchée, « ready » dès
qu'un gestionnaire existe), et une main peut être attribuée à un agent puis
retirée.
"""
from __future__ import annotations

from horizon.schema import FAS_SEED


def test_catalogue_couvre_les_sept_familles(client):
    body = client.get("/api/v1/tools").json()
    families = {item["family"] for item in body["items"]}
    for expected in ("machine", "monde", "donnees", "creation", "meta", "physique", "securite"):
        assert expected in families
    assert len(body["items"]) >= 40


def test_motion_design_declare(client):
    item = client.get("/api/v1/tools/tool-motion-design").json()
    assert item["family"] == "creation"
    assert item["status"] == "planned"
    assert item["channel"] == "connector"


def test_connecteurs_reseaux_sociaux_declares(client):
    body = client.get("/api/v1/tools").json()
    by_id = {item["id"]: item for item in body["items"]}
    for tool_id in ("tool-telegram-bot", "tool-facebook", "tool-instagram", "tool-tiktok"):
        assert tool_id in by_id
        assert by_id[tool_id]["channel"] == "connector"
        # Ces quatre mains disposent d'un gestionnaire : l'état affiché doit
        # dire la vérité (« ready »), plus « planned ».
        assert by_id[tool_id]["status"] == "ready"
        assert by_id[tool_id]["executable"] is True


def test_outil_declare_honnetement(client):
    item = client.get("/api/v1/tools/tool-web-search").json()
    assert item["status"] == "ready"
    assert item["executable"] is True
    assert item["risk"] == "low"
    assert item["channel"] == "native"


def test_main_non_branchee_reste_planned(client):
    """Une main sans gestionnaire reste « planned » : aucun faux état."""
    item = client.get("/api/v1/tools/tool-motion-design").json()
    assert item["executable"] is False
    assert item["status"] == "planned"


def test_etat_desactive_non_reactive_automatiquement(client):
    """Un outil désactivé le reste : la synchronisation ne réactive rien."""
    response = client.post("/api/v1/tools/tool-plan/status", params={"status": "disabled"})
    assert response.status_code == 200, response.text
    try:
        item = client.get("/api/v1/tools/tool-plan").json()
        assert item["status"] == "disabled"
    finally:
        client.post("/api/v1/tools/tool-plan/status", params={"status": "ready"})


def test_attribution_outil_a_un_agent(client):
    agent = client.get(
        "/api/v1/agents",
        params={"orchestrator_id": FAS_SEED["id"], "role": "orchestrator"},
    ).json()["items"][0]

    attached = client.post(f"/api/v1/agents/{agent['id']}/tools/tool-plan")
    assert attached.status_code == 200, attached.text
    tools = client.get(f"/api/v1/agents/{agent['id']}/tools").json()["items"]
    assert any(tool["id"] == "tool-plan" for tool in tools)

    client.delete(f"/api/v1/agents/{agent['id']}/tools/tool-plan")
    tools_after = client.get(f"/api/v1/agents/{agent['id']}/tools").json()["items"]
    assert all(tool["id"] != "tool-plan" for tool in tools_after)
