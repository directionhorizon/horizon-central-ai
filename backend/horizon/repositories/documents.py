"""Dépôt de la mémoire documentaire centrale.

La mémoire centrale est distincte des mémoires spécialisées : elle conserve des
documents rattachés à un projet, sans écrasement silencieux (archivage logique).
Aucun secret n'est stocké ici : uniquement du texte fourni par l'utilisateur.
"""
from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from ..db import now

FIELDS = "id,project_id,title,content,tags,source,status,created_at,updated_at"


def _match_clause(query: str) -> tuple[str, list[str]]:
    """Recherche par mots-clés sur titre, contenu, tags et source (sans IA)."""
    pattern = f"%{query.strip()}%"
    clause = " AND (title LIKE ? OR content LIKE ? OR tags LIKE ? OR source LIKE ?)"
    return clause, [pattern, pattern, pattern, pattern]


def list_documents(
    db: sqlite3.Connection,
    project_id: str | None = None,
    query: str | None = None,
    status: str = "active",
    limit: int = 200,
) -> list[dict[str, Any]]:
    sql = f"SELECT {FIELDS} FROM documents WHERE status=?"
    params: list[Any] = [status]
    if project_id:
        sql += " AND project_id=?"
        params.append(project_id)
    if query and query.strip():
        clause, extra = _match_clause(query)
        sql += clause
        params.extend(extra)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    rows = db.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def get_document(db: sqlite3.Connection, document_id: str) -> dict[str, Any] | None:
    row = db.execute(f"SELECT {FIELDS} FROM documents WHERE id=?", (document_id,)).fetchone()
    return dict(row) if row else None


def create_document(db: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    document_id, stamp = str(uuid.uuid4()), now()
    db.execute(
        "INSERT INTO documents(id,project_id,title,content,tags,source,status,created_at,updated_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (
            document_id,
            payload.get("project_id"),
            payload.get("title", ""),
            payload.get("content", ""),
            payload.get("tags", ""),
            payload.get("source", ""),
            "active",
            stamp,
            stamp,
        ),
    )
    db.commit()
    return get_document(db, document_id) or {}


def update_document(
    db: sqlite3.Connection, document_id: str, changes: dict[str, Any]
) -> dict[str, Any] | None:
    if get_document(db, document_id) is None:
        return None
    allowed = {
        key: value
        for key, value in changes.items()
        if key in {"title", "content", "tags", "source", "project_id"} and value is not None
    }
    if allowed:
        assignments = ", ".join(f"{key}=?" for key in allowed)
        db.execute(
            f"UPDATE documents SET {assignments}, updated_at=? WHERE id=?",
            (*allowed.values(), now(), document_id),
        )
        db.commit()
    return get_document(db, document_id)


def archive_document(db: sqlite3.Connection, document_id: str) -> dict[str, Any] | None:
    """Archivage logique : aucun document n'est supprimé physiquement."""
    if get_document(db, document_id) is None:
        return None
    db.execute(
        "UPDATE documents SET status='archived', updated_at=? WHERE id=?", (now(), document_id)
    )
    db.commit()
    return get_document(db, document_id)


def count_documents(db: sqlite3.Connection, project_id: str | None = None) -> int:
    if project_id:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE status='active' AND project_id=?",
            (project_id,),
        ).fetchone()
    else:
        row = db.execute("SELECT COUNT(*) AS n FROM documents WHERE status='active'").fetchone()
    return int(row["n"]) if row else 0
