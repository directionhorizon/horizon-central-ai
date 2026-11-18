"""Journal des opérations importantes.

Le journal ne contient aucun secret : ni clé, ni jeton, ni contenu de message.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now
from . import signatures

FIELDS = "id,actor,action,target_type,target_id,result,detail,created_at"


def log(
    db: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    result: str = "success",
    detail: str = "",
    systeme: str = "",
    projet: str = "",
    provenance: str = "",
    version: str = "",
) -> dict[str, Any]:
    entry = {
        "id": str(uuid.uuid4()),
        "actor": actor,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "result": result,
        "detail": detail[:1000],
        "created_at": now(),
    }
    db.execute(
        f"INSERT INTO operation_log({FIELDS}) VALUES(?,?,?,?,?,?,?,?)",
        (
            entry["id"],
            entry["actor"],
            entry["action"],
            entry["target_type"],
            entry["target_id"],
            entry["result"],
            entry["detail"],
            entry["created_at"],
        ),
    )
    # Signature d'auteur de l'écriture : stockée côté serveur, jamais exposée
    # par l'API ni affichée dans l'interface (gouvernance §4.2).
    signatures.sign(
        db,
        entity_type=target_type,
        entity_id=target_id,
        agent_auteur=actor,
        systeme=systeme,
        projet=projet,
        provenance=provenance or action,
        version=version,
    )
    db.commit()
    return entry


def list_entries(
    db: sqlite3.Connection, limit: int = 100, target_type: str | None = None
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 500))
    if target_type:
        rows = db.execute(
            f"SELECT {FIELDS} FROM operation_log WHERE target_type=? ORDER BY created_at DESC LIMIT ?",
            (target_type, safe_limit),
        ).fetchall()
    else:
        rows = db.execute(
            f"SELECT {FIELDS} FROM operation_log ORDER BY created_at DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]
