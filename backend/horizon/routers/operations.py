"""Routes de lecture du journal d'opérations."""
from __future__ import annotations

from fastapi import APIRouter

from ..db import connect
from ..repositories import operations

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("")
def list_operations(limit: int = 100, target_type: str | None = None):
    with connect() as db:
        items = operations.list_entries(db, limit=limit, target_type=target_type)
    return {"items": items}
