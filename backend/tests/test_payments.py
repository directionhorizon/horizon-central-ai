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
        assert set(item["capabilities"]) <= {"intent", "checkout", "setup", "refund"}


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


def _stripe_signature(secret: str, payload: bytes) -> str:
    """Construit une signature Stripe valide pour un corps donné."""
    import hashlib
    import hmac
    import time

    stamp = int(time.time())
    signed = f"{stamp}.{payload.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={digest}"


def _create_stripe_payment(client, monkeypatch, payment_id: str, amount: int = 2500):
    from horizon.payment_providers import stripe_provider

    monkeypatch.setenv("HORIZON_STRIPE_SECRET_KEY", "sk_test_fake")
    _FakeAsyncClient.response = {
        "id": payment_id,
        "amount": amount,
        "currency": "eur",
        "status": "requires_payment_method",
    }
    monkeypatch.setattr(stripe_provider.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/payments",
        json={
            "amount": amount,
            "currency": "eur",
            "confirm": True,
            "provider": "stripe",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_cle_idempotence_rejoue_sans_second_paiement(client, monkeypatch):
    """Le même Idempotency-Key ne doit jamais créer un second paiement."""
    from horizon.payment_providers import stripe_provider

    monkeypatch.setenv("HORIZON_STRIPE_SECRET_KEY", "sk_test_fake")
    _FakeAsyncClient.response = {
        "id": "pi_idem",
        "amount": 1000,
        "currency": "eur",
        "status": "requires_payment_method",
    }
    monkeypatch.setattr(stripe_provider.httpx, "AsyncClient", _FakeAsyncClient)
    headers = {"Idempotency-Key": "cle-idem-1"}
    body = {"amount": 1000, "currency": "eur", "confirm": True, "provider": "stripe"}
    first = client.post("/api/v1/payments", json=body, headers=headers)
    assert first.status_code == 200, first.text
    # Le fournisseur n'est plus joignable : seul le rejeu local doit répondre.
    monkeypatch.delenv("HORIZON_STRIPE_SECRET_KEY", raising=False)
    second = client.post("/api/v1/payments", json=body, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["replayed"] is True
    assert second.json()["id"] == first.json()["id"]
    items = client.get("/api/v1/payments").json()["items"]
    assert [item["id"] for item in items].count("pi_idem") == 1


def test_webhook_stripe_signature_invalide_refuse(client, monkeypatch):
    monkeypatch.setenv("HORIZON_STRIPE_WEBHOOK_SECRET", "whsec_test")
    payload = (
        b'{"id":"evt_bad","type":"payment_intent.succeeded",'
        b'"data":{"object":{"id":"pi_x"}}}'
    )
    response = client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={
            "Stripe-Signature": "t=1,v1=deadbeef",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 400


def test_webhook_stripe_met_a_jour_le_statut_et_rejoue(client, monkeypatch):
    _create_stripe_payment(client, monkeypatch, "pi_webhook", 1200)
    monkeypatch.setenv("HORIZON_STRIPE_WEBHOOK_SECRET", "whsec_test")
    payload = (
        b'{"id":"evt_1","type":"payment_intent.succeeded",'
        b'"data":{"object":{"id":"pi_webhook"}}}'
    )
    headers = {
        "Stripe-Signature": _stripe_signature("whsec_test", payload),
        "Content-Type": "application/json",
    }
    first = client.post("/api/v1/payments/webhook/stripe", content=payload, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["duplicate"] is False
    assert first.json()["status"] == "succeeded"
    assert client.get("/api/v1/payments/pi_webhook").json()["status"] == "succeeded"
    second = client.post("/api/v1/payments/webhook/stripe", content=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    events = client.get("/api/v1/payments/events").json()["items"]
    assert [item["id"] for item in events].count("evt_1") == 1


def test_remboursement_stripe_met_a_jour_le_statut(client, monkeypatch):
    _create_stripe_payment(client, monkeypatch, "pi_refundable", 3000)
    _FakeAsyncClient.response = {
        "id": "re_test",
        "status": "succeeded",
        "amount": 3000,
        "currency": "eur",
    }
    response = client.post(
        "/api/v1/payments/pi_refundable/refund", json={"amount": 3000}
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == "re_test"
    item = client.get("/api/v1/payments/pi_refundable").json()
    assert item["status"] == "refunded"
