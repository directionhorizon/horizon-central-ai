"""HORIZON CENTRAL AI — API du cœur : sessions et capacités locales, sans faux modèle IA."""
from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from horizon import llm as llm_adapter
from horizon import sync_worker
from horizon.auth import auth_enabled
from horizon.repositories import llm as llm_repo
from horizon.repositories import operations as operations_repo
from horizon.routers import core as core_router
from horizon.routers import (
    auth as auth_router, diagnostics, documents, integrations, llm_models, missions,
    operations, orchestrators, projects, skills, sync, system,
)
from horizon.schema import run_migrations

load_dotenv()
DB_PATH = Path(os.getenv("HORIZON_DATABASE_PATH", "./data/horizon.db")).expanduser()
ORIGINS = [x.strip() for x in os.getenv(
    "HORIZON_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if x.strip()]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            content TEXT NOT NULL, created_at TEXT NOT NULL
        )""")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    run_migrations()
    # Synchronisation automatique : inactif par défaut (HORIZON_SYNC_AUTO=1
    # pour l'activer). Le démarrage n'est jamais bloqué par le réseau.
    worker = asyncio.create_task(sync_worker.run_loop())
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass


app = FastAPI(title="HORIZON CENTRAL AI — Core API", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=ORIGINS, allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Horizon-Token"],
)

# --- Garde-fou réseau et en-têtes de sécurité ---------------------------------
# L'application a été conçue pour un poste unique : sans authentification, elle
# ne doit jamais être joignable depuis un autre hôte. Si un nom d'hôte non local
# arrive (proxy, tunnel, domaine public) et qu'aucune authentification n'est
# configurée, l'API refuse de répondre au lieu d'exposer les données.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "testserver"}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self'",
    "worker-src 'self' blob:",
    "connect-src 'self' " + " ".join(ORIGINS),
])


def _host_name(request: Request) -> str:
    """Nom d'hôte demandé, sans port ni crochets IPv6."""
    raw = request.headers.get("host", "")
    if raw.startswith("["):
        return raw[1:].split("]", 1)[0].strip().lower()
    return raw.split(":", 1)[0].strip().lower()


def _is_local_host(host: str) -> bool:
    return host in LOCAL_HOSTS or host.endswith(".localhost")


@app.middleware("http")
async def harden(request: Request, call_next):
    host = _host_name(request)
    path = request.url.path
    if (
        not _is_local_host(host)
        and not auth_enabled()
        and path.startswith("/api/")
        and path != "/api/v1/health"
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Accès distant refusé : aucune authentification n'est configurée. "
                    "Définir HORIZON_ADMIN_TOKEN (ou l'authentification Google) avant "
                    "d'exposer l'application hors de cette machine."
                ),
                "code": "auth_required_for_remote_access",
            },
        )

    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    forwarded = request.headers.get("x-forwarded-proto", request.url.scheme)
    if forwarded.split(",", 1)[0].strip().lower() == "https":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

# Modules métier (monolithe modulaire) : projets, orchestrateurs, missions,
# fournisseurs LLM, journal, supervision et moteur de planification.
for module in (
    auth_router,
    projects,
    orchestrators,
    missions,
    documents,
    llm_models,
    integrations,
    operations,
    skills,
    sync,
    system,
    diagnostics,
    core_router,
):
    app.include_router(module.router)


class SessionCreate(BaseModel):
    title: str = Field(default="Nouvelle session", min_length=1, max_length=160)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "horizon-core", "version": app.version, "timestamp": now()}


@app.get("/api/v1/capabilities")
def capabilities():
    with connect() as db:
        providers = llm_repo.list_providers(db)
        available = [item for item in providers if item.get("status") == "available"]
        orchestrator_count = db.execute(
            "SELECT COUNT(*) AS n FROM orchestrators WHERE status='active'"
        ).fetchone()["n"]
        project_count = db.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE status<>'archived'"
        ).fetchone()["n"]
        mission_count = db.execute("SELECT COUNT(*) AS n FROM missions").fetchone()["n"]

    if available:
        llm_status, llm_detail = "available", f"{len(available)} fournisseur(s) vérifié(s)."
        llm_verified = available[0].get("last_checked_at")
    elif providers:
        llm_status, llm_detail, llm_verified = "unverified", f"{len(providers)} fournisseur(s) non vérifié(s).", None
    else:
        llm_status, llm_detail, llm_verified = "not_configured", "Aucun fournisseur enregistré.", None

    return {
        "schema_version": "1.1", "generated_at": now(),
        "capabilities": [
            {"id": "core.sessions", "status": "available", "verified_at": now(), "detail": "Sessions SQLite locales."},
            {"id": "core.projects", "status": "available", "verified_at": now(), "detail": f"{project_count} projet(s) actif(s)."},
            {"id": "core.orchestrators", "status": "available" if orchestrator_count else "not_configured", "verified_at": now(), "detail": f"{orchestrator_count} orchestrateur(s) actif(s)."},
            {"id": "core.missions", "status": "available", "verified_at": now(), "detail": f"{mission_count} mission(s) enregistrée(s)."},
            {"id": "llm.default", "status": llm_status, "verified_at": llm_verified, "detail": llm_detail},
            {"id": "memory.google_drive", "status": "not_configured", "verified_at": None, "detail": "Connecteur non raccordé."},
            {"id": "repository.github", "status": "not_configured", "verified_at": None, "detail": "Synchronisation non raccordée."},
            {"id": "system.metrics", "status": "available", "verified_at": now(), "detail": "Sonde Windows réelle (ctypes + shutil)."},
        ]
    }


