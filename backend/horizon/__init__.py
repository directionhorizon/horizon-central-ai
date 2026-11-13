"""HORIZON CENTRAL AI — noyau applicatif modulaire.

Ce paquet contient les modules métier ajoutés au backend existant :
accès aux données, modèles, authentification, adaptateur LLM, routeurs.

Le point d'entrée historique (`backend/app.py`) reste la seule application
FastAPI servie : les routeurs sont inclus depuis ce paquet.
"""

__all__ = ["db", "schema", "models", "auth", "metrics", "llm"]
