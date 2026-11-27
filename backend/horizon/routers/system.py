"""Routes de supervision et d'état système.

Les métriques sont mesurées réellement (ctypes + shutil) : aucune valeur
n'est simulée. Si une mesure échoue, elle est renvoyée à `None`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import connectivity, metrics, updater
from ..auth import require_admin, token_status
from ..db import connect, now
from ..repositories import llm as llm_repo
from ..repositories import operations

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/system/metrics")
def system_metrics():
    """Métriques mesurées. Les chemins locaux sont réservés au diagnostic protégé."""
    data = metrics.collect()
    disk = data.get("disk")
    if isinstance(disk, dict):
        disk.pop("path", None)
    return data


@router.get("/system/connectivity")
def system_connectivity():
    """État réseau mesuré (aucune supposition, aucune exception levée)."""
    return connectivity.check()


@router.get("/system/status")
def system_status():
    """État consolidé, sans aucun secret."""
    with connect() as db:
        providers = llm_repo.list_providers(db)
        selection = llm_repo.get_selection(db)
        counts = {
            "projects": _count(db, "projects", "status<>'archived'"),
            "orchestrators": _count(db, "orchestrators", "status<>'disabled'"),
            "missions": _count(db, "missions", None),
            "sessions": _count(db, "sessions", None),
            "operations": _count(db, "operation_log", None),
        }
    available = [p for p in providers if p.get("status") == "available"]
    return {
        "generated_at": now(),
        "auth": token_status(),
        "counts": counts,
        "llm": {
            "providers": len(providers),
            "available_providers": len(available),
            "selection": selection,
            "status": "available" if available else ("unverified" if providers else "not_configured"),
        },
    }


def _count(db, table: str, condition: str | None) -> int:
    query = f"SELECT COUNT(*) AS n FROM {table}"
    if condition:
        query += f" WHERE {condition}"
    row = db.execute(query).fetchone()
    return int(row["n"]) if row else 0


@router.get("/system/update")
def system_update_status():
    """Etat de la mise a jour (bouton « Mettre a jour »). Aucun secret."""
    return updater.status()


@router.post("/system/update")
def system_update_start(actor: str = Depends(require_admin)):
    """Lance la mise a jour : locale (git pull + build) ou en ligne (GitHub)."""
    result = updater.start()
    with connect() as db:
        operations.log(
            db, actor=actor, action="system.update", target_type="system", target_id=None,
            detail=f"Mise a jour demandee (mode {result.get('mode') or 'inconnu'}).",
        )
    return result
