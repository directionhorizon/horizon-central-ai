"""Synchronisation automatique de la file locale, quand la connexion revient.

Désactivée par défaut : HORIZON doit rester utilisable hors ligne sans effet de
bord. Elle s'active uniquement si `HORIZON_SYNC_AUTO=1` ET si un fournisseur
distant est réellement configuré.

Aucune donnée n'est supprimée, aucun conflit n'est écrasé : le worker réutilise
le moteur partagé `sync_engine` (même logique que les routes HTTP).
"""
from __future__ import annotations

import asyncio
import logging
import os

from . import connectivity, sync_provider
from .sync_engine import pull_remote, push_pending

logger = logging.getLogger("horizon.sync")
DEFAULT_INTERVAL_S = 120.0


def _enabled() -> bool:
    return os.getenv("HORIZON_SYNC_AUTO", "").strip().lower() in {"1", "true", "yes", "on"}


def _interval() -> float:
    raw = os.getenv("HORIZON_SYNC_INTERVAL_S", "").strip()
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_INTERVAL_S
    return max(30.0, min(value, 3600.0))


def _cycle() -> None:
    """Un cycle complet, exécuté hors de la boucle asyncio (I/O bloquante)."""
    provider = sync_provider.get_provider()
    if provider is None:
        return
    if not connectivity.check().get("online"):
        return
    result = push_pending(provider, actor="sync_worker")
    logger.info(
        "sync automatique : %s pushed=%s failed=%s conflicts=%s",
        result.get("status"), result.get("pushed"), result.get("failed"), result.get("conflicts"),
    )
    pull_remote(provider, actor="sync_worker")


async def run_loop() -> None:
    """Boucle de fond. Ne bloque jamais le démarrage de l'application."""
    if not _enabled():
        return
    interval = _interval()
    logger.info("synchronisation automatique active (intervalle %.0f s)", interval)
    while True:
        try:
            await asyncio.to_thread(_cycle)
        except Exception:  # noqa: BLE001 - un échec réseau ne doit jamais arrêter l'app
            logger.exception("échec du cycle de synchronisation automatique")
        await asyncio.sleep(interval)


def status() -> dict:
    """État non sensible du worker, exposé par /api/v1/sync/status."""
    return {
        "auto_enabled": _enabled(),
        "interval_s": _interval(),
        "env_flag": "HORIZON_SYNC_AUTO",
    }
