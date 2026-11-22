"""Catégories de compétences et outils recommandés par catégorie.

Chaque catégorie associe un domaine de travail aux outils réellement disponibles
dans le catalogue. Cette table est déclarative : elle ne crée aucun outil, elle
indique seulement lesquels mobiliser pour une compétence de ce domaine.

Les outils listés sont des identifiants du catalogue (`tools_catalog`). Un outil
absent du catalogue n'est jamais inventé : il est simplement ignoré côté interface.
"""
from __future__ import annotations

#: Catégories historiques (déjà présentes dans le catalogue de skills).
EXISTING_CATEGORIES = (
    "Création de contenu et rédaction",
    "Développement et informatique",
    "Analyse de données et recherche",
    "Productivité et gestion de projet",
    "Design, multimédia et créativité",
    "Métier et expertise spécialisée",
    "Méta-skills (IA)",
    "Développement de jeux vidéo",
)

#: Catégories ajoutées pour couvrir les activités de l'organisation.
NEW_CATEGORIES = (
    "Vente et relation client",
    "Finance et comptabilité",
    "Juridique et conformité",
    "Support et opérations",
    "Données et BI",
    "Marketing et acquisition",
    "Ressources humaines",
    "Automatisation et intégrations",
    "Sécurité et contrôle",
)

#: Outils recommandés par catégorie (identifiants du catalogue d'outils).
CATEGORY_TOOLS: dict[str, list[str]] = {
    "Création de contenu et rédaction": ["tool-web-search", "tool-email-send", "tool-image-generate"],
    "Développement et informatique": ["tool-code-python", "tool-terminal", "tool-file-write", "tool-api-call"],
    "Analyse de données et recherche": ["tool-web-search", "tool-web-extract", "tool-data-extract", "tool-spreadsheet"],
    "Productivité et gestion de projet": ["tool-email-send", "tool-notifications", "tool-office-docs"],
    "Design, multimédia et créativité": ["tool-image-generate", "tool-image-edit", "tool-design", "tool-motion-design"],
    "Métier et expertise spécialisée": ["tool-web-search", "tool-pdf-read"],
    "Méta-skills (IA)": ["tool-web-search"],
    "Développement de jeux vidéo": ["tool-code-python", "tool-model-3d", "tool-image-generate"],
    "Vente et relation client": ["tool-email-send", "tool-messaging", "tool-payment", "tool-telegram-bot"],
    "Finance et comptabilité": ["tool-payment", "tool-spreadsheet", "tool-office-docs", "tool-db-query"],
    "Juridique et conformité": ["tool-pdf-read", "tool-web-search", "tool-office-docs"],
    "Support et opérations": ["tool-email-read", "tool-messaging", "tool-telegram-bot", "tool-notifications"],
    "Données et BI": ["tool-db-query", "tool-spreadsheet", "tool-data-extract", "tool-api-call"],
    "Marketing et acquisition": ["tool-social-post", "tool-image-generate", "tool-web-search", "tool-email-send"],
    "Ressources humaines": ["tool-email-send", "tool-office-docs", "tool-pdf-read"],
    "Automatisation et intégrations": ["tool-api-call", "tool-code-python", "tool-web-extract", "tool-db-query"],
    "Sécurité et contrôle": ["tool-terminal", "tool-web-search", "tool-file-read"],
}


#: Reclassement des compétences existantes vers les catégories cibles.
#: Sert à peupler les nouvelles catégories avec des compétences déjà présentes,
#: sans en inventer. Appliqué au démarrage (idempotent).
SKILL_RECLASSIFICATION: dict[str, str] = {
    # Finance et comptabilité
    "skill-analyse-de-bilan": "Finance et comptabilité",
    "skill-previsionnel": "Finance et comptabilité",
    "skill-indicateurs-financiers": "Finance et comptabilité",
    # Juridique et conformité
    "skill-analyse-de-clauses-contractuelles": "Juridique et conformité",
    "skill-redaction-de-cgv": "Juridique et conformité",
    "skill-vulgarisation-de-textes-de-loi": "Juridique et conformité",
    "skill-conformite-rgpd": "Juridique et conformité",
    # Ressources humaines (recrutement, intégration, formation)
    "skill-fiche-de-poste": "Ressources humaines",
    "skill-grille-d-entretien": "Ressources humaines",
    "skill-plan-d-integration": "Ressources humaines",
    "skill-evaluation-de-performance": "Ressources humaines",
    "skill-quiz": "Ressources humaines",
    "skill-plan-de-cours": "Ressources humaines",
    "github-anthropic-academy-guide": "Ressources humaines",
}


def category_catalog() -> list[dict]:
    """Liste des catégories avec leurs outils recommandés."""
    items: list[dict] = []
    for category in (*EXISTING_CATEGORIES, *NEW_CATEGORIES):
        items.append(
            {
                "category": category,
                "tools": list(CATEGORY_TOOLS.get(category, [])),
                "existing": category in EXISTING_CATEGORIES,
            }
        )
    return items


def tools_for_category(category: str) -> list[str]:
    return list(CATEGORY_TOOLS.get(category, []))
