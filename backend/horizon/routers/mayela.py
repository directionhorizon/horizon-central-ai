"""Routes de lecture du flux MAYELA (lecture seule, aucun secret renvoyé).

HORIZON ne fait que lire : aucune route n'écrit, ni dans MAYELA, ni dans une
comptabilité. Le paramètre `limit` est borné par le module `mayela_feed`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_admin
from .. import mayela_feed as feed

router = APIRouter(prefix="/api/v1/mayela", tags=["mayela"])


def _read(view: str, limit: int) -> dict:
    try:
        items = feed.fetch(view, limit=limit)
    except feed.MayelaError as error:
        raise HTTPException(502, str(error)) from error
    return {"view": view, "count": len(items), "items": items}


@router.get("/status")
def mayela_status(actor: str = Depends(require_admin)):
    """Configuration, joignabilité et compteurs, sans jamais échouer."""
    return feed.status()


@router.get("/posts")
def mayela_posts(
    limit: int = Query(200, ge=1, le=feed.MAX_LIMIT),
    actor: str = Depends(require_admin),
):
    """Publications MAYELA (Meta, TikTok…), les plus récentes d'abord."""
    return _read("posts", limit)


@router.get("/ads")
def mayela_ads(
    limit: int = Query(200, ge=1, le=feed.MAX_LIMIT),
    actor: str = Depends(require_admin),
):
    """Dépenses publicitaires par jour et par campagne."""
    return _read("ads", limit)


@router.get("/flux")
def mayela_flux(
    limit: int = Query(200, ge=1, le=feed.MAX_LIMIT),
    actor: str = Depends(require_admin),
):
    """Flux financiers observés : ventes et créances."""
    return _read("flux", limit)
