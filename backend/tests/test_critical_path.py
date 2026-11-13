"""Tests du parcours critique de HORIZON CORE.

Objectif : un filet minimal mais réel sur ce qui casse l'application en
production — santé, en-têtes de sécurité, garde-fou réseau, lecture/écriture
d'un projet, et service de l'interface compilée.
"""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
DIST_INDEX = BACKEND_DIR.parent / "dist" / "index.html"


def test_health_repond(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "horizon-core"


def test_entetes_de_securite_presents(client):
    headers = client.get("/api/v1/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["Cross-Origin-Opener-Policy"] == "same-origin"


def test_hsts_seulement_en_https(client):
    assert "Strict-Transport-Security" not in client.get("/api/v1/health").headers
    distant = client.get("/api/v1/health", headers={"x-forwarded-proto": "https"})
    assert "max-age=31536000" in distant.headers["Strict-Transport-Security"]


def test_capabilities(client):
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "1.1"
    assert any(item["id"] == "core.projects" for item in body["capabilities"])


def test_parcours_projet_creation_et_lecture(client):
    created = client.post(
        "/api/v1/projects",
        json={"name": "Projet de test critique", "description": "Créé par pytest"},
    )
    assert created.status_code == 201, created.text
    project = created.json()

    lu = client.get(f"/api/v1/projects/{project['id']}")
    assert lu.status_code == 200
    assert lu.json()["name"] == "Projet de test critique"

    liste = client.get("/api/v1/projects")
    assert liste.status_code == 200
    assert any(item["id"] == project["id"] for item in liste.json()["items"])


def test_route_api_inconnue_renvoie_404(client):
    response = client.get("/api/v1/route-qui-nexiste-pas")
    assert response.status_code == 404


def test_acces_distant_refuse_sans_authentification(client):
    response = client.get("/api/v1/projects", headers={"host": "horizon.example.com"})
    assert response.status_code == 503
    assert response.json()["code"] == "auth_required_for_remote_access"


def test_sante_accessible_meme_en_distant(client):
    response = client.get("/api/v1/health", headers={"host": "horizon.example.com"})
    assert response.status_code == 200


def test_acces_distant_autorise_avec_jeton(client, monkeypatch):
    monkeypatch.setenv("HORIZON_ADMIN_TOKEN", "jeton-de-test")
    entetes = {"host": "horizon.example.com", "Authorization": "Bearer jeton-de-test"}
    response = client.get("/api/v1/projects", headers=entetes)
    assert response.status_code == 200


def test_ecriture_exige_le_jeton_quand_auth_active(client, monkeypatch):
    monkeypatch.setenv("HORIZON_ADMIN_TOKEN", "jeton-de-test")
    refus = client.post("/api/v1/projects", json={"name": "Sans jeton"})
    assert refus.status_code == 401

    accepte = client.post(
        "/api/v1/projects",
        json={"name": "Avec jeton"},
        headers={"X-Horizon-Token": "jeton-de-test"},
    )
    assert accepte.status_code == 201


def test_informations_bureau(client):
    body = client.get("/api/v1/system/desktop").json()
    assert body["mode"] == "desktop_offline_first"
    assert isinstance(body["ui_bundled"], bool)


@pytest.mark.skipif(not DIST_INDEX.exists(), reason="interface compilée absente (dist)")
def test_interface_compilee_servie_sur_route_spa(client):
    response = client.get("/cockpit")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
