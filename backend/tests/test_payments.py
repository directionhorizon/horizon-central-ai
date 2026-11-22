"""Tests des paiements : garde-fou de validation humaine et liste locale."""
from __future__ import annotations


def test_liste_paiements_vide(client):
    response = client.get("/api/v1/payments")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_paiement_sans_confirm_refuse_et_non_enregistre(client):
    response = client.post(
        "/api/v1/payments",
        json={"amount": 1000, "currency": "eur"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "requires_human_validation"
    # Aucun paiement n'a été créé : la liste reste vide.
    assert client.get("/api/v1/payments").json()["items"] == []


def test_registre_fournisseurs_ouvert(client):
    """Le registre expose plusieurs adaptateurs, sans aucun secret."""
    body = client.get("/api/v1/payments/providers").json()
    kinds = {item["kind"] for item in body["items"]}
    assert {"stripe", "paypal", "mollie"} <= kinds
    assert body["default"] in kinds
    for item in body["items"]:
        # Seuls des NOMS de variables sont exposés, jamais leur valeur.
        assert "value" not in item
        assert all(name.isupper() for name in item["env_vars"])
        assert set(item["capabilities"]) <= {"intent", "checkout", "setup"}


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeAsyncClient:
    response = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        return _FakeResponse(_FakeAsyncClient.response)


def test_paiement_stripe_enregistre_detail_et_provider(client, monkeypatch):
    """Un paiement Stripe simulé est enregistré avec sa référence et son adaptateur."""
    from horizon.payment_providers import stripe_provider

    monkeypatch.setenv("HORIZON_STRIPE_SECRET_KEY", "sk_test_fake")
    _FakeAsyncClient.response = {
        "id": "pi_test_adapter",
        "amount": 2500,
        "currency": "eur",
        "status": "requires_payment_method",
    }
    monkeypatch.setattr(stripe_provider.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/payments",
        json={
            "amount": 2500,
            "currency": "eur",
            "confirm": True,
            "provider": "stripe",
            "detail": "Commande #42",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "pi_test_adapter"
    assert body["provider"] == "stripe"
    item = client.get("/api/v1/payments/pi_test_adapter").json()
    assert item["detail"] == "Commande #42"
    assert item["provider"] == "stripe"
    assert item["mode"] == "intent"


def test_fournisseur_inconnu_refuse(client):
    response = client.post(
        "/api/v1/payments",
        json={"amount": 100, "confirm": True, "provider": "banque-imaginaire"},
    )
    assert response.status_code == 400
    assert "inconnu" in response.json()["detail"].lower()


def test_record_payment_complete_le_detail_sans_ecraser(client):
    """La première écriture du moteur est complétée par la référence du routeur."""
    from horizon.db import connect
    from horizon.repositories import payments

    with connect() as db:
        payments.record_payment(db, "pi_completion", 500, "eur", "created")
        payments.record_payment(
            db, "pi_completion", 500, "eur", "created", "Référence ajoutée"
        )
        item = payments.get_payment(db, "pi_completion")
    assert item["detail"] == "Référence ajoutée"
    assert item["provider"] == "stripe"
