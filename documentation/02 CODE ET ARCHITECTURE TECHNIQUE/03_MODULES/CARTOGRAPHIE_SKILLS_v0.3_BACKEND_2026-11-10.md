# CARTOGRAPHIE — CATALOGUE DES SKILLS v0.3 → BACKEND RÉEL
**Version 0.1 — 10 novembre 2026 — audit lecture seule (étape 3, politique §12)**
**Objet** : confronter les skills de l'orchestrateur et les compétences HORIZON CORE du catalogue v0.3 au backend réellement présent dans `02_CODE_SOURCE\HORIZON_LOCAL_AI\backend`.
**Règle** : le §8 du catalogue exige un statut explicite. Aucune capacité n'est déclarée « existante » sans preuve dans le code.

## 1. État réel du socle (vérifié dans le code)

| Élément | Source | Contenu constaté |
|---|---|---|
| Entité **orchestrateur** | `schema.py` migration 1 | `orchestrators(id, name, kind, description, endpoint, version, status, health_status, last_checked_at, config_json)` |
| **Affectation** orchestrateur ↔ projet | migration 1 | `orchestrator_projects(orchestrator_id, project_id, role)` — `role` par défaut `'member'` |
| Capacités déclarées | migration 1 | `orchestrator_capabilities(orchestrator_id, capability_id, level, detail)` |
| Projet | migration 1 | `projects(id, name, description, status ∈ active/paused/archived)` |
| Mission | migration 1 | `missions(... orchestrator_id, status, priority)` |
| Journal d'opérations | `repositories/operations.py` | `operation_log(actor, action, target_type, target_id, result, detail, created_at)` ; `detail` tronqué à 1 000 car. ; aucun secret |
| Intégrations | migration 5 | `integrations(... api_key_env, last_checked_at, last_error)` — nom de variable d'env, jamais la valeur |
| Synchronisation | `sync_provider.py`, `sync_engine.py`, `sync_worker.py` | mode `local_cache_only` ; provider distant non configuré |
| Export d'instantané | `tools/export_snapshot.py` | snapshot JSON (preuve : `data/snapshots/…json`, 15,2 Ko) |

