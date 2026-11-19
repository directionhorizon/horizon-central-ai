"""Schéma de données versionné et migrations.

Chaque migration est appliquée une seule fois, dans l'ordre, et tracée dans
`schema_migrations`. Aucune donnée existante n'est supprimée : les évolutions
ajoutent des tables ou des colonnes nullables.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

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
    (
        6,
        "orchestrator_runs",
        (
            """
            CREATE TABLE IF NOT EXISTS orchestrator_runs (
                id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
                step_id TEXT REFERENCES mission_steps(id) ON DELETE SET NULL,
                orchestrator_id TEXT REFERENCES orchestrators(id) ON DELETE SET NULL,
                run_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                idempotency_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'started',
                phase TEXT NOT NULL DEFAULT 'dispatching',
                replayed_count INTEGER NOT NULL DEFAULT 0,
                requested_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                output TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                usage_json TEXT NOT NULL DEFAULT '{}',
                runtime_json TEXT NOT NULL DEFAULT '{}',
                raw_status_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(idempotency_key)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_runs_mission ON orchestrator_runs(mission_id)",
            "CREATE INDEX IF NOT EXISTS idx_runs_run_id ON orchestrator_runs(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_runs_status ON orchestrator_runs(status)",
        ),
    ),
    (
        7,
        "authorship_signatures",
        (
            """
            CREATE TABLE IF NOT EXISTS authorship (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL DEFAULT '',
                agent_auteur TEXT NOT NULL DEFAULT '',
                systeme TEXT NOT NULL DEFAULT '',
                projet TEXT NOT NULL DEFAULT '',
                provenance TEXT NOT NULL DEFAULT '',
                version TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_authorship_entity ON authorship(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_authorship_created ON authorship(created_at)",
        ),
    ),
    (
        8,
        "skills_library",
        (
            """
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                description TEXT NOT NULL DEFAULT '',
                level TEXT NOT NULL DEFAULT 'standard',
                tags TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','disabled')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)",
            "CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)",
            """
            CREATE TABLE IF NOT EXISTS orchestrator_skills (
                orchestrator_id TEXT NOT NULL REFERENCES orchestrators(id) ON DELETE CASCADE,
                skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY (orchestrator_id, skill_id)
            )
            """,
        ),
    ),
    (
        9,
        "skills_provenance",
        (
            "ALTER TABLE skills ADD COLUMN origin TEXT NOT NULL DEFAULT 'integrated'",
            "ALTER TABLE skills ADD COLUMN source_url TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE skills ADD COLUMN author TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE skills ADD COLUMN license TEXT NOT NULL DEFAULT ''",
        ),
    ),
    (
        10,
        "skills_subcategory",
        (
            "ALTER TABLE skills ADD COLUMN subcategory TEXT NOT NULL DEFAULT ''",
        ),
    ),
]

# Orchestrateur pilote P0 : adresse et NOM de variable uniquement, aucune valeur secrète.
HERMES_SEED = {
    "id": "orchestrator-hermes",
    "name": "Hermes",
    "kind": "hermes",
    "description": "Orchestrateur d'exécution pilote : API server Hermes sur le poste local.",
    "endpoint": "http://127.0.0.1:8642",
    "version": "0.22.4",
    "config_json": '{"api_key_env": "HERMES_API_SERVER_KEY", "profile": "default"}',
}

#: Système d'orchestration de repli quand une mission n'en désigne aucun.
#: Hermes est le premier branchement de l'UOIM, pas une dépendance obligatoire :
#: une mission peut désigner un autre système via son champ `orchestrator_id`.
DEFAULT_ORCHESTRATOR_ID = HERMES_SEED["id"]

#: Répertoire des fichiers sources du catalogue de skills, classés par catégorie.
#: Chaque fichier JSON décrit une série de compétences (métadonnées uniquement,
#: jamais de code exécutable). C'est la source de vérité, versionnée dans le dépôt.
SKILLS_CATALOG_DIR = Path(__file__).resolve().parent / "skills_catalog"


def load_catalog_entries() -> list[dict]:
    """Lit tous les fichiers du catalogue classé et renvoie leurs compétences."""
    entries: list[dict] = []
    if not SKILLS_CATALOG_DIR.is_dir():
        return entries
    for path in sorted(SKILLS_CATALOG_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, list):
            entries.extend(item for item in data if isinstance(item, dict) and item.get("name"))
    return entries

DEFAULT_PROJECT_ID = "project-default"


def _table_has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _skip_existing_column(db: sqlite3.Connection, statement: str) -> bool:
    """Vrai si l'instruction ajoute une colonne déjà présente (migration rejouable)."""
    match = re.match(r"\s*ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", statement, re.IGNORECASE)
    if not match:
        return False
    return _table_has_column(db, match.group(1), match.group(2))


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


def _ensure_hermes_orchestrator(db: sqlite3.Connection) -> None:
    """Enregistre le pilote Hermes une fois, sans jamais écraser une édition locale."""
    exists = db.execute("SELECT id FROM orchestrators WHERE id=?", (HERMES_SEED["id"],)).fetchone()
    if exists:
        return
    stamp = now()
    db.execute(
        """INSERT INTO orchestrators
           (id,name,kind,description,endpoint,version,status,health_status,config_json,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            HERMES_SEED["id"],
            HERMES_SEED["name"],
            HERMES_SEED["kind"],
            HERMES_SEED["description"],
            HERMES_SEED["endpoint"],
            HERMES_SEED["version"],
            "active",
            "unverified",
            HERMES_SEED["config_json"],
            stamp,
            stamp,
        ),
    )
    # Capacité d'exécution : CORE peut router une mission vers ce pilote.
    db.execute(
        """INSERT OR IGNORE INTO orchestrator_capabilities
           (id,orchestrator_id,capability_id,level,detail,created_at)
           VALUES(?,?,?,?,?,?)""",
        (
            "cap-hermes-execution",
            HERMES_SEED["id"],
            "execution",
            "primary",
            "Exécution réelle des missions via l'API server Hermes.",
            stamp,
        ),
    )


def _ensure_skills_catalog(db: sqlite3.Connection) -> None:
    """Installe le catalogue de skills depuis les fichiers classés du dépôt.

    Idempotent : une compétence déjà présente (par identifiant) n'est jamais
    écrasée, afin de préserver les modifications locales de l'utilisateur.
    """
    stamp = now()
    for item in load_catalog_entries():
        skill_id = str(item.get("id") or "").strip()
        if not skill_id:
            continue
        exists = db.execute("SELECT id FROM skills WHERE id=?", (skill_id,)).fetchone()
        if exists:
            continue
        db.execute(
            """INSERT INTO skills(
                   id,name,category,description,level,tags,status,
                   origin,source_url,author,license,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,'active',?,?,?,?,?,?)""",
            (
                skill_id,
                item["name"],
                item.get("category", "Général"),
                item.get("description", ""),
                item.get("level", "standard"),
                item.get("tags", ""),
                item.get("origin", "integrated"),
                item.get("source_url", ""),
                item.get("author", ""),
                item.get("license", ""),
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
                # Une colonne peut déjà exister si la base a été préparée
                # manuellement : on vérifie avant d'altérer la table.
                if _skip_existing_column(db, statement):
                    continue
                db.execute(statement)
            db.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (version, name, now()),
            )
            applied.append(f"{version}:{name}")
        _ensure_default_project(db)
        _ensure_hermes_orchestrator(db)
        _ensure_skills_catalog(db)
        db.commit()
    return applied
