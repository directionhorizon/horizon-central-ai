# HORIZON LOCAL AI — CARTOGRAPHIE FONCTIONNELLE ET ARCHITECTURALE

Date : 2026-11-09
Périmètre analysé : `C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI`
Nature : **analyse seule**. Aucun fichier du projet n'a été modifié, créé ni supprimé (seul ce rapport est écrit).

## 0. Méthode et sources de preuve

### 0.1 Code lu

| Fichier | Constat |
|---|---|
| `backend/app.py` (5 987 o, 137 lignes) | 7 routes, 2 tables SQLite, CORS, aucune IA, aucune authentification |
| `src/App.tsx` (123 lignes) | routeur, 6 pages, sélecteur de session, indicateur de santé |
| `src/shared/ChatSessionContext.tsx` (374 lignes) | persistance serveur, états, erreurs, synchronisation URL |
| `src/api/*.ts`, `src/config/env.ts`, `src/components/BackendHealth.tsx` | couche réseau unique |
| `src/pages/main-workbench/MainWorkbench.tsx` | raccordé au backend |
| `src/pages/ai-control-center/AIControlCenter.tsx` | raccordé au backend |
| `src/pages/model-manager/ModelManager.tsx` (15 410 o) | statique + formulaire en état local |
| `src/pages/knowledge-memory-hub/KnowledgeMemoryHub.tsx` | statique |
| `src/pages/agents-tools-catalog/AgentsToolsCatalog.tsx` | statique |
| `src/pages/system-monitor/SystemMonitor.tsx` | statique |
| `docs/contracts/CORE_API_CONTRACT_v0.1.md` | contrat cible : 13 routes prévues, 7 implémentées |

### 0.2 Rapports déjà disponibles (non refaits)

`RAPPORT_AUDIT_COMPLET_2026-11-08.md` (25 785 o) · `RAPPORT_AUDIT_RACCORDEMENT_FRONTEND_BACKEND_2026-11-09.md` (19 949 o) · `RAPPORT_VALIDATION_TECHNIQUE_2026-11-09.md` (15 314 o) · `RAPPORT_RACCORDEMENT_FRONTEND_BACKEND_2026-11-09.md` (10 372 o) · `COMPARAISON_6_INTERFACES.csv` · `COMPARAISON_VERSIONS.csv` · `DOUBLONS_EXACTS_CORRIGE.csv` · `INVENTAIRE_APPLICATION_47_FICHIERS.csv`

### 0.3 Recherches exécutées pour cette cartographie

| Recherche | Résultat |
|---|---|
| `fetch(`, `axios`, `XMLHttpRequest`, `WebSocket`, `EventSource` dans `src/` hors `api/` | **0 occurrence** — tout passe par `src/api/http.ts` |
| `orchestrat` dans le code | 10 occurrences, **toutes du texte d'interface statique** |
| `Hermes` dans le code | **0 occurrence** |
| `budget`, `security` dans le code | **0 occurrence** |
| `permission` | 5 occurrences, texte d'interface uniquement |
| Composants `SideNav` / `SystemHeader` / `LLMSelector` / `ContextPanel` | **0 import** — 13 fichiers orphelins (code mort) |

### 0.4 Distinction faits / hypothèses

Toute ligne marquée **[vérifié]** est constatée dans le code ou par un test réel déjà documenté. Toute ligne marquée **[hypothèse]** est une déduction de conception, non démontrée par l'exécution.

---

## 1. MATRICE DES SIX FONCTIONS

> « État réel » ne considère comme existant que ce qui est prouvé par le code ou par un test. Une page visible sans appel réseau n'est **pas** une fonctionnalité.

### F1 — HORIZON CORE

| Colonne | Contenu |
|---|---|
| **État réel** | **ABSENT** hors persistance de conversation. Aucun moteur de compréhension, de décomposition en missions, de décision, de répartition ni d'arbitrage. **[vérifié]** |
| **Preuves** | `backend/app.py:115-125` : `add_message()` insère le message et renvoie `execution.status = "accepted_no_model"` + `warnings`. Aucun appel LLM (`HORIZON_LLM_BASE_URL` lu en `:77` seulement pour un statut de capacité). Aucune table mission/plan/tâche. |
| **Écarts** | Interprétation de l'intention, génération de missions, sélection d'orchestrateur, politique de routage, arbitrage, vision globale : tous absents. Le contrat v0.1 prévoit une réponse du cœur avec `status = completed` et `citations` — non implémentée. |
| **Composants réutilisables** | Tables `sessions`/`messages`, `ChatSessionContext`, couche `src/api/*`, `BackendHealth`, capacité `core.sessions` (available). |
| **Actions nécessaires** | Définir le contrat « mission », ajouter un service de planification, un adaptateur LLM via Model Manager, une politique de routage côté backend. |
| **Priorité** | **P0** |

