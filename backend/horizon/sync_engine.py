"""Moteur de synchronisation Offline-First.

Logique partagée entre les routes HTTP (`routers/sync.py`) et le worker
automatique (`sync_worker.py`). Aucune donnée n'est supprimée : un conflit est
toujours consigné, jamais écrasé silencieusement.

Le moteur ne s'exécute que si un fournisseur distant est réellement configuré.
Sinon il ne fait rien et la file locale reste intacte.
"""
from __future__ import annotations

import json
from typing import Any

from .db import connect
from .repositories import operations, sync
from .sync_provider import SyncError, SyncProvider

# Tables distantes autorisées. Aucune table arbitraire n'est poussée.
ALLOWED_ENTITIES = {
    "projects": "projects",
    "orchestrators": "orchestrators",
    "missions": "missions",
    "documents": "documents",
}


class UnknownEntity(ValueError):
    """Entité absente de la liste blanche."""


def table_for(entity: str) -> str:
    table = ALLOWED_ENTITIES.get(entity)
    if table is None:
        raise UnknownEntity(f"Entité non synchronisable : {entity}")
    return table


def push_pending(provider: SyncProvider | None, actor: str = "sync_worker") -> dict[str, Any]:
    """Pousse les entrées en attente. Sans fournisseur, ne touche à rien."""
    with connect() as db:
        pending = sync.list_outbox(db, status="pending", limit=200)
        if provider is None:
            return {
                "status": "not_configured",
                "detail": "Aucun fournisseur distant configuré. La file locale est conservée.",
                "pushed": 0,
                "failed": 0,
                "conflicts": 0,
                "pending": len(pending),
            }
        pushed = failed = conflicts = 0
        for item in pending:
            try:
                table = table_for(item["entity"])
                remote = provider.push(table, json.loads(item["payload_json"] or "{}"))
                sync.mark_synced(db, item["id"], remote.get("updated_at"))
                pushed += 1
            except UnknownEntity:
                sync.mark_failed(db, item["id"], "Entité non synchronisable.")
                failed += 1
            except SyncError as exc:
                message = str(exc)
                if "HTTP 409" in message or "23505" in message:
                    sync.mark_conflict(db, item["id"], message)
                    sync.record_conflict(
                        db, item["entity"], item["entity_id"],
                        "Conflit distant (enregistrement déjà modifié).",
                    )
                    conflicts += 1
                else:
                    sync.mark_failed(db, item["id"], message)
                    failed += 1
        operations.log(
            db, actor=actor, action="sync.push", target_type="sync",
            target_id=None, result="success",
            detail=f"pushed={pushed} failed={failed} conflicts={conflicts}",
        )
    return {"status": "completed", "pushed": pushed, "failed": failed, "conflicts": conflicts}


def pull_remote(provider: SyncProvider | None, actor: str = "sync_worker") -> dict[str, Any]:
    """Récupère les modifications distantes. Aucune écriture locale n'est forcée."""
    with connect() as db:
        if provider is None:
            return {
                "status": "not_configured",
                "detail": "Aucun fournisseur distant configuré. Aucune donnée locale n'a été modifiée.",
                "pulled": 0,
                "conflicts": 0,
            }
        pulled = conflicts = 0
        for entity, table in ALLOWED_ENTITIES.items():
            row = db.execute(
                "SELECT MAX(last_synced_at) AS since FROM sync_state WHERE entity=?", (entity,)
            ).fetchone()
            since = row["since"] if row else None
            try:
                remote_items = provider.pull(table, since)
            except SyncError as exc:
                sync.record_conflict(db, entity, "*", f"Échec de lecture distante : {exc}")
                conflicts += 1
                continue
            for remote in remote_items:
                remote_id = remote.get("id")
                if not remote_id:
                    continue
                remote_updated = remote.get("updated_at")
                local_row = db.execute(
                    "SELECT local_updated_at FROM sync_state WHERE entity=? AND entity_id=?",
                    (entity, remote_id),
                ).fetchone()
                pending_row = db.execute(
                    "SELECT COUNT(*) AS n FROM sync_outbox WHERE entity=? AND entity_id=? AND status='pending'",
                    (entity, remote_id),
                ).fetchone()
                local_updated = local_row["local_updated_at"] if local_row else None
                if (
                    remote_updated
                    and local_updated
                    and remote_updated > local_updated
                    and pending_row
                    and int(pending_row["n"]) > 0
                ):
                    sync.record_conflict(
                        db, entity, remote_id,
                        "Modification locale et distante simultanées.",
                        local_updated_at=local_updated, remote_updated_at=remote_updated,
                    )
                    conflicts += 1
                    continue
                pulled += 1
        operations.log(
            db, actor=actor, action="sync.pull", target_type="sync",
            target_id=None, result="success", detail=f"pulled={pulled} conflicts={conflicts}",
        )
    return {"status": "completed", "pulled": pulled, "conflicts": conflicts}
