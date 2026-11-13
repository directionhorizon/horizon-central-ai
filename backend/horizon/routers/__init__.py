"""Routeurs FastAPI additionnels, inclus depuis `backend/app.py`."""
from . import auth, core, documents, diagnostics, integrations, llm_models, missions, operations, orchestrators, projects, sync, system

__all__ = [
    "auth",
    "core",
    "diagnostics",
    "documents",
    "integrations",
    "llm_models",
    "missions",
    "operations",
    "orchestrators",
    "projects",
    "sync",
    "system",
]