### F2 — Orchestration Manager

| Colonne | Contenu |
|---|---|
| **État réel** | **ABSENT** en tant que registre. Le concept n'existe que comme texte d'interface. Aucun enregistrement, identifiant unique, test de compatibilité ni supervision. **[vérifié]** |
| **Preuves** | `AgentsToolsCatalog.tsx:12-50` : `environments` et `integrations` en constantes locales, dont `name: 'External orchestrators'` (`:46`). Ligne `:73` : « Registry prototype · No orchestration or … ». Aucune entité orchestrateur en base, aucune route `/orchestrators`. `Hermes` : 0 occurrence. |
| **Écarts** | Entité orchestrateur, fiche de capacités, découverte, test de connexion, historique de performances, remplacement à chaud. Le lien « un orchestrateur ↔ plusieurs projets » n'existe nulle part. |
| **Composants réutilisables** | Page `AgentsToolsCatalog` (liste + filtres + panneaux), mécanisme de statut de `capabilities`, modules `src/api/*` comme patron. |
| **Actions nécessaires** | Schéma « orchestrateur » + « affectation projet », routes de registre, raccordement de la page. Prérequis de F4 et F5. |
| **Priorité** | **P0** |

### F3 — Orchestration Builder

| Colonne | Contenu |
|---|---|
| **État réel** | **ABSENT** totalement. Aucune génération de fichiers ou de code, aucun build, aucun test automatisé. **[vérifié]** |
| **Preuves** | Aucune occurrence de génération dans `backend/app.py`. Aucun service de fichiers. Aucun endpoint de build. `06_TESTS\Plan_Tests.md` = 163 o (squelette). `package.json` : ni Vitest ni Playwright. |
| **Écarts** | Moteur de génération, sandbox d'exécution, gestion de versions, validation avant enregistrement au registre. |
| **Composants réutilisables** | Aucun composant dédié. Indirectement : `capabilities`, modules API, contrat. |
| **Actions nécessaires** | Concevoir **après** F2 et F6 : le Builder doit soumettre ses productions à validation. |
| **Priorité** | **P2** |

### F4 — Execution & Continuity Manager

| Colonne | Contenu |
|---|---|
| **État réel** | **TRÈS PARTIEL** : persistance de conversation seulement. Aucune notion de mission, d'étape, de point de contrôle, de reprise ni de verrou. **[vérifié]** |
| **Preuves** | `backend/app.py:36-46` : tables `sessions` et `messages` uniquement. Aucune table `missions`, `tasks`, `checkpoints`, `locks`. Aucune file ni worker : `add_message` est synchrone (réponse 202). `GET /sessions/{id}` (`:105-112`) permet le rechargement — seule continuité réellement opérationnelle. |
| **Écarts** | Modèle de mission, états d'exécution, idempotence, verrous, reprise après interruption, réattribution. La continuité repose aujourd'hui sur la seule mémoire conversationnelle, ce que la vision interdit. |
| **Composants réutilisables** | `connect()` / `init_db()` / tables SQLite, `ChatSessionContext`, `http.ts` (timeout + retry GET), module `sessions.ts`. |
| **Actions nécessaires** | Modèle mission/étape, exécution asynchrone avec suivi persistant, verrouillage, points de contrôle. |
| **Priorité** | **P0** |

### F5 — Memory & Knowledge Manager

| Colonne | Contenu |
|---|---|
| **État réel** | **INTERFACE STATIQUE** uniquement. Aucune mémoire persistée hors messages de session. Aucun document, aucune recherche, aucun connecteur. **[vérifié]** |
| **Preuves** | `KnowledgeMemoryHub.tsx:13-78` : `DOCUMENTS` et `GRAPH_POINTS` en constantes. État local `activeTab`, `query`, `isSyncEnabled`, `isIndexing` (`:80-83`) — l'indexation ne fait qu'un délai local. `capabilities` : `memory.google_drive = not_configured` (`app.py:83`). Aucune route `/memory/*`. |
| **Écarts** | Stockage documentaire, index, recherche, provenance, séparation mémoire centrale / spécialisée, connecteur Drive. `GET /memory/status` et `POST /memory/search` prévus au contrat : absents. |
| **Composants réutilisables** | Page `KnowledgeMemoryHub` (onglets, recherche, liste, graphe), contrat v0.1, tables SQLite comme socle. |
| **Actions nécessaires** | Schéma documentaire, routes mémoire, raccordement de la page. Dépend de F2 pour la mémoire spécialisée par orchestrateur. |
| **Priorité** | **P1** |

