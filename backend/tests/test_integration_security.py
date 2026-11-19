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
