"""Tests du moteur de synchronisation : filtrage des colonnes distantes."""
from __future__ import annotations

from horizon.sync_engine import sanitize_payload


def test_sanitize_retire_les_champs_imbriques():
    payload = {
        "id": "m1",
        "title": "Mission",
        "status": "draft",
        "steps": [{"id": "s1"}],
        "checkpoints": [{"id": "c1"}],
        "inconnu": 42,
    }
    cleaned = sanitize_payload("missions", payload)
    assert cleaned == {"id": "m1", "title": "Mission", "status": "draft"}


def test_sanitize_conserve_les_colonnes_connues():
    payload = {"id": "p1", "name": "Projet", "description": "", "status": "active"}
    assert sanitize_payload("projects", payload) == payload