### F6 — Validation & Deployment Manager

| Colonne | Contenu |
|---|---|
| **État réel** | **ABSENT** en tant que fonction applicative. La pratique existe hors application (ZIP, rapports, versions). **[vérifié]** |
| **Preuves** | Aucune route de validation, de version ni de déploiement. Aucune table de journal. `capabilities` n'expose aucun statut de déploiement. Sauvegardes manuelles : 2 ZIP dans `03 MÉMOIRE LOCALE\07_SAUVEGARDES` + 4 archives de versions. Aucun test automatisé. |
| **Écarts** | Harnais de tests, registre de versions applicatif, journal d'opérations, workflow d'autorisation, rollback automatisé. |
| **Composants réutilisables** | Archives et rapports existants (traçabilité manuelle), `capabilities`, arborescence `07_AUDIT_CLASSEMENT`. |
| **Actions nécessaires** | Modèle validation/journal, routes, workflow d'autorisation. Dépend de F2, F3 et du service Security. |
| **Priorité** | **P1** |

**Synthèse :** sur 6 fonctions, **0 est réellement opérationnelle** au sens de la vision · **1 très partielle** (F4, via la persistance de session) · **1 interface statique** (F5) · **4 absentes** (F1, F2, F3, F6).

---

## 2. CARTOGRAPHIE DES PAGES ET MODULES ACTUELS

### 2.1 Pages (6) et état de raccordement

| Page | Route | Fichier | Octets | Raccordée au backend ? | Preuve |
|---|---|---|---|---|---|
| Main Workbench | `/workbench`, `/workbench/:sessionId` | `MainWorkbench.tsx` | 9 545 | **OUI** | `useChatSession()` → `sendMessage` → `POST /sessions/{id}/messages` |
| AI Control Center | `/control`, `/control/:sessionId` | `AIControlCenter.tsx` | 8 116 | **OUI** | `sendMessage`, `createSession`, `resetSession` |
| Model Manager | `/models` | `ModelManager.tsx` | 15 410 | **NON** | 3 fournisseurs + 8 points de graphique + 3 stats en constantes ; formulaire d'endpoint en `useState` seul |
| Knowledge & Memory Hub | `/memory` | `KnowledgeMemoryHub.tsx` | 13 511 | **NON** | `DOCUMENTS`, `GRAPH_POINTS` constants ; `isIndexing` simulé localement |
| Agents & Tools Catalog | `/catalog` | `AgentsToolsCatalog.tsx` | 7 350 | **NON** | `environments`, `integrations` constants ; filtres locaux |
| System Monitor | `/monitor` | `SystemMonitor.tsx` | 8 978 | **NON** | `initialNodes` constant ; bouton `refresh` local |

### 2.2 Modules applicatifs (couche technique)

| Module | Fichier | Rôle | État |
|---|---|---|---|
| Configuration | `src/config/env.ts` | URL backend, délai, table de routes | Opérationnel |
| Client HTTP | `src/api/http.ts` | fetch, timeout, erreurs, retry GET | Opérationnel |
| Erreurs | `src/api/errors.ts` | `ApiError` + messages sûrs | Opérationnel |
| Types | `src/api/types.ts` | contrats backend | Opérationnel |
| Sessions | `src/api/sessions.ts` | 5 opérations sessions | Opérationnel |
| Santé/capacités | `src/api/capabilities.ts` | health + capabilities | Opérationnel |
| Contexte session | `src/shared/ChatSessionContext.tsx` | état, persistance, URL | Opérationnel |
| Indicateur santé | `src/components/BackendHealth.tsx` | pastille + détail | Opérationnel |
| Routeur / coquille | `src/App.tsx` | 6 routes + variantes `:sessionId`, sélecteur de session | Opérationnel |

### 2.3 Backend réel (7 routes, 2 tables)

