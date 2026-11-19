"""Dépôt de la bibliothèque de skills (compétences) et de leurs affectations.

Un skill est une compétence réutilisable qu'on peut associer à un système
d'orchestration (ou, plus tard, à un agent). La bibliothèque est un catalogue
générique : rien n'y est codé en dur et tout est modifiable par l'utilisateur.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = (
    "id,name,category,subcategory,description,level,tags,status,"
    "origin,source_url,author,license,usage,outputs,example,created_at,updated_at"
)
PREFIXED = ", ".join(f"s.{name}" for name in FIELDS.split(","))

INSERT_COLUMNS = (
    "id,name,category,subcategory,description,level,tags,status,"
    "origin,source_url,author,license,usage,outputs,example,created_at,updated_at"
)


def _insert(db: sqlite3.Connection, data: dict[str, Any], stamp: str) -> None:
    db.execute(
        f"INSERT INTO skills({INSERT_COLUMNS}) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            data["id"],
            str(data["name"]).strip(),
            (str(data.get("category") or "general").strip() or "general"),
            str(data.get("subcategory") or ""),
            str(data.get("description") or ""),
            str(data.get("level") or "standard"),
            str(data.get("tags") or ""),
            str(data.get("status") or "active"),
            str(data.get("origin") or "manual"),
            str(data.get("source_url") or ""),
            str(data.get("author") or ""),
            str(data.get("license") or ""),
            str(data.get("usage") or ""),
            str(data.get("outputs") or ""),
            str(data.get("example") or ""),
            stamp,
            stamp,
        ),
    )


def list_skills(
    db: sqlite3.Connection,
    q: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    query = f"SELECT {FIELDS} FROM skills"
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(name LIKE ? OR description LIKE ? OR tags LIKE ? OR category LIKE ?)")
        params.extend([like, like, like, like])
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY category, name"
    return [dict(row) for row in db.execute(query, params).fetchall()]


def get_skill(db: sqlite3.Connection, skill_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {FIELDS} FROM skills WHERE id=?", (skill_id,)).fetchone()
    return dict(row) if row else None


def create_skill(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    sid = str(uuid.uuid4())
    payload = dict(data)
    payload["id"] = sid
    _insert(db, payload, now())
    db.commit()
    return get_skill(db, sid) or {}


def import_skills(
    db: sqlite3.Connection,
    items: list[dict[str, Any]],
    *,
    origin: str = "github",
    source_ref: str = "",
) -> dict[str, int]:
    """Insère des compétences importées, sans jamais écraser l'existant.

    Sûreté : seules les métadonnées déclaratives sont retenues (nom, catégorie,
    description, niveau, mots-clés, provenance). Aucun code n'est exécuté.
    """
    stamp = now()
    created = 0
    skipped = 0
    for item in items:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        sid = str(item.get("id") or "").strip()
        if not sid:
            continue
        if db.execute("SELECT id FROM skills WHERE id=?", (sid,)).fetchone():
            skipped += 1
            continue
        payload = dict(item)
        payload["id"] = sid
        payload.setdefault("origin", origin)
        payload["source_url"] = str(item.get("source_url") or source_ref)
        _insert(db, payload, stamp)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


def update_skill(
    db: sqlite3.Connection, skill_id: str, changes: dict[str, Any]
) -> dict[str, Any] | None:
    if get_skill(db, skill_id) is None:
        return None
    allowed: dict[str, Any] = {}
    for key in ("name", "category", "subcategory", "description", "level", "tags", "status",
                "origin", "source_url", "author", "license", "usage", "outputs", "example"):
        if changes.get(key) is not None:
            allowed[key] = changes[key]
    if allowed:
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(
            f"UPDATE skills SET {assignments}, updated_at=? WHERE id=?",
            (*allowed.values(), now(), skill_id),
        )
        db.commit()
    return get_skill(db, skill_id)


def disable_skill(db: sqlite3.Connection, skill_id: str) -> dict[str, Any] | None:
    """Désactivation logique : la fiche est conservée pour l'historique."""
    return update_skill(db, skill_id, {"status": "disabled"})


def categories(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        "SELECT DISTINCT category FROM skills WHERE status='active' ORDER BY category"
    ).fetchall()
    return [row["category"] for row in rows]


def attach_skill(db: sqlite3.Connection, orchestrator_id: str, skill_id: str) -> bool:
    cursor = db.execute(
        "INSERT OR IGNORE INTO orchestrator_skills(orchestrator_id,skill_id,created_at) VALUES(?,?,?)",
        (orchestrator_id, skill_id, now()),
    )
    db.commit()
    return cursor.rowcount > 0


def detach_skill(db: sqlite3.Connection, orchestrator_id: str, skill_id: str) -> bool:
    cursor = db.execute(
        "DELETE FROM orchestrator_skills WHERE orchestrator_id=? AND skill_id=?",
        (orchestrator_id, skill_id),
    )
    db.commit()
    return cursor.rowcount > 0


def list_for_orchestrator(db: sqlite3.Connection, orchestrator_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        f"""SELECT {PREFIXED} FROM skills s
            JOIN orchestrator_skills os ON os.skill_id = s.id
            WHERE os.orchestrator_id = ?
            ORDER BY s.category, s.name""",
        (orchestrator_id,),
    ).fetchall()
    return [dict(row) for row in rows]
