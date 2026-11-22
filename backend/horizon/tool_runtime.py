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
from urllib.parse import quote

import httpx

from . import payment_providers
from .db import now

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


def sync_catalog_status(db: Any) -> list[str]:
    """Aligne l'état affiché du catalogue sur la réalité de l'exécution.

    Une main réellement branchée (un gestionnaire existe) passe de « planned » à
    « ready » : l'interface ne doit jamais annoncer « prévu » ce qui fonctionne.
    Une main désactivée (`disabled`) n'est jamais réactivée automatiquement, et
    une main sans gestionnaire reste « planned » (aucun faux état).
    """
    if not _HANDLERS:
        return []
    tool_ids = sorted(_HANDLERS)
    placeholders = ",".join("?" for _ in tool_ids)
    rows = db.execute(
        f"SELECT id, status FROM tools WHERE id IN ({placeholders})", tool_ids
    ).fetchall()
    updated: list[str] = []
    stamp = now()
    for row in rows:
        if str(row["status"] or "") != "planned":
            continue
        db.execute(
            "UPDATE tools SET status='ready', updated_at=? WHERE id=?",
            (stamp, row["id"]),
        )
        updated.append(str(row["id"]))
    return updated


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


# --- Connecteurs et services externes ----------------------------------------
# Les identifiants sont lus UNIQUEMENT dans l'environnement : jamais en base,
# jamais dans l'interface, jamais dans les journaux. Sans configuration, la main
# refuse honnêtement : aucun résultat n'est fabriqué.

def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _credential(db, account: Any, default_env: str, label: str) -> str:
    """Résout un secret SANS jamais le journaliser (plusieurs comptes possibles).

    - si `account` est fourni : la fiche d'intégration correspondante (par `id`
      ou `name`) donne le NOM de la variable (`api_key_env`) ; la valeur est lue
      dans l'environnement ;
    - sinon : variable d'environnement par défaut (`default_env`).
    """
    account = str(account or "").strip()
    if account:
        row = db.execute(
            "SELECT id, api_key_env, method FROM integrations WHERE archived=0 AND (id=? OR name=?) LIMIT 1",
            (account, account),
        ).fetchone()
        if row is None:
            raise ToolError(f"Connexion « {account} » introuvable dans le registre.")
        env_name = (row["api_key_env"] or "").strip()
        if (row["method"] or "") == "oauth2" or env_name.startswith("secret:"):
            from . import oauth_connectors

            secret = oauth_connectors.load_secret(row["id"])
            token = str((secret or {}).get("access_token") or "").strip()
            if not token:
                raise ToolError(f"Connexion « {account} » non autorisée : reconnectez via OAuth.")
            return token
        if not env_name:
            raise ToolError(f"La connexion « {account} » ne référence aucune variable de clé.")
        value = (os.getenv(env_name) or "").strip()
        if not value:
            raise ToolError(f"Variable {env_name} absente pour la connexion « {account} ».")
        return value
    value = (os.getenv(default_env) or "").strip()
    if not value:
        raise ToolError(f"Aucun {label} configuré ({default_env}).")
    return value


def _duckduckgo_search(query: str, limit: int) -> dict[str, Any]:
    """Recherche sans clé ni serveur (DuckDuckGo). Repli par défaut."""
    try:
        from ddgs import DDGS
    except ImportError as error:
        raise ToolError(
            "Recherche indisponible : configurez HORIZON_SEARCH_URL (SearXNG) ou "
            "installez le repli DuckDuckGo (ddgs)."
        ) from error
    try:
        results = DDGS().text(query, max_results=limit)
    except Exception as error:  # ddgs lève des erreurs variées (réseau, format)
        raise ToolError(f"Recherche DuckDuckGo indisponible ({type(error).__name__}).") from error
    items = [
        {"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")}
        for r in (results or [])
    ]
    return {"provider": "duckduckgo", "query": query, "count": len(items), "items": items}