| Méthode | Route | Comportement vérifié |
|---|---|---|
| GET | `/api/v1/health` | 200, `service=horizon-core`, `version=0.1.0` |
| GET | `/api/v1/capabilities` | 200, 5 capacités (`core.sessions`, `llm.default`, `memory.google_drive`, `repository.github`, `system.metrics`) |
| POST | `/api/v1/sessions` | 201 ; corps obligatoire (422 sans corps) |
| GET | `/api/v1/sessions` | 200, `{items}`, `limit` 1–100 (défaut 30) |
| GET | `/api/v1/sessions/{id}` | 200 avec `messages` ; 404 si inconnue |
| POST | `/api/v1/sessions/{id}/messages` | 202, `execution.status = accepted_no_model`, `warnings` ; 422 si contenu vide |
| POST | `/api/v1/sessions/{id}/reset` | 200, supprime les messages ; 404 si inconnue |

Tables : `sessions(id, title, created_at, updated_at)` · `messages(id, session_id → sessions ON DELETE CASCADE, role IN user/assistant/system, content, created_at)`. Aucune table projet, mission, tâche, orchestrateur, agent, document, permission, budget, journal.

### 2.4 Composants orphelins (code mort, 13 fichiers)

`SideNav.tsx` (4 copies, 2 461–2 927 o) · `SystemHeader.tsx` (4 copies, 2 535 o) · `LLMSelector.tsx` (4 copies, 3 936 o) · `ContextPanel.tsx` (1 copie, 4 255 o). **Aucun import** dans `App.tsx` ni dans les pages : ils ne sont jamais rendus.

---

## 3. RAPPROCHEMENT MODULES EXISTANTS ↔ SIX FONCTIONS

| Module / page existant | F1 CORE | F2 Orchestration | F3 Builder | F4 Continuité | F5 Mémoire | F6 Validation |
|---|---|---|---|---|---|---|
| `backend/app.py` (sessions/messages) | support de trace | — | — | **partiel** | trace de conversation | — |
| `ChatSessionContext` | support d'échange | — | — | **partiel** | — | — |
| `src/api/*` | socle d'appels | socle d'appels | socle d'appels | socle d'appels | socle d'appels | socle d'appels |
| `BackendHealth` | — | **indicateur partiel** (santé du cœur) | — | — | — | — |
| `capabilities` (backend) | — | **socle de statut** réutilisable | socle de statut | — | déclare `memory.google_drive` | — |
| Main Workbench | **interface d'entrée** | — | — | trace | — | — |
| AI Control Center | **interface d'entrée** + panneau | — | — | trace | — | — |
| Agents & Tools Catalog | — | **interface cible** (registre) | interface cible | — | — | — |
| Model Manager | — | — | — | — | — | — |
| Knowledge & Memory Hub | — | — | — | — | **interface cible** | — |
| System Monitor | — | — | — | — | — | **interface cible** (supervision) |
| Contrat API v0.1 | **contrat cible** | partiel | — | — | **contrat cible** | — |

**Lecture :** aucun module existant ne couvre F1, F2, F3 ou F6 au-delà d'une interface ou d'un socle. F4 dispose d'un socle réel (sessions/messages) mais sans modèle de mission. F5 dispose d'une interface complète mais sans persistance.

---

## 4. SERVICES TRANSVERSAUX — PRÉSENTS OU ABSENTS

| Service transversal attendu | Présent ? | Preuve / absence | Constat |
|---|---|---|---|
| **Security & Permissions Manager** | **ABSENT** | `backend/app.py` : aucune authentification, aucun rôle, aucune permission, aucun journal. `allow_credentials=False` seulement. `permission` n'apparaît que dans du texte d'interface. `Regles_Securite.md` existe (2 281 o) mais n'est pas outillé. | Seul un référentiel documentaire existe |
| **Resource Discovery & Inventory Manager** | **ABSENT** | Aucune découverte de machine, logiciel, modèle, orchestrateur, agent ou service. Aucune route. | — |
| **Project Infrastructure Manager** | **ABSENT** | Aucune entité « projet » en base. Le dossier `03 MÉMOIRE LOCALE\04_PROJETS\Projets_Locaux.md` fait 74 o. | — |
| **Remote Production Manager** | **ABSENT** | Aucune notion de machine distante dans le code. `capabilities` ne déclare aucune capacité distante. | — |
| **Synchronization Manager** | **ABSENT** | Aucun code de synchronisation. `04 MÉMOIRE EN LIGNE\04_SYNCHRONISATION\Synchronisation.md` = 132 o. `memory.google_drive` et `repository.github` = `not_configured` (`app.py:83-84`). | Documentaire seulement |
| **Budget Manager** | **ABSENT** | `budget` : 0 occurrence dans le code. Aucun compteur de tokens ni de coût. | — |
| **Model Manager** | **INTERFACE SEULE** | `ModelManager.tsx` : 3 fournisseurs en constantes (`:19-46`), statut figé `Not verified`, latence `42 ms` / `318 ms` / `—` (valeurs de démonstration). Aucune route `/models`, aucun `PUT /settings/model-selection`. | La capacité `llm.default` renvoie `not_configured` |
| **Monitoring & Notification** | **INTERFACE SEULE** | `SystemMonitor.tsx` : `initialNodes` constants (`:4-32`), `refresh` ne fait que réinitialiser l'état local. Aucune alerte, aucune notification, aucune route `/system/metrics`. Capacité `system.metrics` = `unverified`. | — |

