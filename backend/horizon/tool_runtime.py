"""Exécution des mains (outils) des agents.

Chaque main possède un chemin d'exécution défini :
- une main « native » est réellement exécutée ici ;
- une main qui dépend d'un service externe (connecteur, MCP, matériel) refuse
  honnêtement tant que ce service n'est pas disponible : jamais de faux résultat.

Garde-fous : tout accès fichier est confiné à un espace de travail autorisé,
chaque commande a un délai maximal, et les sorties sont bornées.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

DEFAULT_TIMEOUT = 20.0
MAX_OUTPUT = 20000

#: Espace de travail autorisé : aucune main ne peut sortir de ce dossier.
WORKSPACE = Path(os.getenv("HORIZON_WORKSPACE_DIR", "./workspace")).resolve()

Handler = Callable[[Any, dict[str, Any]], Awaitable[dict[str, Any]]]
_HANDLERS: dict[str, Handler] = {}


class ToolError(RuntimeError):
    """Erreur d'exécution d'une main, message lisible et sans secret."""


def handler(tool_id: str):
    """Déclare le gestionnaire d'une main."""

    def decorate(fn: Handler) -> Handler:
        _HANDLERS[tool_id] = fn
        return fn

    return decorate


def is_executable(tool_id: str) -> bool:
    return tool_id in _HANDLERS


def executable_tools() -> list[str]:
    return sorted(_HANDLERS)


def _clip(text: str) -> str:
    return text[:MAX_OUTPUT]


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_path(rel: str) -> Path:
    """Résout un chemin relatif en le confinant à l'espace de travail."""
    cleaned = (rel or "").strip().lstrip("/\\")
    target = (WORKSPACE / cleaned).resolve()
    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ToolError("Chemin hors de l'espace de travail autorisé.")
    return target


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


# --- Famille 1 : machine (fichiers, code, terminal) -------------------------

@handler("tool-file-list")
async def _file_list(_db, params: dict[str, Any]) -> dict[str, Any]:
    target = _safe_path(params.get("path", "."))
    if not target.is_dir():
        raise ToolError("Dossier introuvable.")
    items = sorted(entry.name for entry in target.iterdir())
    return {"path": _rel(target), "items": items[:500], "count": len(items)}


@handler("tool-file-read")
async def _file_read(_db, params: dict[str, Any]) -> dict[str, Any]:
    target = _safe_path(params.get("path", ""))
    if not target.is_file():
        raise ToolError("Fichier introuvable.")
    return {
        "path": _rel(target),
        "content": _clip(target.read_text(encoding="utf-8", errors="replace")),
    }


@handler("tool-file-write")
async def _file_write(_db, params: dict[str, Any]) -> dict[str, Any]:
    if not str(params.get("path") or "").strip():
        raise ToolError("Chemin requis.")
    target = _safe_path(params.get("path", ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    content = str(params.get("content", ""))
    target.write_text(content, encoding="utf-8")
    return {"path": _rel(target), "bytes": len(content.encode("utf-8"))}


@handler("tool-file-patch")
async def _file_patch(_db, params: dict[str, Any]) -> dict[str, Any]:
    target = _safe_path(params.get("path", ""))
    if not target.is_file():
        raise ToolError("Fichier introuvable.")
    old, new = str(params.get("old", "")), str(params.get("new", ""))
    if not old:
        raise ToolError("Texte à remplacer manquant.")
    text = target.read_text(encoding="utf-8", errors="replace")
    if old not in text:
        raise ToolError("Texte à remplacer introuvable dans le fichier.")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    return {"path": _rel(target), "patched": True}


def _run_process(argv: list[str] | str, shell: bool) -> dict[str, Any]:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            argv, cwd=str(WORKSPACE), shell=shell,
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as error:
        raise ToolError(f"Délai dépassé ({DEFAULT_TIMEOUT:.0f} s).") from error
    return {
        "stdout": _clip(proc.stdout),
        "stderr": _clip(proc.stderr),
        "returncode": proc.returncode,
    }


@handler("tool-code-python")
async def _code_python(_db, params: dict[str, Any]) -> dict[str, Any]:
    code = str(params.get("code", ""))
    if not code.strip():
        raise ToolError("Code manquant.")
    return await asyncio.to_thread(_run_process, [sys.executable, "-c", code], False)


@handler("tool-terminal")
async def _terminal(_db, params: dict[str, Any]) -> dict[str, Any]:
    command = str(params.get("command", "")).strip()
    if not command:
        raise ToolError("Commande manquante.")
    return await asyncio.to_thread(_run_process, command, True)


# --- Famille 2 : monde (web, flux, notifications) ---------------------------

def _require_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ToolError("URL http(s) requise.")
    return url


@handler("tool-web-extract")
async def _web_extract(_db, params: dict[str, Any]) -> dict[str, Any]:
    url = _require_url(params.get("url"))
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "horizon-agent"})
    if response.status_code >= 400:
        raise ToolError(f"HTTP {response.status_code} sur {url}.")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", response.text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {"url": url, "text": _clip(text)}


