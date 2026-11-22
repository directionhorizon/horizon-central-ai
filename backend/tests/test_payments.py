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