**Conclusion :** sur 8 services transversaux, **0 est opérationnel**. 2 disposent d'une interface (Model Manager, Monitoring), 6 sont totalement absents. Le seul mécanisme transversal réellement réutilisable est le registre de statuts de `capabilities` (`available` / `not_configured` / `unverified` / `degraded` / `unavailable`).

---

## 5. DÉPENDANCES ENTRE COMPOSANTS

### 5.1 Dépendances techniques réelles (vérifiées)

```
main.tsx → App.tsx
App.tsx → BrowserRouter → ChatSessionProvider → AppShell
AppShell → 6 pages + BackendHealth + sélecteur de session
ChatSessionContext → api/sessions.ts → api/http.ts → config/env.ts
BackendHealth → api/capabilities.ts → api/http.ts
api/* → api/errors.ts, api/types.ts
```

**Propriétés vérifiées :** aucune dépendance circulaire · un seul point de sortie réseau · aucune page (hors Workbench et Control Center) n'importe la couche API.

### 5.2 Dépendances fonctionnelles cibles (hypothèse de conception)

| Dépendance | Sens | Justification |
|---|---|---|
| F1 CORE → F2 Orchestration Manager | F1 dépend de F2 | Le cœur ne peut distribuer que ce qui est enregistré |
| F1 CORE → Model Manager | F1 dépend du service modèle | Sans modèle, pas de compréhension ni de décision |
| F4 Continuité → F2 | F4 dépend de F2 | La réattribution exige un registre d'orchestrateurs compatibles |
| F4 Continuité → F5 | bidirectionnelle | La reprise exige un historique ; l'historique exige un suivi d'exécution |
| F3 Builder → F6 Validation | F3 dépend de F6 | Aucune production ne doit entrer au registre sans validation |
| F6 Validation → Security | F6 dépend du service sécurité | Toute opération sensible exige une autorisation |
| F5 Mémoire → F2 | F5 dépend de F2 | La mémoire spécialisée appartient aux orchestrateurs |

**Conséquence architecturale :** F2 (registre) et le service Security sont les deux **points de blocage**. Tant qu'ils n'existent pas, F1, F3, F4, F5 et F6 ne peuvent pas être achevés.

---

## 6. DOUBLONS FONCTIONNELS

### 6.1 Doublons certains (vérifiés, identiques au SHA256)

| Doublon | Constat | Impact |
|---|---|---|
| `SideNav.tsx` ×4 | 4 copies dans 4 dossiers de page, aucun import | Code mort dupliqué, maintenance inutile |
| `SystemHeader.tsx` ×4 | 4 copies, aucun import | idem |
| `LLMSelector.tsx` ×4 | 4 copies, aucun import | idem |
| `ContextPanel.tsx` ×1 | jamais importé | code mort |

### 6.2 Doublons fonctionnels de conception (non des fichiers)

| Doublon | Détail |
|---|---|
| **Deux points d'entrée conversation** | Main Workbench et AI Control Center font la même chose (envoi + historique). Le contrat v0.1 assume ce choix (« deux vues consomment le même session_id ») — à conserver, mais il faut éviter d'en ajouter un troisième. |
| **Deux sélecteurs de session** | Le `<select>` de la barre de navigation (`App.tsx`) et la navigation par URL font la même chose. Redondance assumée, mais à documenter pour éviter une troisième voie. |
| **Deux blocs de mémoire documentaire** | `03 MÉMOIRE LOCALE` (15 fichiers `.md`) et `04 MÉMOIRE EN LIGNE` (8 fichiers) doublonnent partiellement la notion de « mémoire » sans code les reliant. |
| **Trois documents d'architecture** | `02 CODE ET ARCHITECTURE TECHNIQUE\Architecture_Generale.md` (495 o), `01_ARCHITECTURE\Architecture_Generale.md` (585 o), `06 ARCHIVES\DOCUMENTS_HISTORIQUES\Architecture_Generale_avant_fusion.md` (336 o) — versions concurrentes non tranchées. |