@handler("tool-api-call")
async def _api_call(_db, params: dict[str, Any]) -> dict[str, Any]:
    url = _require_url(params.get("url"))
    method = str(params.get("method", "GET")).upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        raise ToolError("Méthode non autorisée.")
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=False) as client:
        response = await client.request(method, url, json=params.get("body"))
    return {"status": response.status_code, "body": _clip(response.text)}


@handler("tool-rss")
async def _rss(_db, params: dict[str, Any]) -> dict[str, Any]:
    url = _require_url(params.get("url"))
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise ToolError(f"HTTP {response.status_code} sur {url}.")
    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as error:
        raise ToolError("Flux RSS illisible.") from error
    items: list[dict[str, str]] = []
    for node in root.iter():
        if node.tag.endswith("item") or node.tag.endswith("entry"):
            title = next((c.text for c in node if c.tag.endswith("title")), "")
            link = next((c.get("href") or c.text for c in node if c.tag.endswith("link")), "")
            items.append({"title": (title or "").strip(), "link": (link or "").strip()})
    return {"url": url, "items": items[:50], "count": len(items)}


@handler("tool-notifications")
async def _notifications(_db, params: dict[str, Any]) -> dict[str, Any]:
    message = str(params.get("message", "")).strip()
    if not message:
        raise ToolError("Message requis.")
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    log = WORKSPACE / "notifications.log"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": _stamp(), "message": message}, ensure_ascii=False) + "\n")
    return {"notified": True, "message": message}


# --- Famille 3 : données (extraction structurée) ----------------------------

EXTRACT_PROMPT = (
    "Tu es l'extracteur de HORIZON CENTRAL AI. À partir du texte fourni, "
    "renvoie UNIQUEMENT un objet JSON valide, sans commentaire ni texte autour. "
    "N'invente aucune valeur : si une information est absente, mets null."
)


@handler("tool-data-extract")
async def _data_extract(db, params: dict[str, Any]) -> dict[str, Any]:
    from . import llm, native_engine

    text = str(params.get("text") or "").strip()
    if not text:
        raise ToolError("Texte à analyser manquant.")
    fields = params.get("fields")
    if isinstance(fields, list):
        fields_hint = ", ".join(str(item).strip() for item in fields if str(item).strip())
    else:
        fields_hint = str(fields or "").strip()
    instruction = str(params.get("instruction") or "").strip()

    directives = [EXTRACT_PROMPT]
    if fields_hint:
        directives.append(f"Champs à extraire : {fields_hint}.")
    if instruction:
        directives.append(instruction)
    try:
        provider = native_engine.choose_provider(db)
    except native_engine.NativeEngineError as error:
        raise ToolError(str(error)) from error
    try:
        result = await llm.chat(
            provider,
            [
                {"role": "system", "content": " ".join(directives)},
                {"role": "user", "content": _clip(text)},
            ],
            temperature=0.0,
        )
    except llm.LLMError as error:
        raise ToolError(str(error)) from error
    return {
        "extracted": result.get("content", ""),
        "fields": fields_hint or None,
        "model": result.get("model"),
    }


# --- Famille 3 : documents (lecture PDF) ------------------------------------

@handler("tool-pdf-read")
async def _pdf_read(_db, params: dict[str, Any]) -> dict[str, Any]:
    target = _safe_path(params.get("path", ""))
    if not target.is_file():
        raise ToolError("Fichier introuvable.")
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ToolError("Lecture PDF indisponible : bibliothèque pypdf absente.") from error
    try:
        reader = PdfReader(str(target))
        all_pages = list(reader.pages)
    except Exception as error:  # pypdf lève des erreurs variées selon le fichier
        raise ToolError("PDF illisible ou corrompu.") from error
    texts: list[str] = []
    for page in all_pages[:50]:
        try:
            texts.append((page.extract_text() or "").strip())
        except Exception:  # une page illisible ne doit pas faire échouer tout le document
            texts.append("")
    return {
        "path": _rel(target),
        "pages": len(all_pages),
        "text": _clip("\n".join(texts)),
    }


# --- Famille 5 : méta (mémoire, compétences) --------------------------------

