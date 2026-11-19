"""Applique les migrations SQL de supabase/migrations/ sur la base Supabase.

Fiable en CI : on se connecte via une URL fournie (SUPABASE_DB_URL), typiquement
le **pooler IPv4** de Supabase (compatible avec les runners GitHub IPv4). On tient
un historique (table `supabase_migrations.schema_migrations`) pour ne jamais
rejouer une migration déjà appliquée.

Aucun secret n'est écrit dans le dépôt : l'URL vient de l'environnement.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
HISTORY_TABLE = "supabase_migrations.schema_migrations"


def main() -> int:
    dsn = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        print("SUPABASE_DB_URL manquant.", file=sys.stderr)
        return 1

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("Aucune migration à appliquer.")
        return 0

    conn = psycopg2.connect(dsn, connect_timeout=30)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "create schema if not exists supabase_migrations;"
                f" create table if not exists {HISTORY_TABLE} ("
                "  version text primary key,"
                "  name text not null,"
                "  applied_at timestamptz not null default now())"
            )
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(f"select version from {HISTORY_TABLE}")
            applied = {row[0] for row in cur.fetchall()}

        count = 0
        for path in files:
            version = path.name
            if version in applied:
                print(f"= deja appliquee : {version}")
                continue
            print(f"+ application : {version}")
            with conn.cursor() as cur:
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    f"insert into {HISTORY_TABLE}(version, name) values(%s, %s)",
                    (version, version),
                )
            conn.commit()
            count += 1

        print(f"Termine : {count} migration(s) appliquee(s).")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