### 6.2 bis — Doublons documentaires déjà corrigés

`DOUBLONS_EXACTS_CORRIGE.csv` (1 698 o) documente 5 groupes exacts et 4 paires de même nom au contenu différent, traités lors de la phase de consolidation. Aucun n'a été supprimé.

---

## 7. RISQUES ARCHITECTURAUX

| # | Risque | Gravité | Preuve | Conséquence si non traité |
|---|---|---|---|---|
| R1 | **Confusion interface ↔ fonctionnalité** : 4 pages sur 6 affichent des données de démonstration présentées comme réelles (latences, CPU/GPU, documents, nœuds) | **Élevée** | `ModelManager.tsx:19-46`, `SystemMonitor.tsx:4-32`, `KnowledgeMemoryHub.tsx:13-78`, `AgentsToolsCatalog.tsx:12-50` | Décisions prises sur des chiffres fictifs ; écart de confiance avec la vision |
| R2 | **Absence totale de moteur d'orchestration** alors que c'est la raison d'être du produit | **Élevée** | 0 occurrence de `Hermes`, aucune entité orchestrateur | Le produit reste un chat local + 4 maquettes |
| R3 | **Continuité non persistante au-delà du message** | **Élevée** | Tables limitées à `sessions`/`messages` | Perte de progression sur mission longue ; réattribution impossible |
| R4 | **Aucune sécurité applicative** (ni auth, ni permission, ni journal) | **Élevée** | `app.py` : aucune couche auth ; `allow_credentials=False` seul | Toute opération sensible serait non traçable et non contrôlée |
| R5 | **Monolithe non modularisé** : tout le backend tient dans un seul fichier de 137 lignes | Moyenne | `backend/app.py` unique | La cible « monolithe modulaire » n'est pas encore structurée ; l'évolution en microservices serait coûteuse |
| R6 | **Divergence contrat ↔ implémentation** sur le message | Moyenne | Contrat : `status = completed` + `citations` ; code : `accepted_no_model`, pas de `citations` | Les clients écrits sur le contrat échoueront |
| R7 | **Code mort dupliqué** (13 fichiers, 4 composants × 4 copies) | Faible | 0 import détecté | Dérive de maintenance ; faux sentiment de modularité |
| R8 | **Absence de tests automatisés** | Moyenne | Aucun Vitest/Playwright ; `Plan_Tests.md` = 163 o | Toute régression future sera détectée manuellement |
| R9 | **Pas de séparation mémoire centrale / mémoire spécialisée** dans le code | Moyenne | Une seule table `messages` ; aucune entité document | F5 sera reconstruite de travers si non spécifiée d'abord |
| R10 | **Dépendance à des sauvegardes ZIP manuelles**, pas de CI | Faible | Sauvegardes manuelles | Perte de savoir en cas d'interruption longue |
| R11 | **Documents d'architecture contradictoires** (3 versions) | Faible | Voir §6.2 | Décisions contradictoires lors des prochaines phases |

---

## 8. ÉLÉMENTS À CONSERVER IMPÉRATIVEMENT

| Élément | Raison |
|---|---|
| **Persistance SQLite des sessions/messages** (`backend/app.py:36-46`) | Seule persistance réelle, testée de bout en bout |
| **Couche HTTP unique** `src/api/http.ts` + `config/env.ts` | Point de sortie unique, timeout, erreurs normalisées |
| **`ChatSessionContext`** | Source de vérité côté client, synchronisée avec l'URL |
| **Routeur + URLs partageables** (`/workbench/:id`, `/control/:id`) | Exigence validée, déjà fonctionnelle |
| **Registre de statuts `capabilities`** (5 états) | Mécanisme transversal réutilisable pour tous les services |
| **Les 6 pages et leur design** | Interfaces validées, à ne pas reconstruire |
| **Les 2 points d'entrée conversation partagés** | Décision du contrat v0.1 |
| **`accepted_no_model` explicite** | Garantit l'absence de fausse réponse IA |
| **Archives, sauvegardes ZIP, rapports** | Traçabilité et rollback manuel |
| **`.clinerules` et règles de conduite** | Cadre de travail du projet |

