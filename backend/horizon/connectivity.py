"""Détection réelle de la connectivité Internet.

Aucune dépendance à un service payant : une connexion TCP courte vers un hôte
public configurable (`HORIZON_CONNECTIVITY_PROBE`, format `hôte:port`). Le
résultat est un fait mesuré, jamais une supposition.
"""
from __future__ import annotations

import os
import socket
from datetime import datetime, timezone

DEFAULT_PROBE = "1.1.1.1:443"
DEFAULT_TIMEOUT_S = 2.5


def _target() -> tuple[str, int]:
    raw = os.getenv("HORIZON_CONNECTIVITY_PROBE", DEFAULT_PROBE).strip() or DEFAULT_PROBE
    host, _, port = raw.partition(":")
    try:
        return host or "1.1.1.1", int(port or "443")
    except ValueError:
        return "1.1.1.1", 443


def check() -> dict:
    """Renvoie l'état réseau mesuré, sans jamais lever d'exception."""
    host, port = _target()
    started = datetime.now(timezone.utc)
    try:
        with socket.create_connection((host, port), timeout=DEFAULT_TIMEOUT_S):
            online = True
            error = ""
    except OSError as exc:
        online = False
        error = f"{type(exc).__name__}: {exc}"
    return {
        "online": online,
        "target": f"{host}:{port}",
        "checked_at": started.isoformat(),
        "error": error,
    }
