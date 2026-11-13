"""Export non destructif de la base locale HORIZON CENTRAL AI (instantané JSON).

Objectif : préparer une migration contrôlée vers Supabase **sans rien modifier**.
Ce script :

- ouvre la base SQLite en **lecture seule** (`mode=ro`) ;
- n'exécute aucune écriture, aucune suppression, aucune migration ;
- n'effectue **aucun appel réseau** et ne contacte jamais Supabase ;
- masque les colonnes susceptibles de contenir un secret (les clés API ne sont
  de toute façon jamais stockées : seule la *variable* `api_key_env` l'est).

Usage :
    python tools/export_snapshot.py [--out dossier] [--database chemin]

Sortie : un fichier `horizon-snapshot-AAAAMMJJ-HHMMSS.json` + un résumé des
volumes exportés (aucune donnée n'est affichée sur la console).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TABLES = [
    "projects",
    "orchestrators",
    "orchestrator_capabilities",
    "orchestrator_projects",
    "orchestrator_model_selection",
    "missions",
    "mission_steps",
    "mission_checkpoints",
    "documents",
    "llm_providers",
    "sessions",
    "messages",
    "settings",
    "operation_log",
    "sync_outbox",
    "sync_state",
    "sync_conflicts",
    "schema_migrations",
]

# Colonnes jugées sensibles : remplacées par une marque explicite.
SECRET_COLUMN = re.compile(r"(token|secret|password|passwd|credential)", re.IGNORECASE)
SAFE_COLUMNS = {"api_key_env"}

DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "data" / "horizon.db"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "snapshots"


def redact(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if key in SAFE_COLUMNS:
            result[key] = value
        elif SECRET_COLUMN.search(key) and value not in (None, "", False):
            result[key] = "[masqué]"
        else:
            result[key] = value
    return result


def export(database: Path, output: Path) -> tuple[Path, dict[str, int]]:
    if not database.exists():
        raise SystemExit(f"Base introuvable : {database}")

    # Lecture seule stricte : aucune écriture possible, même par erreur.
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        payload: dict[str, Any] = {
            "format": "horizon-central-ai/snapshot@1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_database": database.name,
            "read_only": True,
            "tables": {},
        }
        counts: dict[str, int] = {}
        existing = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table in TABLES:
            if table not in existing:
                counts[table] = 0
                continue
            rows = [redact(dict(row)) for row in connection.execute(f"SELECT * FROM {table}")]
            payload["tables"][table] = rows
            counts[table] = len(rows)
    finally:
        connection.close()

    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = output / f"horizon-snapshot-{stamp}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export non destructif (lecture seule).")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    target, counts = export(args.database, args.out)
    total = sum(counts.values())
    print(f"Instantané écrit : {target}")
    print(f"Lignes exportées : {total}")
    for table, count in counts.items():
        if count:
            print(f"  - {table}: {count}")
    print("Aucune écriture, aucune suppression, aucun appel réseau.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
