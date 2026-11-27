# ORGANIGRAMME — HORIZON CENTRAL AI (avec l'exécuteur)

Ce document décrit **l'organisation réelle** du système, y compris le **moteur
d'orchestration (exécuteur)** opérationnel depuis le 2026-11-27. Légende des états :

- ✅ **existe** (vérifié dans le code / en ligne)
- 🟢 **opérationnel** (testé réellement en production)
- 🟡 **partiel** (reste à faire, décrit précisément)
- ❌ **à brancher** (mémoire/KR, politiques d'action, connecteurs)

```mermaid
flowchart TB
  U["Utilisateur<br/>App de bureau (en ligne) · Navigateur · Mobile"] --> API

  subgraph HZ["HORIZON CENTRAL AI — serveur en ligne (source de vérité unique)"]
    direction TB
    API["API HORIZON CORE (FastAPI)"]
    subgraph REG["Registre & état (base de référence)"]
      R1["Orchestrateurs / Systèmes"]
      R2["Agents (coordinateur + spécialistes)"]
      R3["Compétences (catalogue)"]
      R4["Projets"]
      R5["Missions · étapes · checkpoints"]
      R6["Exécutions (runs) · journal d'opérations"]
      R7["Outils (mains) · connexions"]
    end
    SEC["Sécurité · permissions · capacités"]
    API --- REG
    API --- SEC
  end

  API --> CORE
  CORE["CORE — Planificateur + Routeur<br/>core.py : build_plan · select_orchestrator<br/>/api/v1/core/plan · /api/v1/core/route"] --> EXEC

  subgraph EXEC["MOTEUR D'ORCHESTRATION — EXÉCUTEUR (générique, 🟢 opérationnel)"]
    direction LR
    E1["1. Décomposer"] --> E2["2. Router vers les agents"] --> E3["3. Exécuter chaque étape"]
    E3 --> E4["4. Suivre (statuts)"] --> E5["5. Consolider"] --> E6["6. Revue qualité"] --> E7["7. Livrer"]
  end

  EXEC --> ADP
  ADP["Adaptateurs UOIM (get_adapter par kind)"]

  ADP --> SYS
  subgraph SYS["Systèmes d'orchestration (aucun codé en dur ; HORIZON décide)"]
    direction TB
    subgraph M360["MARKETING 360 (kind = horizon, moteur natif, sans endpoint)"]
      MO["Marketing Orchestrator (agent coordinateur)"]
      S1["Marketing Strategist"]
      S2["Market Intelligence"]
      S3["Digital Marketing"]
      S4["Marketing & Creative"]
      S5["Performance & Automation"]
      S6["Traditional Marketing"]
      MO --- S1
      MO --- S2
      MO --- S3
      MO --- S4
      MO --- S5
      MO --- S6
    end
    subgraph FAS["FIRST AGENTIC SYSTEM (kind = horizon)"]
      F0["Orchestrateur"]
      F1["Academia Agent"]
      F2["Fullstack Dev"]
      F3["Test Agent"]
      F0 --- F1
      F0 --- F2
      F0 --- F3
    end
  end

  subgraph RES["Ressources transverses"]
    L["Fournisseur LLM (Gemini) — routage & secours"]
    T["Outils / mains — 56 dont 30 prêtes : tool-plan, tool-delegate, tool-skills…"]
    K["Compétences — catalogue (149, vérifié en ligne)"]
    KR["Mémoire / Knowledge (KR) — à brancher"]
    C["Connecteurs : Supabase · Drive · GitHub — non configurés"]
  end

  EXEC -.-> RES
  SYS -.-> RES
  U -.-> RES
```

## Lecture rapide

| Étage | Rôle | État |
|---|---|---|
| **Utilisateur** | app de bureau (mode en ligne), navigateur, mobile | ✅ |
| **API CORE** | registres (systèmes, agents, compétences, projets, missions, runs, outils) + sécurité + journal | ✅ |
| **CORE planificateur / routeur** | transforme une demande en mission + étapes et choisit le système | ✅ |
| **MOTEUR (exécuteur)** | décompose → route vers les **agents** → exécute → suit → consolide | 🟢 **opérationnel** (`orchestrator_engine.py`, vérifié en ligne : mission `1acfa905`, 5 étapes / 5 agents) |
| **Adaptateurs (UOIM)** | branche tout type de système sans code en dur | ✅ |
| **Systèmes** | MARKETING 360 (7 agents) · FIRST AGENTIC SYSTEM (4 agents) | ✅ |
| **Ressources** | LLM, outils, compétences, mémoire/KR, connecteurs | ✅ / ❌ selon la ligne |

## Ce que l'exécuteur utilise (en place et vérifié)
Missions, **étapes** (`assigned_agent_id`), checkpoints, **runs** (statut/sortie/usage/
runtime, `agent_id`), journal ; `effective_skills` (compétences par agent) ; outil
**`tool-delegate`** ; outil **`tool-plan`** ; adaptateurs par `kind` ; fournisseur LLM
(choix automatique du fournisseur configuré).

## Ce qui reste à faire
1. **Boucle d'appel d'outils** dans le moteur : qu'un agent appelle réellement une main
   (recherche web, PDF, image, fichiers) au cours de son étape.
2. **Revue qualité** formalisée après la consolidation (la consolidation distingue déjà
   faits, estimations et hypothèses).
3. **Parallélisation** des étapes indépendantes et reprise ciblée d'une étape en échec.
4. Test PDF **en ligne** après dépôt d'un document réel dans l'espace de travail serveur.
