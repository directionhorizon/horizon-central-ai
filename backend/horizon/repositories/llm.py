"""Dépôt des fournisseurs LLM et de la sélection de modèles.

Aucune clé n'est stockée en base : seule la variable d'environnement qui la
contient est référencée par son nom.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = (
    "id,name,kind,base_url,api_key_env,default_model,status,"
    "last_checked_at,last_error,created_at,updated_at"
)


def list_providers(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute(f"SELECT {FIELDS} FROM llm_providers ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_provider(db: sqlite3.Connection, provider_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {FIELDS} FROM llm_providers WHERE id=?", (provider_id,)).fetchone()
    return dict(row) if row else None


def create_provider(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    pid, stamp = str(uuid.uuid4()), now()
    db.execute(
        """INSERT INTO llm_providers(
            id,name,kind,base_url,api_key_env,default_model,status,
            last_checked_at,last_error,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            data["name"],
            data.get("kind", "openai_compatible"),
            data["base_url"],
            data.get("api_key_env", ""),
            data.get("default_model", ""),
            "unconfigured" if not data.get("default_model") else "unverified",
            None,
            "",
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_provider(db, pid) or {}


def update_provider(db: sqlite3.Connection, provider_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    if get_provider(db, provider_id) is None:
        return None
    allowed: dict[str, Any] = {}
    for key in ("name", "kind", "base_url", "api_key_env", "default_model"):
        if changes.get(key) is not None:
            allowed[key] = changes[key]
    if allowed:
        # Une modification de configuration invalide l'état de vérification.
        allowed["status"] = "unverified"
        allowed["last_error"] = ""
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(
            f"UPDATE llm_providers SET {assignments}, updated_at=? WHERE id=?",
            (*allowed.values(), now(), provider_id),
        )
        db.commit()
    return get_provider(db, provider_id)


def set_health(
    db: sqlite3.Connection, provider_id: str, status: str, detail: str
) -> dict[str, Any] | None:
    db.execute(
        "UPDATE llm_providers SET status=?, last_checked_at=?, last_error=?, updated_at=? WHERE id=?",
        (status, now(), detail[:500], now(), provider_id),
    )
    db.commit()
    return get_provider(db, provider_id)


def delete_provider(db: sqlite3.Connection, provider_id: str) -> bool:
    """Suppression réelle d'une configuration fournisseur (aucune donnée métier)."""
    cursor = db.execute("DELETE FROM llm_providers WHERE id=?", (provider_id,))
    db.commit()
    return cursor.rowcount > 0


def get_selection(db: sqlite3.Connection) -> dict[str, Any]:
    row = db.execute("SELECT value FROM settings WHERE key='model_selection'").fetchone()
    if not row:
        return {"mode": "auto", "provider_id": None, "model": None}
    import json

    try:
        value = json.loads(row["value"])
        if isinstance(value, dict):
            return {
                "mode": value.get("mode", "auto"),
                "provider_id": value.get("provider_id"),
                "model": value.get("model"),
            }
    except ValueError:
        pass
    return {"mode": "auto", "provider_id": None, "model": None}


def set_selection(db: sqlite3.Connection, selection: dict[str, Any]) -> dict[str, Any]:
    import json

    payload = {
        "mode": selection.get("mode", "auto"),
        "provider_id": selection.get("provider_id"),
        "model": selection.get("model"),
    }
    db.execute(
        """INSERT INTO settings(key,value,updated_at) VALUES('model_selection',?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
        (json.dumps(payload, ensure_ascii=False), now()),
    )
    db.commit()
    return payload


def resolve_for_use(
    db: sqlite3.Connection, orchestrator_id: str | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """Détermine le fournisseur et le modèle réellement utilisables.

    Ordre : sélection de l'orchestrateur, puis sélection globale, puis premier
    fournisseur vérifié disponible. Renvoie (provider, model) ou (None, None).
    """
    if orchestrator_id:
        row = db.execute(
            """SELECT lp.*, oms.model AS selected_model
               FROM orchestrator_model_selection oms
               JOIN llm_providers lp ON lp.id = oms.provider_id
               WHERE oms.orchestrator_id=? AND lp.status='available'
               ORDER BY oms.updated_at DESC LIMIT 1""",
            (orchestrator_id,),
        ).fetchone()
        if row:
            item = dict(row)
            return item, item.get("selected_model") or item.get("default_model")

    selection = get_selection(db)
    if selection.get("provider_id"):
        row = db.execute(
            f"SELECT {FIELDS} FROM llm_providers WHERE id=? AND status='available'",
            (selection["provider_id"],),
        ).fetchone()
        if row:
            return dict(row), selection.get("model") or row["default_model"]

    row = db.execute(
        f"SELECT {FIELDS} FROM llm_providers WHERE status='available' AND default_model<>'' "
        "ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    if row:
        return dict(row), row["default_model"]
    return None, None
