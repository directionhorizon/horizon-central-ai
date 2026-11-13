"""Dépôts de données par domaine.

Chaque module expose des fonctions pures qui prennent une connexion SQLite
(`sqlite3.Connection`) en premier argument. Ce découpage permet de remplacer
plus tard l'implémentation locale par un adaptateur distant sans toucher aux
routeurs.
"""
from . import documents, integrations, llm, missions, operations, orchestrators, projects, sync

__all__ = [
    "documents",
    "integrations",
    "llm",
    "missions",
    "operations",
    "orchestrators",
    "projects",
    "sync",
]