---

## 9. ÉLÉMENTS À AMÉLIORER (existant, non bloquant)

| Élément | Amélioration attendue |
|---|---|
| `backend/app.py` monolithique | Découper en modules (sessions, capabilities, health) **sans changer les contrats** |
| `GET /sessions` sans pagination | Ajouter des métadonnées de pagination (route existante à faire évoluer) |
| Pas de suppression de session | Ajouter `DELETE /sessions/{id}` (nouvelle route, décision requise) |
| Pièces jointes non transmises | Étendre le schéma `messages` ou ajouter une table `attachments` |
| 13 composants orphelins | Décider : supprimer (avec sauvegarde) ou réintégrer |
| Absence de tests | Ajouter Vitest + tests d'intégration API |
| Données de démonstration non signalées | Marquer visuellement « DEMO » ou désactiver par configuration |
| Divergence contrat v0.1 | Mettre à jour le contrat ou l'implémentation — décision requise |

---

## 10. ÉLÉMENTS À DÉVELOPPER (absents)

| # | Élément | Fonction liée | Prérequis |
|---|---|---|---|
| D1 | Entité **Orchestrateur** + fiche de capacités + registre | F2 | — |
| D2 | Entité **Projet** + affectation orchestrateur ↔ projets | F2 | D1 |
| D3 | Entité **Mission** + étapes + points de contrôle + verrous | F4 | D1, D2 |
| D4 | **Service de planification / routage** (HORIZON CORE) | F1 | D1, D3, Model Manager |
| D5 | **Adaptateur LLM** commun (OpenAI-compatible) + fallback | Model Manager | Décision fournisseur |
| D6 | **Mémoire documentaire** + recherche + provenance | F5 | D1, D2 |
| D7 | **Security & Permissions** (identités, permissions, journal) | transversal | Décision modèle de sécurité |
| D8 | **Validation & journal d'opérations** + rollback | F6 | D7 |
| D9 | **Monitoring réel** (`/system/metrics` avec source identifiée) | transversal | Sonde Windows |
| D10 | **Budget / compteurs de coûts** | transversal | D5 |
| D11 | **Synchronisation** Drive / GitHub | transversal | Décision stockage |
| D12 | **Orchestration Builder** (génération + build + tests) | F3 | D1, D8 |

---

## 11. FEUILLE DE ROUTE ORDONNÉE

> Ordonnée par dépendances réelles. Chaque étape est un prérequis de la suivante.

| Étape | Contenu | Fonction | Critère de validation |
|---|---|---|---|
| **E0** | Trancher les décisions du §12 | — | Décisions signées |
| **E1** | Modèle de données orchestrateur + projet + mission (schéma, sans code applicatif) | F2 / F4 | Schéma validé et documenté |
| **E2** | Routes de registre (`/orchestrators`, `/projects`) | F2 | Tests API documentés |
| **E3** | Raccordement de la page Agents & Tools Catalog au registre réel | F2 | Données réelles affichées, démonstration retirée |
| **E4** | Adaptateur LLM commun + `/models` + `/settings/model-selection` | Model Manager | Test réel de connexion documenté |
| **E5** | Service de planification HORIZON CORE (demande → mission) | F1 | Une demande produit une mission persistée |
| **E6** | Exécution asynchrone + points de contrôle + verrous | F4 | Reprise après interruption démontrée |
| **E7** | Mémoire documentaire + `/memory/status` + `/memory/search` | F5 | Recherche réelle sur documents réels |
| **E8** | Security & Permissions + journal d'opérations | transversal | Opération sensible bloquée sans autorisation |
| **E9** | Validation & déploiement (tests, versions, rollback) | F6 | Rollback exécuté et documenté |
| **E10** | Monitoring réel + Budget | transversal | Métriques réelles horodatées, source identifiée |
| **E11** | Orchestration Builder | F3 | Un orchestrateur généré passe la validation de E9 |

**Chemin critique :** E0 → E1 → E2 → E4 → E5 → E6. Tout le reste en dépend.

---

## 12. DÉCISIONS À VALIDER AVANT TOUTE NOUVELLE PHASE

