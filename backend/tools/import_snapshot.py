"""Import d'un instantané JSON dans la base locale HORIZON (restauration).

Restaure les données d'un fichier `horizon-snapshot-*.json` (ou d'un instantané
versionné) dans la base SQLite. Idempotent : chaque ligne est insérée ou
remplacée par sa clé primaire, sans jamais supprimer le reste.

Aucun secret n'est présent dans un instantané : les colonnes sensibles sont
masquées à l'export et donc ignorées à l'import.

Usage :
    python tools/import_snapshot.py --in seed/horizon_seed.json [--database chemin]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "data" / "horizon.db"
REDACTED = "[masqué]"


def import_snapshot(database: Path, snapshot: Path) -> dict[str, int]:
    if not snapshot.exists():
        raise SystemExit(f"Instantané introuvable : {snapshot}")
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    tables = payload.get("tables") or {}
    database.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    imported: dict[str, int] = {}
    try:
        existing = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table, rows in tables.items():
            if table not in existing or not isinstance(rows, list) or not rows:
                imported[table] = 0
                continue
            columns = [info["name"] for info in connection.execute(f"PRAGMA table_info({table})")]
            count = 0
            for row in rows:
                usable = {
                    key: value
                    for key, value in row.items()
                    if key in columns and value != REDACTED
                }
                if not usable:
                    continue
                keys = list(usable)
                placeholders = ",".join("?" for _ in keys)
                connection.execute(
                    f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
                    [usable[key] for key in keys],
                )
                count += 1
            imported[table] = count
        connection.commit()
    finally:
        connection.close()
    return imported


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restauration d'un instantané JSON.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--in", dest="snapshot", type=Path, required=True)
    args = parser.parse_args(argv)

    counts = import_snapshot(args.database, args.snapshot)
    total = sum(counts.values())
    print(f"Lignes restaurées : {total}")
    for table, count in counts.items():
        if count:
            print(f"  - {table}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
