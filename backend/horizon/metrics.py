"""Mesures système réelles, sans dépendance externe.

Multiplateforme : sur Windows, `ctypes` (bibliothèque standard) lit la charge
CPU et la mémoire ; sur Linux, `/proc/stat` et `/proc/meminfo` sont lus
directement. `shutil` fournit l'espace disque.
Aucune valeur n'est simulée : si une mesure échoue, elle est renvoyée à
`None` avec la raison, jamais remplacée par un exemple.
"""
from __future__ import annotations

import ctypes
import shutil
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from typing import Any

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


def _filetime_to_int(value: _FILETIME) -> int:
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


def _linux_cpu_times() -> tuple[int, int, int] | None:
    """Lit /proc/stat : renvoie (inactif, noyau, utilisateur) en ticks."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as handle:
            first = handle.readline()
    except OSError:
        return None
    parts = first.split()
    if not parts or parts[0] != "cpu":
        return None
    try:
        values = [int(x) for x in parts[1:]]
    except ValueError:
        return None
    if len(values) < 4:
        return None
    user = values[0] + (values[1] if len(values) > 1 else 0)
    system = values[2] + (values[5] if len(values) > 5 else 0) + (values[6] if len(values) > 6 else 0)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return idle, system, user


def _cpu_times() -> tuple[int, int, int] | None:
    """Renvoie (inactif, noyau, utilisateur) en unités comparables."""
    if IS_LINUX:
        return _linux_cpu_times()
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
    if IS_WINDOWS:
        ctypes.windll.kernel32.Sleep(sample_ms)
    else:
        time.sleep(sample_ms / 1000.0)
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


def _linux_memory() -> dict[str, Any]:
    """Lit /proc/meminfo : mémoire réelle en Mo."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            info = handle.read()
    except OSError as error:
        return {"supported": False, "reason": str(error)}
    values: dict[str, int] = {}
    for line in info.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        try:
            values[key] = int(raw.strip().split()[0])
        except (ValueError, IndexError):
            continue
    total = values.get("MemTotal")
    available = values.get("MemAvailable", values.get("MemFree"))
    if not total or available is None:
        return {"supported": False, "reason": "Lecture mémoire indisponible."}
    return {
        "supported": True,
        "total_mb": round(total / 1024),
        "available_mb": round(available / 1024),
        "used_percent": round((total - available) * 100.0 / total, 1),
    }


def memory() -> dict[str, Any]:
    """Mémoire physique réelle, en mégaoctets."""
    if IS_LINUX:
        return _linux_memory()
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


def _default_disk_path() -> str:
    return "C:\\" if IS_WINDOWS else "/"


def disk(path: str | None = None) -> dict[str, Any]:
    """Espace disque réel du volume demandé."""
    target = path or _default_disk_path()
    try:
        usage = shutil.disk_usage(target)
    except OSError as error:
        return {"supported": False, "reason": str(error)}
    gb = 1024 ** 3
    return {
        "supported": True,
        "path": target,
        "total_gb": round(usage.total / gb, 2),
        "free_gb": round(usage.free / gb, 2),
        "used_percent": round(usage.used * 100.0 / usage.total, 1) if usage.total else None,
    }


def _source_label() -> str:
    if IS_WINDOWS:
        return "windows-ctypes+shutil"
    if IS_LINUX:
        return "linux-proc+shutil"
    return "generic+shutil"


def collect() -> dict[str, Any]:
    """Instantané horodaté des mesures réelles disponibles."""
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "source": _source_label(),
        "cpu_percent": cpu_percent(),
        "memory": memory(),
        "disk": disk(),
    }