**Constat central** : le modèle « **orchestrateur ↔ projet avec rôle** » **existe déjà**. Le principe de responsabilité opérationnelle n'exige donc **pas** une nouvelle abstraction : il exige que `role` porte une valeur `responsable` (aujourd'hui `member` par défaut, sans notion de responsable unique) et que chaque ressource porte l'auteur réel de l'écriture (`operation_log.actor` existe mais n'est pas attaché aux ressources).

## 2. Skills de l'orchestrateur — statut réel

| # | Skill (v0.3) | Ce qui existe | Statut |
|---|---|---|---|
| 4.1 | Classification et gouvernance | rien : aucune table/colonne `classification` | **ABSENT** |
| 4.2 | Nécessité d'une nouvelle catégorie | rien | **ABSENT** |
| 4.3 | Registre provenance et responsabilité | `orchestrator_projects.role`, `missions.orchestrator_id`, `operation_log.actor` | **PARTIEL** — pas de provenance par ressource |
| 4.4 | Coordination, consolidation, rapports | `missions` + `operation_log` + snapshot | **PARTIEL** — pas de rapport de projet produit |
| 4.5 | Partage inter-systèmes | rien (`integrations` ≠ partage de données) | **ABSENT** |
| 4.6 | Cycle de vie des données | seulement `projects.status` | **PARTIEL** — pas de cycle de vie par donnée |
| 4.7 | Durées de conservation | rien | **ABSENT** |
| 4.8 | Transfert de projet | rien | **ABSENT** |
| 4.9 | Conformité et incidents | rien (diagnostics ≠ incidents) | **ABSENT** |
| 4.10 | Synthèse périodique | `metrics.py`, `export_snapshot.py` | **PARTIEL** — métriques techniques |
| 4.11 | Audit et inventaire lecture seule | `export_snapshot.py`, `/admin/diagnostics` | **PARTIEL** — base, pas ressources |
| 4.12 | Qualité des métadonnées / registre | table `documents` à vérifier | **À VÉRIFIER** |
| 4.13 | Projet partagé et catalyseur | `role='member'` seulement | **ABSENT** |
| 4.14 | Contrôle des migrations | `schema.py` (migrations numérotées, idempotentes, `schema_migrations`) | **PARTIEL** — pas de lots ni retour arrière |
| 4.15 | Vérification des sauvegardes | snapshots JSON exportés | **PARTIEL, non vérifié** — aucun test de restauration |
| 4.16 | Permissions et secrets | `auth.py`, `integrations.api_key_env`, `secret_present` | **PARTIEL** — pas de rôles ni matrice |
| 4.17 | Clôture et transfert complet | rien | **ABSENT** |
| 4.18 | Adaptation Supabase / GitHub / Drive | `sync_provider` (local_cache_only) | **PARTIEL** — aucun connecteur réel |
| 4.19 | Journalisation et traçabilité | `operation_log(actor, action, target_type, target_id, result, detail)` | **EXISTANT — VÉRIFIÉ**, avec limites (ni `project_id`, ni corrélation d'écriture) |
| 4.20 | Notifications et validations | rien (aucun canal Telegram) | **ABSENT** |

## 3. Compétences HORIZON CORE — statut réel

| # | Compétence (v0.3) | Ce qui existe | Statut |
|---|---|---|---|
| 5.1 | Supervision transversale | `orchestrators.health_status` + cockpit | **PARTIEL** — état déclaré, pas de supervision active |
| 5.2 | Gouvernance des classifications | rien | **ABSENT** |
| 5.3 | Autorisation des collaborations | rien | **ABSENT** |
| 5.4 | Veille réglementaire | rien | **ABSENT** |
| 5.5 | Journal Telegram | rien | **ABSENT** |
| 5.6 | Arbitrage et incidents | rien | **ABSENT** |
| 5.7 | Registre central / visibilité | `orchestrators`, `projects`, `missions` | **PARTIEL** — ni ressources ni liens inter-plateformes |
| 5.8 | Supervision des projets partagés | rien | **ABSENT** |
| 5.9 | Gouvernance des migrations | rien | **ABSENT** |
| 5.10 | Gouvernance des accès et secrets | `integrations` (présence, pas valeur) | **PARTIEL** |

**Bilan** : 30 capacités examinées — **1 vérifiée** (4.19 journalisation), **12 partielles**, **16 absentes**, **1 à vérifier** (4.12).
Aucun skill n'existe au sens du catalogue (contrat entrée/sortie, responsable, tests). Ce qui existe est de l'**infrastructure de registre**, pas de la **capacité de gouvernance**.

## 4. Ce que « l'Orchestrateur est responsable » change concrètement

1. `orchestrator_projects.role` doit distinguer **`responsable`** et **`contributeur`**, avec **un seul responsable actif** par projet. Aujourd'hui : `member` uniquement.
2. `operation_log.actor` doit recevoir l'**identifiant de l'Orchestrateur** (ou de l'humain), jamais un libellé vague type `system`.
3. Une **ressource** (document, mission, livraison) doit pouvoir désigner son auteur et son responsable.
4. Le lien projet ↔ orchestrateur est une **affectation**, pas une appartenance : un orchestrateur peut être retiré d'un projet sans que le projet disparaisse ; un projet peut changer d'orchestrateur responsable sans perdre son historique (§6).
5. **Un projet n'est pas la raison d'être d'un système** : MAYELA CRM n'est pas la condition sine qua non du système Hermès. Le système existe indépendamment ; MAYELA est **une affectation parmi d'autres**. Le registre doit donc accepter « 0 projet affecté » sans invalider le système — et « 0 orchestrateur affecté » sans supprimer le projet.
6. **Notion de groupe** (catalogue §2.1) : HORIZON CENTRAL AI est comparable à un groupe d'entreprises. Chaque système est une entité opérationnelle ; **son Orchestrateur en est le directeur général**, sans diriger le groupe. L'Orchestrateur produit les synthèses et rapports de ses projets ; HORIZON CORE supervise et arbitre, il ne gère pas le quotidien.

## 5. Ordre de travail proposé (backend — après validation, avec annonce préalable)

1. **Sémantique d'abord, sans migration** : figer les valeurs de `role` et la règle « un seul responsable actif ».
2. **Attribution** : propager l'auteur sur les écritures (impacte les routes d'écriture → annonce obligatoire).
3. **Classification** : référentiel commun (Public / Interne / Confidentiel / Hautement sensible) + métadonnée par ressource ; la classification **finale relève de l'Orchestrateur**, les agents fournissent provenance et alertes (§2.5 du catalogue).
4. **Cycle de vie** : états par ressource (actif / inactif / obsolète / archivé / candidat à suppression).
5. **Restauration** : test réel de restauration d'un snapshot avant de qualifier une sauvegarde de fiable.
6. Le reste (partage inter-systèmes, catalyseur, veille, Telegram) **uniquement sur besoin démontré** (§14 de la politique).

**Aucune de ces étapes n'est engagée. Aucun fichier backend n'a été modifié.**