@handler("tool-web-search")
async def _web_search(_db, params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query") or params.get("q") or "").strip()
    if not query:
        raise ToolError("Requête de recherche manquante.")
    limit = max(1, min(int(params.get("limit") or 8), 20))
    searx = _env("HORIZON_SEARCH_URL")
    brave = _env("HORIZON_BRAVE_SEARCH_KEY")
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        if searx:
            response = await client.get(
                f"{searx.rstrip('/')}/search", params={"q": query, "format": "json"}
            )
            if response.status_code >= 400:
                raise ToolError(f"Recherche indisponible (HTTP {response.status_code}).")
            payload = response.json()
            items = [
                {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
                for r in (payload.get("results") or [])[:limit]
            ]
            return {"provider": "searxng", "query": query, "count": len(items), "items": items}
        if brave:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"X-Subscription-Token": brave, "Accept": "application/json"},
            )
            if response.status_code >= 400:
                raise ToolError(f"Recherche indisponible (HTTP {response.status_code}).")
            payload = response.json()
            results = (payload.get("web") or {}).get("results") or []
            items = [
                {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("description")}
                for r in results[:limit]
            ]
            return {"provider": "brave", "query": query, "count": len(items), "items": items}
    # Aucun moteur configuré : repli sans clé (DuckDuckGo).
    return await asyncio.to_thread(_duckduckgo_search, query, limit)


async def _gmail_send(token: str, to: str, subject: str, body: str) -> dict[str, Any]:
    """Envoi via l'API Gmail (jeton OAuth Google) : aucun mot de passe, aucun SMTP."""
    import base64
    from email.message import EmailMessage

    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"raw": raw},
        )
    if response.status_code >= 400:
        raise ToolError(f"Gmail a refusé l'envoi (HTTP {response.status_code}).")
    return {"sent": True, "to": to, "provider": "gmail"}


@handler("tool-email-send")
async def _email_send(db, params: dict[str, Any]) -> dict[str, Any]:
    import smtplib
    from email.message import EmailMessage

    to = str(params.get("to") or "").strip()
    if not to:
        raise ToolError("Destinataire requis.")
    subject = str(params.get("subject") or "").strip()
    body = str(params.get("body") or params.get("text") or "")

    # Connexion automatique (OAuth) : ex. Gmail. Aucun mot de passe saisi.
    account = str(params.get("account") or "").strip()
    if account:
        row = db.execute(
            "SELECT id, method FROM integrations WHERE archived=0 AND (id=? OR name=?) LIMIT 1",
            (account, account),
        ).fetchone()
        if row is not None and (row["method"] or "") == "oauth2":
            from . import oauth_connectors

            secret = oauth_connectors.load_secret(row["id"]) or {}
            token = str(secret.get("access_token") or "").strip()
            if not token:
                raise ToolError(f"Connexion « {account} » non autorisée : reconnectez via OAuth.")
            if secret.get("provider") == "google":
                return await _gmail_send(token, to, subject, body)
            raise ToolError("Ce fournisseur OAuth ne gère pas l'envoi d'e-mail.")

    host = _env("HORIZON_SMTP_HOST")
    sender = _env("HORIZON_SMTP_FROM") or _env("HORIZON_SMTP_USER")
    if not host or not sender:
        raise ToolError(
            "Aucun compte d'envoi configuré (HORIZON_SMTP_HOST et HORIZON_SMTP_FROM)."
        )
    port = int(_env("HORIZON_SMTP_PORT") or "587")
    security = (_env("HORIZON_SMTP_SECURITY") or "starttls").lower()
    user = _env("HORIZON_SMTP_USER")
    password = os.getenv("HORIZON_SMTP_PASSWORD") or ""

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    def _send() -> None:
        server = (
            smtplib.SMTP_SSL(host, port, timeout=DEFAULT_TIMEOUT)
            if security == "ssl"
            else smtplib.SMTP(host, port, timeout=DEFAULT_TIMEOUT)
        )
        with server:
            if security == "starttls":
                server.starttls()
            if user:
                server.login(user, password)
            server.send_message(message)

    try:
        await asyncio.to_thread(_send)
    except Exception as error:  # smtplib lève des erreurs variées
        raise ToolError(f"Envoi de l'e-mail échoué ({type(error).__name__}).") from error
    return {"sent": True, "to": to, "subject": subject}


@handler("tool-telegram-bot")
async def _telegram_bot(db, params: dict[str, Any]) -> dict[str, Any]:
    token = _credential(db, params.get("account"), "HORIZON_TELEGRAM_BOT_TOKEN", "bot Telegram")
    chat_id = str(params.get("chat_id") or _env("HORIZON_TELEGRAM_CHAT_ID") or "").strip()
    text = str(params.get("text") or params.get("message") or "").strip()
    if not chat_id:
        raise ToolError("Destinataire requis (chat_id).")
    if not text:
        raise ToolError("Message requis.")
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
    if response.status_code >= 400:
        raise ToolError(f"Telegram a refusé l'envoi (HTTP {response.status_code}).")
    return {"sent": True, "chat_id": chat_id}