| # | Décision | Options | Impact |
|---|---|---|---|
| **DÉC-1** | **Données de démonstration** : les conserver en les marquant « DEMO », ou les retirer | 2 options | Crédibilité de toutes les pages |
| **DÉC-2** | **Emplacement des nouvelles entités** : même base SQLite ou base séparée | 2 options | Modularité (R5) |
| **DÉC-3** | **Divergence contrat v0.1** : aligner le contrat sur le code (`accepted_no_model`) ou le code sur le contrat (`completed`) | 2 options | API publique |
| **DÉC-4** | **Premier fournisseur LLM** (Ollama local / OpenAI-compatible / autre) | 3+ options | Model Manager et F1 |
| **DÉC-5** | **Modèle de sécurité** : authentification locale simple ou multi-utilisateur | 2 options | F6 et toutes les opérations sensibles |
| **DÉC-6** | **13 composants orphelins** : suppression après sauvegarde, ou réintégration | 2 options | Dette technique |
| **DÉC-7** | **Documents d'architecture contradictoires** : laquelle des 3 versions fait foi | 3 options | Cohérence documentaire |
| **DÉC-8** | **Ordre F2 → F4** (registre d'abord) ou **F4 → F2** | 2 options | Le §5.2 recommande F2 d'abord |
| **DÉC-9** | **Périmètre « projet »** : entité de première classe en base, ou simple étiquette de session | 2 options | F2, F4, F5 |

---

## 13. FAITS VÉRIFIÉS vs HYPOTHÈSES

### 13.1 Faits vérifiés (constatés dans le code ou par test réel)

1. 7 routes backend, 2 tables SQLite, aucune IA, aucune authentification. **[vérifié]**
2. 2 pages sur 6 raccordées au backend ; 4 statiques. **[vérifié]**
3. 0 appel réseau hors `src/api/http.ts`. **[vérifié]**
4. `Hermes` et `budget` : 0 occurrence dans le code. **[vérifié]**
5. 13 composants orphelins, 0 import. **[vérifié]**
6. Aucune table mission, projet, orchestrateur, document, permission, journal. **[vérifié]**
7. CORS opérationnel pour `http://localhost:5173`. **[vérifié — test réel]**
8. Persistance session + messages validée de bout en bout, y compris en SQLite. **[vérifié — test réel]**
9. `npm run build` réussit. **[vérifié — test réel]**
10. Aucun test automatisé (Vitest / Playwright) présent. **[vérifié]**

### 13.2 Hypothèses de conception (non démontrées)

1. Le découpage en 6 fonctions peut rester dans un monolithe modulaire FastAPI. **[hypothèse]** — aucune structure de modules n'existe encore pour le prouver.
2. Un adaptateur OpenAI-compatible suffira pour tous les fournisseurs visés. **[hypothèse]** — non testé.
3. F2 peut être livré avant F4 sans bloquer la continuité. **[hypothèse]** — dépend de DÉC-8.
4. Les interfaces des 4 pages statiques peuvent être conservées telles quelles en les raccordant. **[hypothèse]** — dépend de la forme réelle des contrats à créer.
5. Le volume de données restera compatible avec SQLite. **[hypothèse]** — aucun test de charge effectué.

---

## 14. CONCLUSION

Le projet HORIZON LOCAL AI possède aujourd'hui un **socle applicatif sain mais minimal** : une API FastAPI de 7 routes avec persistance SQLite réellement testée, un frontend React raccordé pour 2 pages sur 6, une couche réseau centralisée, un routeur avec URLs partageables, et un statut `accepted_no_model` qui empêche toute fausse réponse IA.

Par rapport à la vision complète, l'écart est **structurel, pas cosmétique** : aucune des six fonctions n'est opérationnelle. Le produit actuel couvre environ **la couche 1 (interface)** et une fraction de la couche 3 (persistance de session) de l'architecture en cinq couches. Les couches 2 (HORIZON CORE), 4 (connecteurs/adaptateurs) et 5 (infrastructure distante) sont vides.

**Deux points de blocage dominent :** le registre d'orchestrateurs (F2) et le service de sécurité. Sans eux, F1, F3, F4, F5 et F6 ne peuvent pas être achevés.

**Ce qui ne doit pas être refait :** la persistance SQLite, la couche HTTP, le contexte de session, le routeur, le mécanisme de statuts `capabilities`, les 6 interfaces.

**Ce qui doit être décidé avant tout développement :** les 9 décisions du §12, en particulier DÉC-1 (données de démonstration), DÉC-3 (divergence de contrat), DÉC-4 (premier fournisseur LLM) et DÉC-8 (ordre F2/F4).

