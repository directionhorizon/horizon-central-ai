"""Tests des paiements : garde-fou de validation humaine et liste locale."""
from __future__ import annotations

import pytest


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


def test_paiement_sans_reference_genere_un_detail_lisible(client, monkeypatch):
    """Sans référence saisie, la ligne reste lisible (fournisseur, montant, id)."""
    from horizon.payment_providers import stripe_provider

    monkeypatch.setenv("HORIZON_STRIPE_SECRET_KEY", "sk_test_fake")
    _FakeAsyncClient.response = {
        "id": "pi_test_sans_reference",
        "amount": 2500,
        "currency": "eur",
        "status": "requires_payment_method",
    }
    monkeypatch.setattr(stripe_provider.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/payments",
        json={"amount": 2500, "currency": "eur", "confirm": True, "provider": "stripe"},
    )
    assert response.status_code == 200, response.text
    item = client.get("/api/v1/payments/pi_test_sans_reference").json()
    assert item["detail"], "le détail ne doit jamais être vide"
    assert "Stripe" in item["detail"]
    assert "25.00 EUR" in item["detail"]
    assert "pi_test_sans_reference" in item["detail"]


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


def _fake_moneyfusion_create(monkeypatch, payload):
    from horizon.payment_providers import moneyfusion_provider

    monkeypatch.setenv("HORIZON_MONEYFUSION_API_URL", "https://app.moneyfusion.net/fake")
    monkeypatch.setattr(moneyfusion_provider.httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.response = payload


class _FakeSyncResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def test_paiement_moneyfusion_cree_lien_et_journalise(client, monkeypatch):
    """MoneyFusion rend une URL de paiement ; la référence locale est conservée."""
    _fake_moneyfusion_create(
        monkeypatch,
        {
            "statut": True,
            "token": "mf_token_1",
            "message": "ok",
            "url": "https://pay.moneyfusion.net/mf_token_1",
        },
    )
    response = client.post(
        "/api/v1/payments",
        json={
            "amount": 5000,
            "currency": "xaf",
            "confirm": True,
            "provider": "moneyfusion",
            "mode": "checkout",
            "detail": "Commande #42",
            "customer": "062000000",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "moneyfusion"
    assert body["mode"] == "checkout"
    assert body["checkout_url"].startswith("https://pay.moneyfusion.net/")
    item = client.get("/api/v1/payments/mf_token_1").json()
    assert item["detail"] == "Commande #42"
    assert item["mode"] == "checkout"


def test_paiement_moneyfusion_mode_intent_refuse(client, monkeypatch):
    """MoneyFusion n'expose qu'une page hébergée : le mode intent est refusé."""
    _fake_moneyfusion_create(monkeypatch, {"statut": True})
    response = client.post(
        "/api/v1/payments",
        json={
            "amount": 5000,
            "currency": "xaf",
            "confirm": True,
            "provider": "moneyfusion",
            "mode": "intent",
        },
    )
    assert response.status_code == 400
    assert "checkout" in response.json()["detail"].lower()


def test_webhook_moneyfusion_verifie_a_la_source(client, monkeypatch):
    """Le webhook non signé n'est cru qu'après vérification auprès de l'API."""
    from horizon.payment_providers import moneyfusion_provider

    _fake_moneyfusion_create(
        monkeypatch,
        {
            "statut": True,
            "token": "mf_token_2",
            "url": "https://pay.moneyfusion.net/mf_token_2",
        },
    )
    client.post(
        "/api/v1/payments",
        json={
            "amount": 5000,
            "currency": "xaf",
            "confirm": True,
            "provider": "moneyfusion",
            "mode": "checkout",
        },
    )
    monkeypatch.setattr(
        moneyfusion_provider.httpx,
        "get",
        lambda url, **kwargs: _FakeSyncResponse({"statut": "paid", "Montant": 5000}),
    )
    payload = b'{"tokenPay": "mf_token_2", "statut": "paid"}'
    first = client.post(
        "/api/v1/payments/webhook/moneyfusion",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["duplicate"] is False
    assert first.json()["status"] == "succeeded"
    assert client.get("/api/v1/payments/mf_token_2").json()["status"] == "succeeded"
    second = client.post(
        "/api/v1/payments/webhook/moneyfusion",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    events = client.get("/api/v1/payments/events").json()["items"]
    assert [item["id"] for item in events].count("mf_token_2:succeeded") == 1


def test_fournisseurs_paiement_inscrits_au_registre(client):
    """Chaque adaptateur de paiement a une fiche stable dans le registre."""
    from horizon import payment_providers
    from horizon.db import connect
    from horizon.repositories import integrations

    with connect() as db:
        fiches = integrations.list_integrations(db, category="payment")
        identifiants = {fiche["id"] for fiche in fiches}
        assert "payment:stripe" in identifiants
        assert "payment:moneyfusion" in identifiants
        assert "payment:paypal" in identifiants
        assert "payment:mollie" in identifiants

        moneyfusion = next(f for f in fiches if f["id"] == "payment:moneyfusion")
        assert "checkout" in moneyfusion["capabilities"]
        assert moneyfusion["api_key_env"] == "HORIZON_MONEYFUSION_API_URL"
        assert moneyfusion["category"] == "payment"

        # Idempotence : un second passage ne crée aucun doublon.
        before = len(fiches)
        payment_providers.sync_registry(db)
        after = len(integrations.list_integrations(db, category="payment"))
        assert after == before

        # Aucun secret n'est stocké dans la fiche.
        for fiche in integrations.list_integrations(db, category="payment"):
            assert "sk_" not in str(fiche)
            assert "whsec_" not in str(fiche)


# --- Adaptateur SasPay ---------------------------------------------------------


def test_registre_contient_saspay():
    from horizon import payment_providers

    kinds = {item["kind"]: item for item in payment_providers.describe_providers()}
    assert "saspay" in kinds
    assert "checkout" in kinds["saspay"]["capabilities"]
    assert kinds["saspay"]["env_vars"] == ["HORIZON_SASPAY_API_KEY"]


def test_saspay_refuse_un_mode_non_supporte(monkeypatch):
    import asyncio

    from horizon.payment_providers import saspay_provider

    monkeypatch.setenv("HORIZON_SASPAY_API_KEY", "sk_test_fake")
    provider = saspay_provider.SasPayProvider()
    request = saspay_provider.PaymentRequest(amount=5000, currency="xaf")
    with pytest.raises(saspay_provider.ProviderError):
        asyncio.run(provider.create(request, {}, mode="intent"))


def test_saspay_cree_une_session_de_checkout(client, monkeypatch):
    """Une session hebergée est créée et son URL est conservée."""
    from horizon.payment_providers import saspay_provider

    monkeypatch.setenv("HORIZON_SASPAY_API_KEY", "sk_test_fake")
    _FakeAsyncClient.response = {
        "success": True,
        "data": {
            "id": "c9a17e2c-4b1a-4f0e-9c3d-2a1b3c4d5e6f",
            "status": "PENDING",
            "checkout_url": "https://pay.saspay.me/kZ2v9rT4bQxL8mNpYw",
        },
        "code": 200,
    }
    monkeypatch.setattr(saspay_provider.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/payments",
        json={
            "amount": 5000,
            "currency": "xaf",
            "confirm": True,
            "provider": "saspay",
            "mode": "checkout",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "saspay"
    assert body["mode"] == "checkout"
    assert body["checkout_url"] == "https://pay.saspay.me/kZ2v9rT4bQxL8mNpYw"
    item = client.get(f"/api/v1/payments/{body['id']}").json()
    assert item["checkout_url"] == "https://pay.saspay.me/kZ2v9rT4bQxL8mNpYw"
    assert item["detail"]  # jamais vide, meme sans reference saisie


def _signature(body: bytes, secret: str, timestamp: str) -> str:
    import hashlib
    import hmac

    return hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()


def _evenement_saspay(type_: str, identifiant: str) -> bytes:
    import json

    return json.dumps(
        {
            "event": type_,
            "data": {
                "id": identifiant,
                "transaction_id": identifiant,
                "reference": "TXN-2026-000456",
                "amount": "25000.00",
                "currency": "XAF",
            },
        }
    ).encode("utf-8")


def test_saspay_webhook_signature_valide(monkeypatch):
    import time

    from horizon.payment_providers import saspay_provider

    monkeypatch.setenv("HORIZON_SASPAY_WEBHOOK_SECRET", "secret-test")
    body = _evenement_saspay("transaction.success", "txn_1")
    stamp = str(int(time.time()))
    headers = {
        "X-Webhook-Signature": _signature(body, "secret-test", stamp),
        "X-Webhook-Timestamp": stamp,
        "X-Webhook-Event": "transaction.success",
    }
    provider = saspay_provider.SasPayProvider()
    event = provider.verify_webhook(body, headers)
    assert event["type"] == "transaction.success"
    assert event["id"] == "transaction.success:txn_1"
    assert provider.webhook_event(event) == ("txn_1", "succeeded")


def test_saspay_webhook_signature_invalide(monkeypatch):
    import time

    from horizon.payment_providers import saspay_provider

    monkeypatch.setenv("HORIZON_SASPAY_WEBHOOK_SECRET", "secret-test")
    body = _evenement_saspay("transaction.success", "txn_2")
    headers = {
        "X-Webhook-Signature": "0" * 64,
        "X-Webhook-Timestamp": str(int(time.time())),
    }
    with pytest.raises(saspay_provider.ProviderError):
        saspay_provider.SasPayProvider().verify_webhook(body, headers)


def test_saspay_webhook_horodatage_expire(monkeypatch):
    from horizon.payment_providers import saspay_provider

    monkeypatch.setenv("HORIZON_SASPAY_WEBHOOK_SECRET", "secret-test")
    body = _evenement_saspay("transaction.success", "txn_3")
    stamp = "1000000000"  # 2001 : hors tolerance
    headers = {
        "X-Webhook-Signature": _signature(body, "secret-test", stamp),
        "X-Webhook-Timestamp": stamp,
    }
    with pytest.raises(saspay_provider.ProviderError):
        saspay_provider.SasPayProvider().verify_webhook(body, headers)


def test_saspay_webhook_route_et_idempotence(client, monkeypatch):
    """La route verifie la signature, enregistre l'evenement et ne le rejoue pas."""
    import time

    monkeypatch.setenv("HORIZON_SASPAY_WEBHOOK_SECRET", "secret-test")
    body = _evenement_saspay("transaction.failed", "txn_route")
    stamp = str(int(time.time()))
    headers = {
        "X-Webhook-Signature": _signature(body, "secret-test", stamp),
        "X-Webhook-Timestamp": stamp,
    }
    first = client.post("/api/v1/payments/webhook/saspay", content=body, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["duplicate"] is False
    assert first.json()["status"] == "failed"
    second = client.post("/api/v1/payments/webhook/saspay", content=body, headers=headers)
    assert second.json()["duplicate"] is True


def test_saspay_refuse_une_signature_absente(client, monkeypatch):
    monkeypatch.setenv("HORIZON_SASPAY_WEBHOOK_SECRET", "secret-test")
    body = _evenement_saspay("transaction.success", "txn_4")
    response = client.post("/api/v1/payments/webhook/saspay", content=body)
    assert response.status_code == 400


def test_fiche_saspay_au_registre(client):
    from horizon import payment_providers
    from horizon.db import connect
    from horizon.repositories import integrations

    with connect() as db:
        payment_providers.sync_registry(db)
        fiches = {
            f["id"]: f for f in integrations.list_integrations(db, category="payment")
        }
    assert "payment:saspay" in fiches
    fiche = fiches["payment:saspay"]
    assert fiche["api_key_env"] == "HORIZON_SASPAY_API_KEY"
    assert "checkout" in fiche["capabilities"]
    assert "sk_" not in str(fiche)