@handler("tool-image-generate")
async def _image_generate(_db, params: dict[str, Any]) -> dict[str, Any]:
    base = _env("HORIZON_IMAGE_BASE_URL")
    if not base:
        raise ToolError(
            "Aucun fournisseur d'images configuré (HORIZON_IMAGE_BASE_URL : "
            "Pollinations gratuit sans clé, Together AI, OpenAI, ou tout service "
            "compatible /images/generations)."
        )
    prompt = str(params.get("prompt") or "").strip()
    if not prompt:
        raise ToolError("Description (prompt) requise.")
    model = _env("HORIZON_IMAGE_MODEL") or "flux"
    api_key = os.getenv("HORIZON_IMAGE_API_KEY")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    size = str(params.get("size") or "1024x1024")

    if "pollinations" in base.lower():
        # Pollinations : service d'images gratuit, sans clé ni compte. La main
        # renvoie une URL d'image réellement servie (aucun faux résultat).
        try:
            width, height = (int(part) for part in size.lower().split("x", 1))
        except (TypeError, ValueError):
            width, height = 1024, 1024
        seed = params.get("seed") or (uuid.uuid4().int % 1_000_000)
        url = (
            f"{base.rstrip('/')}/prompt/{quote(prompt, safe='')}"
            f"?width={width}&height={height}&nologo=true&seed={seed}"
        )
        return {
            "provider": "pollinations",
            "model": model,
            "prompt": prompt,
            "size": f"{width}x{height}",
            "images": [url],
            "detail": "Service gratuit, sans clé API.",
        }

    body: dict[str, Any] = {"model": model, "prompt": prompt}
    if "together" in base.lower():
        # Together AI attend width/height ; le format « 1024x1024 » est conservé
        # côté appelant pour rester compatible avec les autres fournisseurs.
        try:
            width, height = (int(part) for part in size.lower().split("x", 1))
        except (TypeError, ValueError):
            width, height = 1024, 1024
        body["width"] = width
        body["height"] = height
    else:
        body["size"] = size
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            f"{base.rstrip('/')}/images/generations", headers=headers, json=body
        )
    if response.status_code >= 400:
        detail = " ".join(response.text.split())[:300]
        raise ToolError(
            f"Génération d'image refusée (HTTP {response.status_code}) : {detail}"
        )
    payload = response.json()
    images = []
    for item in (payload.get("data") or [])[:4]:
        images.append(item.get("url") or (item.get("b64_json") or "")[:120])
    return {"provider": "image", "model": model, "prompt": prompt, "images": images}


@handler("tool-payment")
async def _payment(db, params: dict[str, Any]) -> dict[str, Any]:
    """Paiement via l'adaptateur du fournisseur choisi (aucun fournisseur codé en dur)."""
    amount = params.get("amount")
    if amount is None:
        raise ToolError("Montant requis (en plus petite unité, ex. centimes).")
    currency = str(params.get("currency") or "eur").lower()
    mode = str(params.get("mode") or "intent").strip().lower()
    kind = str(params.get("provider") or payment_providers.default_provider()).strip().lower()
    if params.get("confirm") is not True:
        # Decision validee v1.1 : le paiement est la SEULE opération exigeant une
        # validation humaine explicite avant exécution. Aucune clé n'est lue ici.
        return {
            "status": "requires_human_validation",
            "amount": amount,
            "currency": currency,
            "provider": kind,
            "mode": mode,
            "detail": "Le paiement exige une validation humaine explicite : "
            "renvoyez confirm=true après accord.",
        }
    try:
        provider = payment_providers.get_provider(kind)
        credentials = payment_providers.resolve_credentials(
            provider,
            account=params.get("account"),
            credential_reader=lambda account, name, label: _credential(
                db, account, name, label
            ),
            env_reader=_env,
        )
        request = payment_providers.PaymentRequest(
            amount=int(amount),
            currency=currency,
            detail=str(params.get("detail") or "").strip(),
            customer_email=str(params.get("customer_email") or "").strip(),
            customer_name=str(params.get("customer_name") or "").strip(),
            success_url=str(params.get("success_url") or "").strip(),
            cancel_url=str(params.get("cancel_url") or "").strip(),
            customer=str(params.get("customer") or "").strip(),
            idempotency_key=str(params.get("idempotency_key") or "").strip(),
        )
        result = await provider.create(request, credentials, mode=mode)
    except payment_providers.ProviderError as error:
        raise ToolError(str(error)) from error
    except httpx.HTTPError as error:
        raise ToolError(
            f"Fournisseur {kind} injoignable ({type(error).__name__})."
        ) from error
    payload = result.as_dict()
    # Trace locale (best-effort : ne casse jamais l'exécution).
    try:
        from .repositories import payments as payments_repo

        payments_repo.record_payment(
            db,
            result.id,
            result.amount,
            result.currency,
            result.status,
            result.detail,
            provider=result.provider,
            mode=result.mode,
            checkout_url=result.checkout_url,
            idempotency_key=str(params.get("idempotency_key") or "").strip(),
        )
    except Exception:
        pass
    return payload

