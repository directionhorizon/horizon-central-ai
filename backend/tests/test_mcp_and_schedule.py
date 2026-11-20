"""Tests du pont MCP et de la planification temporelle.

Objectif : brancher un outil via un serveur MCP réel (stdio) et exécuter une
tâche planifiée arrivée à échéance.
"""
from __future__ import annotations

import sys
from pathlib import Path

SERVER = Path(__file__).parent / "fixtures" / "mcp_echo_server.py"


def test_mcp_appelle_un_outil_dun_serveur(client):
    created = client.post(
        "/api/v1/mcp/servers",
        json={"name": "echo", "command": sys.executable, "args": [str(SERVER)]},
    )
    assert created.status_code == 201, created.text
    server_id = created.json()["id"]

    response = client.post(
        "/api/v1/tools/tool-mcp/run",
        json={"params": {"server_id": server_id, "tool": "echo", "arguments": {"text": "bonjour"}}},
    )
    assert response.status_code == 200, response.text
    import json

    assert "echo:bonjour" in json.dumps(response.json()["result"])


def test_mcp_serveur_inconnu_refuse(client):
    response = client.post(
        "/api/v1/tools/tool-mcp/run",
        json={"params": {"server_id": "inexistant", "tool": "echo"}},
    )
    assert response.status_code == 400
    assert "introuvable" in response.json()["detail"]


def test_planification_executee_si_echeance_passee(client):
    response = client.post(
        "/api/v1/tools/tool-schedule/run",
        json={
            "params": {
                "run_at": "2000-01-01T00:00:00+00:00",
                "tool_id": "tool-code-python",
                "params": {"code": "print('planifie')"},
            }
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["executed"] is True
    assert "planifie" in response.json()["result"]["result"]["stdout"]


def test_planification_future_enregistree(client):
    response = client.post(
        "/api/v1/tools/tool-schedule/run",
        json={
            "params": {
                "run_at": "2999-01-01T00:00:00+00:00",
                "tool_id": "tool-code-python",
                "params": {"code": "print('plus tard')"},
            }
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["scheduled"] is True
