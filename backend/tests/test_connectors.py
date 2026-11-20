"""Tests des connecteurs externes (recherche, e-mail, Telegram, image, Stripe).

Principe : sans identifiants, la main refuse honnêtement ; avec des identifiants
simulés, elle appelle le bon service (transport réseau remplacé par un faux).
Aucun appel réseau réel n'est effectué.
"""
from __future__ import annotations

import pytest

from horizon import tool_runtime

UNCONFIG = [
    ("tool-web-search", {"query": "test"}),
    ("tool-email-send", {"to": "a@b.c", "subject": "s", "body": "b"}),
    ("tool-telegram-bot", {"chat_id": "1", "text": "salut"}),
    ("tool-image-generate", {"prompt": "un chat"}),
    ("tool-payment", {"amount": 100}),
    ("tool-facebook", {"message": "bonjour"}),
    ("tool-instagram", {"image_url": "http://example.com/a.png"}),
    ("tool-tiktok", {}),
]

ENV_VARS = (
    "HORIZON_SEARCH_URL",
    "HORIZON_BRAVE_SEARCH_KEY",
    "HORIZON_SMTP_HOST",
    "HORIZON_SMTP_FROM",
    "HORIZON_SMTP_USER",
    "HORIZON_TELEGRAM_BOT_TOKEN",
    "HORIZON_IMAGE_BASE_URL",
    "HORIZON_STRIPE_SECRET_KEY",
    "HORIZON_META_ACCESS_TOKEN",
    "HORIZON_TIKTOK_ACCESS_TOKEN",
)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeAsyncClient:
    response = {}
    last = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        _FakeAsyncClient.last = {"method": "GET", "url": url, **kwargs}
        return _FakeResponse(_FakeAsyncClient.response)

    async def post(self, url, **kwargs):
        _FakeAsyncClient.last = {"method": "POST", "url": url, **kwargs}
        return _FakeResponse(_FakeAsyncClient.response)


@pytest.mark.parametrize("tool_id,params", UNCONFIG)
def test_connecteur_refuse_sans_configuration(client, monkeypatch, tool_id, params):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    response = client.post(f"/api/v1/tools/{tool_id}/run", json={"params": params})
    assert response.status_code == 400, response.text
    assert "configur" in response.json()["detail"]


def test_recherche_searxng(client, monkeypatch):
    monkeypatch.setenv("HORIZON_SEARCH_URL", "http://127.0.0.1:8888")
    monkeypatch.delenv("HORIZON_BRAVE_SEARCH_KEY", raising=False)
    _FakeAsyncClient.response = {
        "results": [{"title": "Titre", "url": "http://x", "content": "extrait"}]
    }
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-web-search/run", json={"params": {"query": "horizon"}}
    )
    assert response.status_code == 200, response.text
    body = response.json()["result"]
    assert body["provider"] == "searxng"
    assert body["items"][0]["title"] == "Titre"


def test_telegram_envoi(client, monkeypatch):
    monkeypatch.setenv("HORIZON_TELEGRAM_BOT_TOKEN", "123:ABC")
    _FakeAsyncClient.response = {"ok": True}
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-telegram-bot/run",
        json={"params": {"chat_id": "42", "text": "bonjour"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["sent"] is True
    assert "api.telegram.org" in _FakeAsyncClient.last["url"]


def test_image_generation(client, monkeypatch):
    monkeypatch.setenv("HORIZON_IMAGE_BASE_URL", "http://127.0.0.1:9000/v1")
    _FakeAsyncClient.response = {"data": [{"url": "http://img/1.png"}]}
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-image-generate/run", json={"params": {"prompt": "un chat"}}
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["images"] == ["http://img/1.png"]


def test_paiement_exige_validation_humaine(client, monkeypatch):
    monkeypatch.setenv("HORIZON_STRIPE_SECRET_KEY", "sk_test_x")
    response = client.post(
        "/api/v1/tools/tool-payment/run",
        json={"params": {"amount": 1000, "currency": "eur"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["status"] == "requires_human_validation"


def test_email_envoi(client, monkeypatch):
    import smtplib

    monkeypatch.setenv("HORIZON_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("HORIZON_SMTP_FROM", "bot@example.com")
    monkeypatch.setenv("HORIZON_SMTP_USER", "bot@example.com")
    monkeypatch.delenv("HORIZON_SMTP_SECURITY", raising=False)
    sent: dict = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, user, password):
            sent["login"] = user

        def send_message(self, message):
            sent["to"] = message["To"]

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    response = client.post(
        "/api/v1/tools/tool-email-send/run",
        json={"params": {"to": "x@y.z", "subject": "s", "body": "b"}},
    )
    assert response.status_code == 200, response.text
    assert sent.get("to") == "x@y.z"
    assert sent.get("tls") is True


def _create_integration(client, name, env_var):
    response = client.post(
        "/api/v1/integrations",
        json={
            "name": name,
            "category": "communication",
            "method": "bearer",
            "api_key_env": env_var,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_facebook_publication(client, monkeypatch):
    monkeypatch.setenv("HORIZON_META_ACCESS_TOKEN", "EAAG-token")
    _FakeAsyncClient.response = {"id": "123_456"}
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-facebook/run",
        json={"params": {"page_id": "P1", "message": "bonjour"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["id"] == "123_456"
    assert "graph.facebook.com" in _FakeAsyncClient.last["url"]


def test_instagram_publication(client, monkeypatch):
    monkeypatch.setenv("HORIZON_META_ACCESS_TOKEN", "t")
    monkeypatch.setenv("HORIZON_META_IG_USER_ID", "IG1")
    _FakeAsyncClient.response = {"id": "IG-1"}
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-instagram/run",
        json={"params": {"image_url": "http://example.com/i.png", "caption": "c"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["id"] == "IG-1"


def test_tiktok_creator_info(client, monkeypatch):
    monkeypatch.setenv("HORIZON_TIKTOK_ACCESS_TOKEN", "tt")
    _FakeAsyncClient.response = {"data": {"creator_username": "me"}}
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-tiktok/run", json={"params": {"action": "creator_info"}}
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["action"] == "creator_info"


def test_multi_comptes_via_registre(client, monkeypatch):
    """Plusieurs clés : une fiche par compte ; le paramètre `account` choisit la bonne."""
    _create_integration(client, "Page A", "HORIZON_META_TOKEN_A")
    _create_integration(client, "Page B", "HORIZON_META_TOKEN_B")
    monkeypatch.setenv("HORIZON_META_TOKEN_A", "TOKEN-A")
    monkeypatch.setenv("HORIZON_META_TOKEN_B", "TOKEN-B")
    _FakeAsyncClient.response = {"id": "x"}
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/tools/tool-facebook/run",
        json={"params": {"account": "Page B", "page_id": "P2", "message": "hi"}},
    )
    assert response.status_code == 200, response.text
    assert _FakeAsyncClient.last["data"]["access_token"] == "TOKEN-B"