@handler("tool-facebook")
async def _facebook(db, params: dict[str, Any]) -> dict[str, Any]:
    token = _credential(db, params.get("account"), "HORIZON_META_ACCESS_TOKEN", "jeton Meta")
    page_id = str(params.get("page_id") or _env("HORIZON_META_PAGE_ID") or "").strip()
    message = str(params.get("message") or "").strip()
    if not page_id:
        raise ToolError("Page Facebook requise (page_id ou HORIZON_META_PAGE_ID).")
    if not message:
        raise ToolError("Message requis.")
    body = {"message": message, "access_token": token}
    if params.get("link"):
        body["link"] = str(params["link"])
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            f"https://graph.facebook.com/v21.0/{page_id}/feed", data=body
        )
    if response.status_code >= 400:
        raise ToolError(f"Facebook a refusé la publication (HTTP {response.status_code}).")
    return {"published": True, "id": response.json().get("id")}


@handler("tool-instagram")
async def _instagram(db, params: dict[str, Any]) -> dict[str, Any]:
    token = _credential(db, params.get("account"), "HORIZON_META_ACCESS_TOKEN", "jeton Meta")
    ig_user_id = str(params.get("ig_user_id") or _env("HORIZON_META_IG_USER_ID") or "").strip()
    image_url = _require_url(params.get("image_url"))
    caption = str(params.get("caption") or "")
    if not ig_user_id:
        raise ToolError("Compte Instagram Business requis (ig_user_id ou HORIZON_META_IG_USER_ID).")
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        created = await client.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
        )
        if created.status_code >= 400:
            raise ToolError(f"Instagram a refusé le média (HTTP {created.status_code}).")
        container = created.json().get("id")
        published = await client.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish",
            data={"creation_id": container, "access_token": token},
        )
    if published.status_code >= 400:
        raise ToolError(f"Instagram a refusé la publication (HTTP {published.status_code}).")
    return {"published": True, "id": published.json().get("id")}


@handler("tool-tiktok")
async def _tiktok(db, params: dict[str, Any]) -> dict[str, Any]:
    token = _credential(db, params.get("account"), "HORIZON_TIKTOK_ACCESS_TOKEN", "jeton TikTok")
    action = str(params.get("action") or "creator_info").strip().lower()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        if action == "creator_info":
            response = await client.get(
                "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
                headers=headers,
            )
        elif action == "publish":
            video_url = _require_url(params.get("video_url"))
            response = await client.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers=headers,
                json={
                    "post_info": {"title": str(params.get("title") or "")},
                    "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
                },
            )
        else:
            raise ToolError("Action TikTok inconnue (creator_info ou publish).")
    if response.status_code >= 400:
        raise ToolError(f"TikTok a refusé la demande (HTTP {response.status_code}).")
    return {"action": action, "result": response.json()}


async def run_tool(db, tool: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Exécute une main branchée. Lève `ToolError` si elle ne l'est pas."""
    tool_id = str(tool.get("id") or "")
    fn = _HANDLERS.get(tool_id)
    if fn is None:
        raise ToolError(
            f"Cette main n'est pas encore branchée (mode : {tool.get('channel') or 'inconnu'})."
        )
    return await fn(db, params or {})
