"""Tests du connecteur MAYELA : lecture seule, aucun secret exposé.

MAYELA n'est jamais simulée en base : le client HTTP est remplacé, on vérifie
uniquement le contrat de HORIZON (lecture, erreurs, état, registre).
"""
from __future__ import annotations

import pytest

MAYELA_VARS = (
    "HORIZON_MAYELA_SUPABASE_URL",
    "HORIZON_MAYELA_SUPABASE_ANON_KEY",
    "HORIZON_MAYELA_SUPABASE_TOKEN",
)


@pytest.fixture()
def sans_config(monkeypatch):
    for name in MAYELA_VARS:
        monkeypatch.delenv(name, raising=False)


class _Reponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


@pytest.fixture()
def config(monkeypatch):
    """Configure MAYELA avec des valeurs factices et renvoie le module."""
    from horizon import mayela_feed

    monkeypatch.setenv("HORIZON_MAYELA_SUPABASE_URL", "https://exemple.supabase.co")
    monkeypatch.setenv("HORIZON_MAYELA_SUPABASE_ANON_KEY", "anon-publique")
    monkeypatch.setenv("HORIZON_MAYELA_SUPABASE_TOKEN", "jeton-de-test")
    return mayela_feed


def test_status_non_configure(client, sans_config):
    body = client.get("/api/v1/mayela/status").json()
    assert body["configured"] is False
    assert body["status"] == "not_configured"
    assert set(body["missing"]) == set(MAYELA_VARS)


def test_lecture_sans_configuration_renvoie_502(client, sans_config):
    assert client.get("/api/v1/mayela/posts").status_code == 502


def test_status_connecte_et_compteurs(client, config, monkeypatch):
    monkeypatch.setattr(
        config.httpx, "get", lambda *a, **k: _Reponse([{"id": "1"}, {"id": "2"}])
    )
    body = client.get("/api/v1/mayela/status").json()
    assert body["status"] == "connected"
    assert (body["posts"], body["ads"], body["flux"]) == (2, 2, 2)


def test_aucun_secret_renvoye(client, config, monkeypatch):
    monkeypatch.setattr(
        config.httpx, "get", lambda *a, **k: _Reponse([{"id": "1"}])
    )
    for route in ("/api/v1/mayela/status", "/api/v1/mayela/posts"):
        body = client.get(route).text
        assert "jeton-de-test" not in body
        assert "anon-publique" not in body


def test_lecture_posts(client, config, monkeypatch):
    monkeypatch.setattr(
        config.httpx, "get", lambda *a, **k: _Reponse([{"platform": "tiktok"}])
    )
    body = client.get("/api/v1/mayela/posts?limit=1").json()
    assert body["view"] == "posts"
    assert body["count"] == 1
    assert body["items"][0]["platform"] == "tiktok"


def test_lecture_refusee_renvoie_502(client, config, monkeypatch):
    monkeypatch.setattr(
        config.httpx, "get", lambda *a, **k: _Reponse({"message": "refus"}, 401)
    )
    response = client.get("/api/v1/mayela/ads")
    assert response.status_code == 502
    assert "401" in response.json()["detail"]


def test_limite_bornee(client):
    assert client.get("/api/v1/mayela/posts?limit=99999").status_code == 422
    assert client.get("/api/v1/mayela/posts?limit=0").status_code == 422


def test_fiche_mayela_au_registre_sans_secret(client):
    items = client.get("/api/v1/integrations").json()["items"]
    card = next(item for item in items if item["id"] == "mayela-crm")
    assert card["category"] == "app"
    assert card["method"] == "bearer"
    assert card["api_key_env"] == "HORIZON_MAYELA_SUPABASE_TOKEN"
    assert "value" not in card and "endpoint" not in card
