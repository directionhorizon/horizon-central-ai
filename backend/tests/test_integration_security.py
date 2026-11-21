"""Tests de sécurité — protection SSRF des tests de connexion (intégrations).

Vérifie qu'un endpoint fourni par l'appelant ne peut pas faire viser au serveur
des adresses internes (boucle locale, réseau privé, métadonnées cloud).
"""
from __future__ import annotations

from horizon.routers.integrations import _probe


def test_probe_refuse_la_boucle_locale():
    ok, _ = _probe("http://127.0.0.1:8000/")
    assert ok is False


def test_probe_refuse_les_metadonnees_cloud():
    ok, _ = _probe("http://169.254.169.254/latest/meta-data/")
    assert ok is False


def test_probe_refuse_le_reseau_prive():
    ok, _ = _probe("http://192.168.1.1/")
    assert ok is False


def test_probe_refuse_hote_tcp_interne():
    ok, _ = _probe("127.0.0.1:8000")
    assert ok is False


def test_appareils_exigent_le_jeton_administrateur(client, monkeypatch):
    """La liste des appareils contient des identifiants de session : protégée."""
    monkeypatch.setenv("HORIZON_ADMIN_TOKEN", "jeton-de-test")
    assert client.get("/api/v1/auth/devices").status_code == 401
    ok = client.get(
        "/api/v1/auth/devices", headers={"X-Horizon-Token": "jeton-de-test"}
    )
    assert ok.status_code == 200
    assert "items" in ok.json()


def test_revocation_appareil_exige_le_jeton_administrateur(client, monkeypatch):
    monkeypatch.setenv("HORIZON_ADMIN_TOKEN", "jeton-de-test")
    refused = client.post("/api/v1/auth/devices/session-inconnue/revoke")
    assert refused.status_code == 401
