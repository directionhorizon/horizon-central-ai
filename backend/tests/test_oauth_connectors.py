"""Tests du flux OAuth des connecteurs (Meta, TikTok).

Aucun appel réseau réel : l'échange de code est simulé. On vérifie que la
connexion est enregistrée (fiche oauth2 + jeton stocké localement) et que la
main retrouve ensuite le jeton SANS aucune variable d'environnement.
"""
from __future__ import annotations

from horizon import oauth_connectors as oauth
from horizon import tool_runtime

APP_VARS = (
    "HORIZON_META_APP_ID",
    "HORIZON_META_APP_SECRET",
    "HORIZON_META_REDIRECT_URI",
    "HORIZON_TIKTOK_CLIENT_KEY",
    "HORIZON_TIKTOK_CLIENT_SECRET",
    "HORIZON_TIKTOK_REDIRECT_URI",
)


def _configure_meta(monkeypatch):
    monkeypatch.setenv("HORIZON_META_APP_ID", "APPID")
    monkeypatch.setenv("HORIZON_META_APP_SECRET", "SECRET")
    monkeypatch.setenv(
        "HORIZON_META_REDIRECT_URI",
        "http://127.0.0.1:8000/api/v1/integrations/oauth/meta/callback",
    )


class _TokenResponse:
    status_code = 200

    def json(self):
        return {"access_token": "OAUTH-TOKEN", "expires_in": 3600}


class _TokenClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        return _TokenResponse()

    async def post(self, *args, **kwargs):
        return _TokenResponse()


def test_providers_listes(client, monkeypatch):
    for name in APP_VARS:
        monkeypatch.delenv(name, raising=False)
    body = client.get("/api/v1/integrations/oauth/providers").json()
    assert set(body["items"]) == {"meta", "tiktok", "google"}
    assert body["items"]["meta"]["configured"] is False


def test_start_sans_configuration_refuse(client, monkeypatch):
    monkeypatch.delenv("HORIZON_META_APP_ID", raising=False)
    monkeypatch.delenv("HORIZON_META_REDIRECT_URI", raising=False)
    response = client.get("/api/v1/integrations/oauth/meta/start")
    assert response.status_code == 400


def test_start_renvoie_url_autorisation(client, monkeypatch):
    _configure_meta(monkeypatch)
    response = client.get(
        "/api/v1/integrations/oauth/meta/start", params={"name": "Ma Page"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "facebook.com" in body["authorize_url"]
    assert "client_id=APPID" in body["authorize_url"]
    assert body["state"]


def test_callback_enregistre_la_connexion(client, monkeypatch):
    _configure_meta(monkeypatch)
    start = client.get(
        "/api/v1/integrations/oauth/meta/start", params={"name": "Page OAuth"}
    ).json()
    monkeypatch.setattr(oauth.httpx, "AsyncClient", _TokenClient)

    callback = client.get(
        "/api/v1/integrations/oauth/meta/callback",
        params={"code": "abc", "state": start["state"]},
    )
    assert callback.status_code == 200, callback.text
    body = callback.json()
    assert body["connected"] is True
    integration_id = body["integration_id"]

    # La main retrouve le jeton via la fiche OAuth, sans variable d'environnement.
    class _PostResponse:
        status_code = 200

        def json(self):
            return {"id": "post-1"}

    class _PostClient:
        last: dict = {}

        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            _PostClient.last = {"url": url, **kwargs}
            return _PostResponse()

    monkeypatch.setenv("HORIZON_META_PAGE_ID", "P1")
    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _PostClient)
    published = client.post(
        "/api/v1/tools/tool-facebook/run",
        json={"params": {"account": integration_id, "message": "bonjour"}},
    )
    assert published.status_code == 200, published.text
    assert _PostClient.last["data"]["access_token"] == "OAUTH-TOKEN"


def _configure_google(monkeypatch):
    monkeypatch.setenv("HORIZON_GOOGLE_CLIENT_ID", "gid")
    monkeypatch.setenv("HORIZON_GOOGLE_CLIENT_SECRET", "gsecret")
    monkeypatch.setenv(
        "HORIZON_GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/api/v1/integrations/oauth/google/callback",
    )


def test_google_provider_liste(client, monkeypatch):
    _configure_google(monkeypatch)
    body = client.get("/api/v1/integrations/oauth/providers").json()
    assert body["items"]["google"]["configured"] is True


def test_email_via_gmail_oauth(client, monkeypatch):
    _configure_google(monkeypatch)
    start = client.get(
        "/api/v1/integrations/oauth/google/start", params={"name": "Mon Gmail"}
    ).json()
    assert "accounts.google.com" in start["authorize_url"]
    monkeypatch.setattr(oauth.httpx, "AsyncClient", _TokenClient)
    callback = client.get(
        "/api/v1/integrations/oauth/google/callback",
        params={"code": "c", "state": start["state"]},
    )
    assert callback.status_code == 200, callback.text
    integration_id = callback.json()["integration_id"]

    class _SendResponse:
        status_code = 200

        def json(self):
            return {"id": "msg-1"}

    class _SendClient:
        last: dict = {}

        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            _SendClient.last = {"url": url, **kwargs}
            return _SendResponse()

    monkeypatch.setattr(tool_runtime.httpx, "AsyncClient", _SendClient)
    response = client.post(
        "/api/v1/tools/tool-email-send/run",
        json={
            "params": {
                "account": integration_id,
                "to": "dest@example.com",
                "subject": "s",
                "body": "b",
            }
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["provider"] == "gmail"
    assert "gmail.googleapis.com" in _SendClient.last["url"]
    assert _SendClient.last["headers"]["Authorization"] == "Bearer OAUTH-TOKEN"


def test_callback_refuse_state_inconnu(client, monkeypatch):
    _configure_meta(monkeypatch)
    response = client.get(
        "/api/v1/integrations/oauth/meta/callback",
        params={"code": "abc", "state": "etat-invente"},
    )
    assert response.status_code == 400
