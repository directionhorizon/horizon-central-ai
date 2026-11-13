"""Schéma de données versionné et migrations.

Chaque migration est appliquée une seule fois, dans l'ordre, et tracée dans
`schema_migrations`. Aucune donnée existante n'est supprimée : les évolutions
ajoutent des tables ou des colonnes nullables.
"""
from __future__ import annotations

import sqlite3

from .db import connect, now

MIGRATIONS: list[tuple[int, str, tuple[str, ...]]] = [
    (
        1,
        "projects_orchestrators_missions",
        (
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','paused','archived')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orchestrators (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'local',
                description TEXT NOT NULL DEFAULT '',
                endpoint TEXT NOT NULL DEFAULT '',
                version TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','inactive','disabled')),
                health_status TEXT NOT NULL DEFAULT 'unverified'
                    CHECK(health_status IN ('unverified','available','unavailable','degraded')),
                last_checked_at TEXT,
                config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orchestrator_capabilities (
                id TEXT PRIMARY KEY,
                orchestrator_id TEXT NOT NULL REFERENCES orchestrators(id) ON DELETE CASCADE,
                capability_id TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'standard',
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(orchestrator_id, capability_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orchestrator_projects (
                orchestrator_id TEXT NOT NULL REFERENCES orchestrators(id) ON DELETE CASCADE,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                role TEXT NOT NULL DEFAULT 'member',
                created_at TEXT NOT NULL,
                PRIMARY KEY (orchestrator_id, project_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK(status IN ('draft','planned','running','paused','completed','failed','cancelled')),
                priority TEXT NOT NULL DEFAULT 'normal'
                    CHECK(priority IN ('low','normal','high','critical')),
                orchestrator_id TEXT REFERENCES orchestrators(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mission_steps (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','running','completed','failed','skipped')),
                assigned_orchestrator_id TEXT REFERENCES orchestrators(id) ON DELETE SET NULL,
                started_at TEXT,
                completed_at TEXT,
                error TEXT NOT NULL DEFAULT '',
                UNIQUE(mission_id, position)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS mission_checkpoints (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
                step_id TEXT REFERENCES mission_steps(id) ON DELETE SET NULL,
                label TEXT NOT NULL,
                state_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS operation_log (
                id TEXT PRIMARY KEY,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT,
                result TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS llm_providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'openai_compatible',
                base_url TEXT NOT NULL,
                api_key_env TEXT NOT NULL DEFAULT '',
                default_model TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'unconfigured'
                    CHECK(status IN ('unconfigured','unverified','available','unavailable')),
                last_checked_at TEXT,
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orchestrator_model_selection (
                orchestrator_id TEXT NOT NULL REFERENCES orchestrators(id) ON DELETE CASCADE,
                provider_id TEXT NOT NULL REFERENCES llm_providers(id) ON DELETE CASCADE,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (orchestrator_id, provider_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
        ),
    ),
    (
        2,
        "sessions_project_link",
        ("ALTER TABLE sessions ADD COLUMN project_id TEXT",),
    ),
    (
        3,
        "documents_memory",
        (
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','archived')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id)",
        ),
    ),
    (
        4,
        "offline_first_sync",
        (
            """
            CREATE TABLE IF NOT EXISTS sync_outbox (
                id TEXT PRIMARY KEY,
                entity TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                operation TEXT NOT NULL
                    CHECK(operation IN ('create','update','delete')),
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','synced','failed','conflict')),
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_sync_outbox_status ON sync_outbox(status)",
            """
            CREATE TABLE IF NOT EXISTS sync_state (
                entity TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                last_synced_at TEXT,
                remote_updated_at TEXT,
                local_updated_at TEXT,
                PRIMARY KEY (entity, entity_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id TEXT PRIMARY KEY,
                entity TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                local_updated_at TEXT,
                remote_updated_at TEXT,
                reason TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """,
        ),
    ),
    (
        5,
        "integrations_registry",
        (
            """
            CREATE TABLE IF NOT EXISTS integrations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                method TEXT NOT NULL,
                endpoint TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'not_configured',
                permissions TEXT NOT NULL DEFAULT '',
                capabilities TEXT NOT NULL DEFAULT '',
                api_key_env TEXT NOT NULL DEFAULT '',
                last_checked_at TEXT,
                last_error TEXT NOT NULL DEFAULT '',
                config_json TEXT NOT NULL DEFAULT '{}',
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_integrations_category ON integrations(category)",
            "CREATE INDEX IF NOT EXISTS idx_integrations_archived ON integrations(archived)",
        ),
    ),
]

DEFAULT_PROJECT_ID = "project-default"


def _table_has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _ensure_default_project(db: sqlite3.Connection) -> None:
    exists = db.execute("SELECT id FROM projects WHERE id=?", (DEFAULT_PROJECT_ID,)).fetchone()
    if exists:
        return
    stamp = now()
    db.execute(
        "INSERT INTO projects(id,name,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (
            DEFAULT_PROJECT_ID,
            "Projet par défaut",
            "Projet créé automatiquement pour rattacher les sessions antérieures à la gestion par projet.",
            "active",
            stamp,
            stamp,
        ),
    )


def run_migrations() -> list[str]:
    """Applique les migrations manquantes et renvoie la liste de celles exécutées."""
    applied: list[str] = []
    with connect() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )"""
        )
        done = {row["version"] for row in db.execute("SELECT version FROM schema_migrations").fetchall()}
        for version, name, statements in MIGRATIONS:
            if version in done:
                continue
            for statement in statements:
                # La colonne peut déjà exister si la base a été préparée
                # manuellement : on vérifie avant d'altérer la table.
                if "ADD COLUMN project_id" in statement and _table_has_column(db, "sessions", "project_id"):
                    continue
                db.execute(statement)
            db.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (version, name, now()),
            )
            applied.append(f"{version}:{name}")
        _ensure_default_project(db)
        db.commit()
    return applied