@app.post("/api/v1/sessions", status_code=201)
def create_session(payload: SessionCreate):
    sid, stamp = str(uuid.uuid4()), now()
    with connect() as db:
        db.execute("INSERT INTO sessions(id,title,created_at,updated_at) VALUES(?,?,?,?)", (sid, payload.title, stamp, stamp))
    return {"id": sid, "title": payload.title, "created_at": stamp, "updated_at": stamp}


@app.get("/api/v1/sessions")
def list_sessions(limit: int = 30):
    with connect() as db:
        rows = db.execute("SELECT id,title,created_at,updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?", (max(1, min(limit, 100)),)).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/v1/sessions/{session_id}")
def read_session(session_id: str):
    with connect() as db:
        session = db.execute("SELECT id,title,created_at,updated_at FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not session:
            raise HTTPException(404, "Session introuvable.")
        messages = db.execute("SELECT id,role,content,created_at FROM messages WHERE session_id=? ORDER BY created_at,id", (session_id,)).fetchall()
    return {**dict(session), "messages": [dict(row) for row in messages]}


@app.post("/api/v1/sessions/{session_id}/messages", status_code=202)
async def add_message(session_id: str, payload: MessageCreate):
    stamp, mid = now(), str(uuid.uuid4())
    with connect() as db:
        exists = db.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "Session introuvable.")
        db.execute("INSERT INTO messages(id,session_id,role,content,created_at) VALUES(?,?, 'user', ?, ?)", (mid, session_id, payload.content, stamp))
        db.execute("UPDATE sessions SET updated_at=? WHERE id=?", (stamp, session_id))
    # Aucun modèle vérifié : statut honnête conservé, aucune réponse inventée.
    with connect() as db:
        provider, model = llm_repo.resolve_for_use(db)
    if provider is None or not model:
        return {
            "session_id": session_id,
            "message": {"id": mid, "role": "user", "content": payload.content, "created_at": stamp},
            "execution": {"status": "accepted_no_model", "provider_id": None, "model_id": None, "fallback_used": False},
            "warnings": ["Message enregistré. Aucun modèle IA vérifié n'est disponible : aucune réponse assistant n'a été générée."],
        }

    with connect() as db:
        history = db.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY created_at, id",
            (session_id,),
        ).fetchall()
    conversation = [{"role": row["role"], "content": row["content"]} for row in history]

    try:
        result = await llm_adapter.chat(provider, conversation, model=model)
    except llm_adapter.LLMError as error:
        with connect() as db:
            operations_repo.log(
                db, actor="local-admin", action="message.llm", target_type="session",
                target_id=session_id, result="failed", detail=str(error),
            )
        return {
            "session_id": session_id,
            "message": {"id": mid, "role": "user", "content": payload.content, "created_at": stamp},
            "execution": {"status": "failed", "provider_id": provider.get("id"), "model_id": model, "fallback_used": False},
            "warnings": [f"Le fournisseur a échoué : {error}"],
        }

    with connect() as db:
        aid, astamp = str(uuid.uuid4()), now()
        db.execute(
            "INSERT INTO messages(id,session_id,role,content,created_at) VALUES(?,?, 'assistant', ?, ?)",
            (aid, session_id, result["content"], astamp),
        )
        db.execute("UPDATE sessions SET updated_at=? WHERE id=?", (astamp, session_id))
        operations_repo.log(
            db, actor="local-admin", action="message.llm", target_type="session",
            target_id=session_id, result="success",
            detail=f"Réponse générée par {result.get('provider_id')} ({result.get('model')}).",
        )
    return {
        "session_id": session_id,
        "message": {"id": aid, "role": "assistant", "content": result["content"], "created_at": astamp},
        "execution": {"status": "completed", "provider_id": result.get("provider_id"), "model_id": result.get("model"), "fallback_used": False},
        "citations": [],
        "warnings": [],
    }


@app.post("/api/v1/sessions/{session_id}/reset")
def reset_session(session_id: str):
    stamp = now()
    with connect() as db:
        exists = db.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "Session introuvable.")
        db.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        db.execute("UPDATE sessions SET updated_at=? WHERE id=?", (stamp, session_id))
    return {"session_id": session_id, "status": "reset", "updated_at": stamp}


# --- Service de l'interface (mode application de bureau, hors ligne) ---------
# Le backend sert lui-même le build de production : un seul processus suffit,
# aucune connexion Internet n'est nécessaire pour ouvrir l'application.
DIST_DIR = Path(__file__).resolve().parent.parent / "dist"


@app.get("/api/v1/system/desktop", include_in_schema=False)
def desktop_info():
    """Informations minimales de démarrage (aucun chemin ni détail d'infrastructure)."""
    return {
        "mode": "desktop_offline_first",
        "version": app.version,
        "ui_bundled": (DIST_DIR / "index.html").exists(),
    }


if (DIST_DIR / "index.html").exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    if (DIST_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    # Le shell HTML n'est jamais mis en cache : apres un rebuild, une fenetre
    # deja ouverte ne peut donc pas rester bloquee sur un ancien bundle supprime.
    # Les fichiers /assets sont hachés par Vite : leur cache est sans risque.
    NO_STORE = {
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_ui(full_path: str):
        """Sert l'interface locale et renvoie index.html pour les routes SPA."""
        if full_path.startswith("api/"):
            raise HTTPException(404, "Route API inconnue.")
        candidate = (DIST_DIR / full_path).resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError:
            return FileResponse(DIST_DIR / "index.html", headers=NO_STORE)
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html", headers=NO_STORE)
