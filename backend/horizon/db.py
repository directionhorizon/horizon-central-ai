"""Accès à la base locale.

Une seule source de vérité pour le chemin de la base, partagée avec `app.py`.
Le stockage est volontairement abstrait derrière `connect()` pour permettre
le remplacement par un adaptateur distant (Supabase) sans réécrire les
routeurs : seule cette fonction changerait.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Même expression que dans app.py : les deux modules doivent viser le même fichier.
DB_PATH = Path(os.getenv("HORIZON_DATABASE_PATH", "./data/horizon.db")).expanduser()


def now() -> str:
    """Horodatage UTC ISO 8601, cohérent avec le reste du backend."""
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec clés étrangères et lignes nommées."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
