# REGISTRE DES SYSTÈMES ET PROJETS — HORIZON CENTRAL AI
**Version 0.1 — 10 novembre 2026 — document de travail (audit étape 3, politique §7)**
Statut : provisoire. Aucune entrée ne vaut décision technique. Les faits sont vérifiés, les hypothèses sont marquées.

## 1. Règle de lecture

La politique (§2, §4) distingue quatre niveaux. Ils ne sont jamais interchangeables :

**HORIZON CENTRAL AI** (application de supervision) → **système d'orchestration** (responsable opérationnel) → **projet** (unité métier) → **ressource**.

- Un projet **n'est pas** un système. Un système **n'est pas** l'application qui le supervise.
- Un système peut **exister sans être intégré** (cas Hermès).
- Un système peut être **conceptualisé sans exister** (cas GAMEFORGE).
- HORIZON CENTRAL AI ne porte pas la responsabilité d'un projet : elle supervise le système qui la porte.

## 2. Systèmes d'orchestration recensés

| Système | État vérifié | Intégration dans HORIZON CENTRAL AI | Projets sous responsabilité | Preuve |
|---|---|---|---|---|
| **Système d'orchestration existant dans Hermès** | **existant** (hors du périmètre local audité) | **non intégré** — candidat n°1 | MAYELA CRM | déclaration du responsable ; aucune interface vérifiée localement |
| **GAMEFORGE** | **conceptualisé — non mis sur pied** | à créer *dans* HORIZON CENTRAL AI | KING OF THE FOREST | déclaration du responsable ; aucun artefact fonctionnel |

> Aucun des deux systèmes n'a d'interface, de connecteur ni de contrat d'API **vérifié**. Leur présence dans ce registre atteste d'une **désignation**, pas d'une capacité opérationnelle.

## 3. Projets recensés

### 3.1 MAYELA CRM — projet (application)
| Champ | Valeur |
|---|---|
| Nature | Application métier (CRM) |
| Système responsable | Système d'orchestration Hermès (désigné, non intégré) |
| Source autoritaire — données structurées | Supabase `mayela-crm` · ref `ymqdmfsqtkmlmwffqskt` · eu-central-1 · ACTIVE_HEALTHY (ex-`nzila-crm`, renommé le 10/11/2026) |
| Source autoritaire — code | GitHub `directionhorizon/mayela-crm` (privé, HTML, 2 178 Ko, dernier push 21/10/2026) ; homepage Vercel déclarée |
| Source autoritaire — documents/médias | **non déclarée** (Drive non examiné) |
| Classification | à établir — contient des données clients, donc au minimum **Confidentiel** (hypothèse, non validée) |
| Systèmes contributeurs | aucun |
| Statut | **projet mono-système** ; le catalyseur « projet partagé » (§5) n'est pas déclenché |

### 3.2 KING OF THE FOREST — projet (jeu vidéo)
| Champ | Valeur |
|---|---|
| Nature | Jeu vidéo |
| Système responsable | **GAMEFORGE** (conceptualisé, non opérationnel) |
| Sources autoritaires | **aucune vérifiée** : aucun dépôt GitHub correspondant, aucun projet Supabase correspondant, Drive non examiné |
| Emplacement présumé | Production Workstation (accès RustDesk) — **à inventorier** |
| Classification | à établir |
| Statut | **projet orphelin de système opérationnel** : responsable désigné, système inexistant |

## 4. Écarts ouverts

1. **MAYELA** : données structurées et code sont localisés et nommés de façon cohérente depuis le 10/11 ; **les documents/médias ne le sont pas**.
2. **KING OF THE FOREST** : aucune source autoritaire déclarée → l'inventaire distant est un préalable obligatoire.
3. **Aucune intégration système vérifiée** : ni Hermès, ni GAMEFORGE. Aucune fiche connecteur ne peut être remplie honnêtement à ce stade (politique §4 et règles projet).
4. **Registre central** : ce document est un registre **documentaire**, pas le registre central de la politique §7 (qui vise Supabase). Il en préfigure le contenu sans le remplacer.

## 5. Ce que ce registre n'est pas

Il ne prouve aucune fonctionnalité. Il ne remplace ni l'audit distant, ni la validation des architectures cibles, ni la sauvegarde vérifiée. Il fixe le vocabulaire pour que les étapes suivantes (§12) ne mélangent plus projets et systèmes.
