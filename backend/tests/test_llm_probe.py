"""Tests du test de connexion d'un fournisseur LLM.

Aucun appel réseau réel : le transport HTTP est simulé. On vérifie :
- la route `/models` quand elle existe ;
- le repli `/chat/completions` quand `/models` renvoie 404 (cas Gemini) ;
- l'échec honnête quand les deux échouent.
"""
from __future__ import annotations

import asyncio

import httpx

from horizon import llm

ROW = {
    "id": "p1",
    "name": "Gemini (Google)",
    "base_url": "https://example.test/v1beta/openai",
    "default_model": "gemini-2.5-flash",
    "api_key_env": "HORIZON_TEST_LLM_KEY",
}


def _patch_transport(monkeypatch, handler):
    real_client = httpx.AsyncClient

    def factory(**kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler), timeout=5)

    monkeypatch.setattr(llm.httpx, "AsyncClient", factory)
    monkeypatch.setenv("HORIZON_TEST_LLM_KEY", "cle-de-test")


def test_models_disponible(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models")
        assert request.headers.get("Authorization") == "Bearer cle-de-test"
        return httpx.Response(200, json={"data": [{"id": "gemini-2.5-flash"}]})

    _patch_transport(monkeypatch, handler)
    result = asyncio.run(llm.test_connection(ROW))
    assert result["status"] == "available"
    assert result["models"] == ["gemini-2.5-flash"]


def test_repli_chat_quand_models_absent(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(404, json={"error": "not found"})
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})
        return httpx.Response(500)

    _patch_transport(monkeypatch, handler)
    result = asyncio.run(llm.test_connection(ROW))
    assert result["status"] == "available"
    assert result["models"] == ["gemini-2.5-flash"]


def test_echec_honnete(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "cle invalide"}})

    _patch_transport(monkeypatch, handler)
    result = asyncio.run(llm.test_connection(ROW))
    assert result["status"] == "unavailable"
    assert "401" in result["detail"]
    assert "cle-de-test" not in result["detail"]


def test_chat_reessaie_avec_prefixe_models(monkeypatch):
    """Si le fournisseur attend « models/<id> », le chat réessaie automatiquement."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        model = _json.loads(request.content).get("model")
        seen.append(model)
        if model == "gemini-2.5-flash":
            return httpx.Response(404, json={"error": {"message": "model not found"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "bonjour"}}], "usage": {}},
        )

    _patch_transport(monkeypatch, handler)
    result = asyncio.run(llm.chat(ROW, [{"role": "user", "content": "salut"}]))
    assert result["content"] == "bonjour"
    assert seen == ["gemini-2.5-flash", "models/gemini-2.5-flash"]


def test_repli_sur_variable_generique(monkeypatch):
    """La fiche peut déclarer une variable vide : la clé générique est utilisée."""
    monkeypatch.delenv("HORIZON_TEST_LLM_KEY", raising=False)
    monkeypatch.setenv("HORIZON_LLM_API_KEY", "cle-generique")
    assert llm.resolve_api_key("HORIZON_TEST_LLM_KEY") == "cle-generique"
    config = llm.build_config(ROW)
    assert config.api_key == "cle-generique"


def test_non_configure(monkeypatch):
    monkeypatch.delenv("HORIZON_TEST_LLM_KEY", raising=False)
    result = asyncio.run(llm.test_connection({**ROW, "default_model": ""}))
    assert result["status"] == "unconfigured"
