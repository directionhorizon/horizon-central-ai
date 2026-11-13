"""Routes de synchronisation Offline-First.

L'application reste pleinement utilisable hors ligne : ces routes ne font
qu'exposer l'état de la file d'attente, l'état de la connexion et les conflits.
Aucun envoi n'est déclenché automatiquement sans fournisseur configuré.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import connectivity, sync_worker
from ..auth import require_admin
from ..db import connect
from ..repositories import operations, sync
from ..sync_engine import UnknownEntity, pull_remote, push_pending, table_for
from ..sync_provider import get_provider, provider_status

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


def _table(entity: str) -> str:
    try:
        return table_for(entity)
    except UnknownEntity as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/status")
def sync_status():
    """État fonctionnel de la synchronisation (aucun détail d'infrastructure).

    Les éléments techniques (sonde réseau, variables attendues, worker détaillé)
    sont disponibles uniquement dans `/api/v1/admin/diagnostics`.
    """
    with connect() as db:
        counters = sync.stats(db)
        row = db.execute("SELECT MAX(last_synced_at) AS last FROM sync_state").fetchone()
        last_sync = row["last"] if row else None
    provider = provider_status()
    worker = sync_worker.status()
    online = connectivity.check().get("online", False)
    configured = bool(provider.get("configured"))
    return {
        "provider_configured": configured,
        "online": bool(online),
        "queue": counters,
        "worker_active": bool(worker.get("auto_enabled")),
        "last_sync_at": last_sync,
        # Stockage de reference : Supabase (distant) d'abord, SQLite ensuite
        # comme cache local qui garantit le fonctionnement hors ligne.
        "mode": "hybrid_remote_first" if configured else "local_cache_only",
        "primary_store": "supabase" if configured else "sqlite",
        "secondary_store": "sqlite" if configured else None,
        "note": (
            "Supabase est le stockage de reference, SQLite en est la copie locale "
            "qui permet de continuer a travailler sans connexion."
        ),
    }


@router.get("/queue")
def sync_queue(status: str = "pending", limit: int = 200):
    with connect() as db:
        items = sync.list_outbox(db, status=status or None, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/enqueue", status_code=201)
def sync_enqueue(payload: dict[str, Any], actor: str = Depends(require_admin)):
    entity = str(payload.get("entity", "")).strip()
    entity_id = str(payload.get("entity_id", "")).strip()
    operation = str(payload.get("operation", "update")).strip()
    _table(entity)
    if not entity_id:
        raise HTTPException(422, "entity_id requis.")
    if operation not in {"create", "update", "delete"}:
        raise HTTPException(422, "operation invalide.")
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    with connect() as db:
        item = sync.enqueue(db, entity, entity_id, operation, body)
        operations.log(
            db, actor=actor, action="sync.enqueue", target_type="sync",
            target_id=item.get("id"), detail=f"{entity}/{entity_id} ({operation})",
        )
    return item


@router.post("/push")
def sync_push(actor: str = Depends(require_admin)):
    """Pousse la file d'attente vers le fournisseur distant, s'il est configuré."""
    return push_pending(get_provider(), actor=actor)


@router.post("/pull")
def sync_pull(actor: str = Depends(require_admin)):
    """Récupère les modifications distantes et signale les conflits."""
    return pull_remote(get_provider(), actor=actor)


@router.get("/conflicts")
def sync_conflicts(resolved: bool = False):
    with connect() as db:
        items = sync.list_conflicts(db, resolved=resolved)
    return {"items": items, "count": len(items)}


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, actor: str = Depends(require_admin)):
    with connect() as db:
        item = sync.resolve_conflict(db, conflict_id)
        if item is None:
            raise HTTPException(404, "Conflit introuvable.")
        operations.log(
            db, actor=actor, action="sync.resolve", target_type="sync",
            target_id=conflict_id, detail="Conflit marqué comme résolu (aucune donnée écrasée).",
        )
    return item
