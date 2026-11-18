"""Signatures d'auteur des écritures (gouvernance des données, §4.2).

Chaque écriture métier est signée : qui agit (agent_auteur), depuis quel
système, pour quel projet, avec quelle provenance et quelle version.

Ces informations sont **stockées côté serveur** et **jamais exposées** par
l'API ni affichées dans l'interface : elles servent à l'audit et à la
traçabilité. Aucun secret n'y figure.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = "id,entity_type,entity_id,agent_auteur,systeme,projet,provenance,version,created_at"

#: Nom du système qui signe par défaut : l'application elle-même.
SYSTEM_NAME = "HORIZON CORE"


def sign(
    db: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: str | None = None,
    agent_auteur: str = "",
    systeme: str = "",
    projet: str = "",
    provenance: str = "",
    version: str = "",
) -> dict[str, Any]:
    """Enregistre une signature. Ne valide pas la transaction (l'appelant le fait)."""
    entry = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id or "",
        "agent_auteur": agent_auteur or "",
        "systeme": systeme or SYSTEM_NAME,
        "projet": projet or "",
        "provenance": provenance or "",
        "version": version or "",
        "created_at": now(),
    }
    db.execute(
        f"INSERT INTO authorship({FIELDS}) VALUES(?,?,?,?,?,?,?,?,?)",
        tuple(entry[key] for key in FIELDS.split(",")),
    )
    return entry


def list_for(db: sqlite3.Connection, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
    """Historique des signatures d'une entité (usage interne / audit)."""
    rows = db.execute(
        f"SELECT {FIELDS} FROM authorship WHERE entity_type=? AND entity_id=? ORDER BY created_at DESC",
        (entity_type, entity_id),
    ).fetchall()
    return [dict(row) for row in rows]
