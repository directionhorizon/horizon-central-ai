"""Mesures système réelles, sans dépendance externe.

Windows uniquement : utilisation de `ctypes` (bibliothèque standard) pour
lire la charge CPU et la mémoire, et de `shutil` pour l'espace disque.
Aucune valeur n'est simulée : si une mesure échoue, elle est renvoyée à
`None` avec la raison, jamais remplacée par un exemple.
"""
from __future__ import annotations

import ctypes
import shutil
from ctypes import wintypes
from datetime import datetime, timezone
from typing import Any

IS_WINDOWS = hasattr(ctypes, "windll")


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


def _filetime_to_int(value: _FILETIME) -> int:
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


def _cpu_times() -> tuple[int, int, int] | None:
    """Renvoie (inactif, noyau, utilisateur) en unités de 100 ns."""
    if not IS_WINDOWS:
        return None
    idle, kernel, user = _FILETIME(), _FILETIME(), _FILETIME()
    ok = ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    )
    if not ok:
        return None
    return _filetime_to_int(idle), _filetime_to_int(kernel), _filetime_to_int(user)


def cpu_percent(sample_ms: int = 120) -> float | None:
    """Charge CPU mesurée sur un intervalle court, en pourcentage."""
    first = _cpu_times()
    if first is None:
        return None
    # Attente courte, sans dépendance : nécessaire pour obtenir un delta.
    ctypes.windll.kernel32.Sleep(sample_ms)
    second = _cpu_times()
    if second is None:
        return None
    idle_delta = second[0] - first[0]
    kernel_delta = second[1] - first[1]
    user_delta = second[2] - first[2]
    total = kernel_delta + user_delta
    if total <= 0:
        return None
    busy = total - idle_delta
    return round(max(0.0, min(100.0, busy * 100.0 / total)), 1)


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def memory() -> dict[str, Any]:
    """Mémoire physique réelle, en mégaoctets."""
    if not IS_WINDOWS:
        return {"supported": False, "reason": "Sonde Windows indisponible."}
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {"supported": False, "reason": "Lecture mémoire refusée par le système."}
    mb = 1024 * 1024
    return {
        "supported": True,
        "total_mb": round(status.ullTotalPhys / mb),
        "available_mb": round(status.ullAvailPhys / mb),
        "used_percent": round(status.dwMemoryLoad, 1),
    }


def disk(path: str = "C:\\") -> dict[str, Any]:
    """Espace disque réel du volume demandé."""
    try:
        usage = shutil.disk_usage(path)
    except OSError as error:
        return {"supported": False, "reason": str(error)}
    gb = 1024 ** 3
    return {
        "supported": True,
        "path": path,
        "total_gb": round(usage.total / gb, 2),
        "free_gb": round(usage.free / gb, 2),
        "used_percent": round(usage.used * 100.0 / usage.total, 1) if usage.total else None,
    }


def collect() -> dict[str, Any]:
    """Instantané horodaté des mesures réelles disponibles."""
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "source": "windows-ctypes+shutil",
        "cpu_percent": cpu_percent(),
        "memory": memory(),
        "disk": disk(),
    }