@handler("tool-skills")
async def _skills(db, params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query", "")).strip().lower()
    rows = db.execute("SELECT id,name,category FROM skills ORDER BY name LIMIT 200").fetchall()
    items = [dict(row) for row in rows]
    if query:
        items = [item for item in items if query in (item["name"] or "").lower()]
    return {"count": len(items), "items": items[:50]}


@handler("tool-memory")
async def _memory(db, params: dict[str, Any]) -> dict[str, Any]:
    rows = db.execute(
        "SELECT id,title,project_id,created_at FROM documents ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


PLAN_PROMPT = (
    "Tu es le planificateur de HORIZON CENTRAL AI. Réponds UNIQUEMENT par un "
    "objet JSON : {\"title\": \"...\", \"steps\": [{\"title\": \"...\"}]} "
    "(2 à 12 étapes, aucune étape ne prétend être exécutée)."
)


@handler("tool-plan")
async def _plan(db, params: dict[str, Any]) -> dict[str, Any]:
    from . import llm, native_engine

    request = str(params.get("request") or params.get("goal") or "").strip()
    if not request:
        raise ToolError("Objectif manquant.")
    try:
        provider = native_engine.choose_provider(db)
    except native_engine.NativeEngineError as error:
        raise ToolError(str(error)) from error
    try:
        result = await llm.chat(
            provider,
            [
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": request},
            ],
            temperature=0.1,
        )
    except llm.LLMError as error:
        raise ToolError(str(error)) from error
    return {"plan": result.get("content", ""), "model": result.get("model")}


@handler("tool-delegate")
async def _delegate(db, params: dict[str, Any]) -> dict[str, Any]:
    from . import native_engine
    from .repositories import orchestrators

    system_id = str(params.get("system_id") or "").strip()
    task = str(params.get("task") or "").strip()
    if not system_id:
        raise ToolError("Système cible requis.")
    if not task:
        raise ToolError("Tâche requise.")
    system = orchestrators.get_orchestrator(db, system_id)
    if system is None:
        raise ToolError("Système d'orchestration introuvable.")
    mission = {
        "title": str(params.get("title") or "Tâche déléguée"),
        "description": task,
        "priority": "normal",
    }
    target_agent = str(params.get("agent_id") or "").strip() or None
    try:
        result = await native_engine.run_mission(db, system, mission, agent_id=target_agent)
    except native_engine.NativeEngineError as error:
        raise ToolError(str(error)) from error
    return {"agent": result["agent_name"], "output": result["output"], "run_id": result["run_id"]}


@handler("tool-mcp")
async def _mcp(db, params: dict[str, Any]) -> dict[str, Any]:
    from .mcp_client import MCPClient, MCPError

    server_id = str(params.get("server_id") or "").strip()
    tool_name = str(params.get("tool") or "").strip()
    if not server_id or not tool_name:
        raise ToolError("Serveur MCP et nom d'outil requis.")
    row = db.execute("SELECT * FROM mcp_servers WHERE id=?", (server_id,)).fetchone()
    if row is None:
        raise ToolError("Serveur MCP introuvable.")
    if not row["enabled"]:
        raise ToolError("Ce serveur MCP est désactivé.")
    args = json.loads(row["args_json"] or "[]")

    def _call():
        with MCPClient(row["command"], args) as client:
            return client.call_tool(tool_name, params.get("arguments") or {})

    try:
        result = await asyncio.to_thread(_call)
    except MCPError as error:
        raise ToolError(str(error)) from error
    return {"server_id": server_id, "tool": tool_name, "result": result}


@handler("tool-schedule")
async def _schedule(db, params: dict[str, Any]) -> dict[str, Any]:
    run_at = str(params.get("run_at") or "").strip()
    tool_id = str(params.get("tool_id") or "").strip()
    if not run_at or not tool_id:
        raise ToolError("Date d'exécution et outil requis.")
    if tool_id not in _HANDLERS:
        raise ToolError("La main à planifier n'est pas branchée.")
    task_params = params.get("params") or {}
    if run_at <= _stamp():
        result = await run_tool(db, {"id": tool_id}, task_params)
        return {"executed": True, "run_at": run_at, "result": result}
    tid = str(uuid.uuid4())
    db.execute(
        """INSERT INTO scheduled_tasks(id,run_at,tool_id,params_json,status,created_at)
           VALUES(?,?,?,?,'pending',?)""",
        (tid, run_at, tool_id, json.dumps(task_params, ensure_ascii=False), _stamp()),
    )
    db.commit()
    return {"scheduled": True, "id": tid, "run_at": run_at, "tool_id": tool_id}


# --- Famille 7 : sécurité et contrôle ---------------------------------------

@handler("tool-audit-log")
async def _audit_log(db, params: dict[str, Any]) -> dict[str, Any]:
    rows = db.execute("SELECT * FROM operation_log ORDER BY created_at DESC LIMIT 50").fetchall()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@handler("tool-monitoring")
async def _monitoring(db, params: dict[str, Any]) -> dict[str, Any]:
    counts = {}
    for table in ("projects", "orchestrators", "agents", "missions", "tools"):
        counts[table] = db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    return {"counts": counts, "checked_at": _stamp()}


@handler("tool-sandbox")
async def _sandbox(_db, params: dict[str, Any]) -> dict[str, Any]:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    return {"workspace": str(WORKSPACE), "exists": WORKSPACE.is_dir()}


@handler("tool-permissions")
async def _permissions(db, params: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(params.get("agent_id", "")).strip()
    if agent_id:
        rows = db.execute(
            "SELECT agent_id,tool_id FROM agent_tools WHERE agent_id=? ORDER BY tool_id",
            (agent_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT agent_id,tool_id FROM agent_tools ORDER BY agent_id,tool_id"
        ).fetchall()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


async def run_tool(db, tool: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Exécute une main branchée. Lève `ToolError` si elle ne l'est pas."""
    tool_id = str(tool.get("id") or "")
    fn = _HANDLERS.get(tool_id)
    if fn is None:
        raise ToolError(
            f"Cette main n'est pas encore branchée (mode : {tool.get('channel') or 'inconnu'})."
        )
    return await fn(db, params or {})
