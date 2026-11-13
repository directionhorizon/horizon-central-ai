"""Routes de supervision et d'état système.

Les métriques sont mesurées réellement (ctypes + shutil) : aucune valeur
n'est simulée. Si une mesure échoue, elle est renvoyée à `None`.
"""
from __future__ import annotations

from fastapi import APIRouter

from .. import connectivity, metrics
from ..auth import token_status
from ..db import connect, now
from ..repositories import llm as llm_repo

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
