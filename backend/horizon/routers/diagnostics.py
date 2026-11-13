"""Diagnostic technique **protégé**.

Toutes les informations d'infrastructure (chemins, sondes réseau, variables
attendues, métriques détaillées, version) sont regroupées ici et exigent le rôle
administrateur. Dès que `HORIZON_ADMIN_TOKEN` est défini, l'accès est refusé sans
jeton. Chaque consultation est journalisée.

Aucune valeur de secret n'est jamais renvoyée : uniquement des noms de variables
et un booléen de présence.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from .. import connectivity, metrics, sync_worker
from ..auth import require_admin, token_status
from ..db import connect, now
from ..repositories import integrations as integrations_repo
from ..repositories import llm as llm_repo
from ..repositories import operations
from ..sync_provider import provider_status

router = APIRouter(prefix="/api/v1/admin", tags=["diagnostics"])

BACKEND_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("HORIZON_DATABASE_PATH", "./data/horizon.db")).expanduser()
DIST_DIR = BACKEND_DIR.parent / "dist"


def _db_size_kb() -> int | None:
    try:
        return int(DB_PATH.stat().st_size / 1024)
    except OSError:
        return None


@router.get("/diagnostics")
def diagnostics(request: Request, actor: str = Depends(require_admin)):
    with connect() as db:
        providers = llm_repo.list_providers(db)
        counters = integrations_repo.stats(db)
        operations.log(
            db, actor=actor, action="admin.diagnostics", target_type="system",
            target_id=None, detail="Consultation du diagnostic technique.",
        )
    env_names = sorted(
        {
            provider.get("api_key_env", "")
            for provider in providers
            if provider.get("api_key_env")
        }
    )
    return {
        "generated_at": now(),
        "version": request.app.version,
        "database": {
            "path": str(DB_PATH),
            "exists": DB_PATH.exists(),
            "size_kb": _db_size_kb(),
        },
        "ui": {
            "dist_dir": str(DIST_DIR),
            "bundled": (DIST_DIR / "index.html").exists(),
        },
        "connectivity": connectivity.check(),
        "sync_provider": provider_status(),
        "sync_worker": sync_worker.status(),
        "auth": token_status(),
        "metrics": metrics.collect(),
        "llm": {
            "providers": len(providers),
            "available": len([p for p in providers if p.get("status") == "available"]),
            "key_env_names": env_names,
            "key_env_present": {name: bool(os.getenv(name, "").strip()) for name in env_names},
        },
        "integrations": counters,
    }