# HORIZON LOCAL AI — Rapport de développement (2026-11-09)

Périmètre : application située dans
`C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI`.

Ce rapport ne remplace aucun audit antérieur : il documente uniquement les
travaux réalisés pendant cette session, les tests réellement exécutés et les
points restés ouverts. Aucun fichier original n'a été supprimé ni déplacé.

---

## 1. État de départ vérifié

| Élément | Constat mesuré |
|---|---|
| Backend | FastAPI `0.2.0`, port 8000, venv Python 3.12 (uv) opérationnel |
| Base | SQLite `backend/data/horizon.db`, migrations versionnées (`schema_migrations`) |
| Frontend | Vite 6.4.5 + React 19 + Tailwind 4, port 5173 |
| CORS | `http://localhost:5173`, `http://127.0.0.1:5173` (variable `HORIZON_CORS_ORIGINS`) |
| Authentification | désactivée par défaut (`HORIZON_ADMIN_TOKEN` absent → mode `local_open`) |
| Fournisseur LLM | aucun enregistré, aucun runtime local (Ollama absent, port 11434 fermé) |
| Espace disque `C:` | ~64 Mo libres → toute installation lourde reste exclue |

---

## 2. Travaux réalisés

### 2.1 Raccordement de la page Agents & Tools Catalog (Priorité 1)

`src/pages/agents-tools-catalog/AgentsToolsCatalog.tsx`

- Ajout d'une section « Registre réel des orchestrateurs » alimentée par
  `GET /api/v1/orchestrators` (aucune donnée statique dans cette section).
- Remplacement des trois compteurs fictifs (« 1 environnement local », etc.)
  par des valeurs mesurées : nombre d'orchestrateurs, nombre d'actifs, nombre de
  connexions vérifiées.
- Boutons « Actualiser » (rechargement réel) et « Gérer le registre »
  (navigation vers `/orchestrators`).
- Gestion explicite des erreurs API (message affiché, pas de repli silencieux).

### 2.2 Nouvelles pages raccordées au backend

| Page | Route | Source de données |
|---|---|---|
| Projets & Missions | `/projects` | `/api/v1/projects`, `/api/v1/missions`, `/api/v1/core/*` |
| Orchestrateurs | `/orchestrators` | `/api/v1/orchestrators` (+ capacités, projets, modèle) |
| Model Manager (live) | `/models` | `/api/v1/models`, `/settings/model-selection` |
| Knowledge & Memory (live) | `/memory` | `/api/v1/documents` |
| System Monitor (live) | `/monitor` | `/api/v1/system/metrics`, `/system/status`, `/operations` |

Les anciennes pages statiques correspondantes (`ModelManager.tsx`,
`AgentsToolsCatalog` historique, `KnowledgeMemoryHub.tsx`, `SystemMonitor.tsx`)
sont **conservées dans le dépôt** mais ne sont plus routées. Décision réversible :
un seul changement de route suffit à les réafficher.

### 2.3 Correction transversale

`src/api/errors.ts` : `describeApiError` accepte désormais `unknown` et normalise
via `toApiError`. Cette correction a supprimé 6 erreurs TypeScript
(`TS2345`) présentes dans `ModelManagerLive.tsx`, `OrchestratorRegistry.tsx` et
`Projects.tsx`.

### 2.4 Nouveau module backend : mémoire documentaire (Priorité 6, partielle)

| Fichier | Rôle |
|---|---|
| `backend/horizon/schema.py` | Migration 3 `documents_memory` (table `documents` + index projet) |
| `backend/horizon/repositories/documents.py` | CRUD + recherche mots-clés + archivage logique |
| `backend/horizon/models.py` | `DocumentCreate`, `DocumentUpdate` |
| `backend/horizon/routers/documents.py` | `GET/POST /api/v1/documents`, `GET/PATCH/DELETE /{id}` |
| `backend/horizon/repositories/__init__.py`, `routers/__init__.py` | Enregistrement des modules |
| `backend/app.py` | Import + inclusion du routeur `documents` (2 lignes) |

Caractéristiques :

- mémoire **centrale** distincte des mémoires spécialisées ;
- documents rattachables à un projet (`project_id` nullable) ;
- recherche par mots-clés SQL (`title`, `content`, `tags`, `source`) — aucune
  sémantique vectorielle revendiquée ;
- archivage logique (`status = archived`), jamais de suppression physique ;
- chaque écriture est journalisée dans `operation_log`.

### 2.5 Frontend de la mémoire

`src/api/documents.ts`, `src/api/entities.ts` (type `KnowledgeDocument`),
`src/config/env.ts` (routes `documents`/`document`),
`src/pages/knowledge-memory-hub/KnowledgeMemoryLive.tsx` : liste, filtre par
projet, recherche, création, ouverture et archivage.

### 2.6 Script de démarrage

`start.ps1` (racine du projet) : démarre le backend s'il n'écoute pas déjà,
choisit un port libre pour Vite, vérifie `/api/v1/health`. Aucun secret n'y est
écrit.

---

## 3. Tests réellement exécutés

### 3.1 Compilation et build

| Commande | Résultat |
|---|---|
| `npm run build` (tsc -b && vite build) | **OK** — 2103 modules, `dist/index.html` + assets générés |

### 3.2 Backend (requêtes HTTP réelles sur 127.0.0.1:8000)

| Test | Résultat obtenu |
|---|---|
| `GET /api/v1/health` | `200` `{"status":"ok","version":"0.2.0"}` |
| `GET /api/v1/capabilities` | `200` |
| `GET /api/v1/sessions` | `200`, 4 sessions |
| `GET /api/v1/projects` | `200`, `default_project_id` présent |
| `GET /api/v1/orchestrators` | `200`, liste réelle |
| `GET /api/v1/models` | `200`, `{"items":[],"selection":{...}}` |
| `GET /api/v1/settings/model-selection` | `200`, `auto` |
| `GET /api/v1/system/metrics` | `200`, mesures réelles (`windows-ctypes+shutil`) |
| `GET /api/v1/system/status` | `200`, compteurs réels |
| `GET /api/v1/documents` | `200`, `{"items":[],"count":0}` avant test |
| `POST /api/v1/documents` | `201`, document créé et relu |
| `GET /api/v1/documents?q=validation` | `200`, 1 résultat (recherche fonctionnelle) |
| `DELETE /api/v1/documents/{id}` | `200`, `status: archived`, liste active vide ensuite |
| `OPTIONS /api/v1/documents` (Origin 5173) | `200`, `Access-Control-Allow-Origin: http://localhost:5173` |

### 3.3 Cycle orchestrateurs (création → association → capacité → test réseau)

| Étape | Résultat |
|---|---|
| `POST /api/v1/projects` | `201` (projet de test créé) |
| `POST /api/v1/orchestrators` | `201`, `status=active`, `health_status=unverified` |
| `POST /orchestrators/{id}/projects` | association enregistrée (1 projet) |
| `POST /orchestrators/{id}/capabilities` | 1 capacité enregistrée |
| `POST /orchestrators/{id}/check` | `unavailable`, `Échec réseau : ConnectError` (appel réseau réel vers `127.0.0.1:9999`) |
| `DELETE /api/v1/orchestrators/{id}` | désactivation logique (`status=disabled`) |

### 3.4 Cycle missions et moteur central

| Étape | Résultat |
|---|---|
| `POST /api/v1/missions` | `201`, statut `draft` |
| `POST /missions/{id}/steps` | étape créée |
| `POST /missions/{id}/checkpoints` | point de contrôle créé |
| `POST /api/v1/core/plan` | `200` `{"status":"no_model","detail":"Aucun fournisseur LLM vérifié…"}` |
| `GET /api/v1/core/route?capability=text-generation` | `200`, orchestrateur sélectionné parmi les actifs |

Point important : le moteur central **refuse** de produire un plan sans
fournisseur vérifié. Aucune réponse IA n'est simulée.

### 3.5 Frontend en développement

| Test | Résultat |
|---|---|
| `GET http://localhost:5173/` | `200` |
| Transpilation des modules `App.tsx`, `ModelManagerLive`, `AgentsToolsCatalog`, `Projects`, `OrchestratorRegistry`, `SystemMonitorLive`, `KnowledgeMemoryLive` | `200` pour chacun |

Limite de vérification : aucun navigateur automatisé n'est disponible dans cet
environnement. Le rendu visuel et les interactions (clics, saisies) **n'ont pas
été observés** ; seuls le build de production et la transpilation des modules
sont prouvés. Les tests d'interface restent à effectuer manuellement.

### 3.6 Données de test créées

- projet `Test Registry E2E` (archivé) ;
- orchestrateur `Test Orchestrator E2E` (désactivé) ;
- fournisseur `Test Provider E2E` (supprimé) ;
- mission `Mission validation raccordement` (statut `draft`) ;
- document `Note de validation memoire` (archivé).

Aucune de ces entités n'est active ; elles n'influencent ni le routage ni les
plans. Elles peuvent être purgées sur demande explicite.

---

## 4. État par priorité

| Priorité | État réel | Preuve |
|---|---|---|
| P1 — Socle et registre des orchestrateurs | **API testée ; UI compilée, non testée en navigateur** | Création, association projet, capacité, test réseau, désactivation testés (3.3) |
| P2 — Projets et missions | **API testée ; UI compilée, non testée en navigateur** | Projets, missions, étapes, checkpoints testés (3.4) |
| P3 — Gestionnaire de modèles IA | **Fonctionnel, sans fournisseur réel** | CRUD + test réseau réels ; aucun fournisseur configuré (pas de clé) |
| P4 — HORIZON CORE | **Fonctionnel, bloqué par l'absence de fournisseur** | `/core/route` sélectionne réellement ; `/core/plan` renvoie `no_model` |
| P5 — Exécution et continuité | **Partiel** | Missions, étapes, checkpoints, statuts existent ; reprise automatique après interruption non implémentée |
| P6 — Mémoire et connaissances | **Partiel** | Mémoire documentaire locale fonctionnelle ; Google Drive et recherche sémantique absents |
| P7 — Sécurité et administration | **Partiel** | `require_admin` + `HORIZON_ADMIN_TOKEN` présents ; authentification non activée ; aucune interface de connexion |
| P8 — Supervision et évolution | **Partiel** | Métriques, statut, journal réels ; coûts, sauvegardes applicatives, Orchestration Builder absents |

---

## 5. Blocages et limites réels

1. **Aucun fournisseur LLM configuré** : sans clé API ni runtime local, aucune
   réponse IA réelle ne peut être produite. Le statut `no_model` est donc le
   comportement correct et attendu. Cette décision nécessite une action
   utilisateur (fournir une clé ou installer un runtime).
2. **Espace disque `C:` ≈ 64 Mo** : installation d'Ollama ou d'un modèle local
   exclue sur cette machine. Seul un fournisseur distant est réaliste.
3. **Authentification non activée** : le backend la supporte, mais aucune
   interface de saisie de jeton n'existe côté frontend. L'activer sans interface
   bloquerait toutes les écritures. À traiter avant toute exposition réseau.
4. **Tests d'interface non réalisés** : aucun navigateur automatisé disponible ;
   seuls build et transpilation sont prouvés.
5. **`DELETE` est logique** (archivage/désactivation) partout : aucune purge
   physique n'est possible via l'API, conformément à la règle de non-suppression.
6. **Pages statiques conservées** : les quatre anciennes pages restent dans le
   dépôt sans être routées (décision réversible, aucun fichier supprimé).

---

## 6. Démarrage, sauvegarde, restauration

### Démarrage

```powershell
cd "C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI"
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Ou manuellement :

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

```powershell
npm run dev -- --port 5173
```

Vérification : `GET http://127.0.0.1:8000/api/v1/health` doit renvoyer `200`.

### Sauvegarde

- Base locale : `backend\data\horizon.db` (copie à froid, backend arrêté de
  préférence) ;
- Code source : dossier `src\` + `backend\` + `package.json` ;
- Les archives existantes dans `03 MÉMOIRE LOCALE\07_SAUVEGARDES\` sont
  conservées telles quelles.

### Restauration

1. Arrêter le backend ;
2. Restaurer `horizon.db` depuis la sauvegarde ;
3. Redémarrer : les migrations manquantes sont rejouées automatiquement, sans
   suppression de données existantes.

---

## 7. Prochaines étapes recommandées (non réalisées)

1. Configurer un fournisseur LLM réel (`/models` ou `backend\.env`) puis vérifier
   `POST /api/v1/core/plan` avec une réponse réelle.
2. Ajouter une interface de connexion administrateur avant d'activer
   `HORIZON_ADMIN_TOKEN`.
3. Implémenter la reprise de mission après interruption (relance des étapes
   `running`, journalisation des reprises).
4. Étendre la mémoire : import de fichiers, intégration Google Drive,
   recherche sémantique.
5. Réaliser la campagne de tests d'interface manuels page par page.
6. Documenter les contrats API exposés (OpenAPI déjà disponible sur `/docs`).

---

## 8. Fichiers créés ou modifiés durant la session

**Créés**

- `src/pages/system-monitor/SystemMonitorLive.tsx`
- `src/pages/knowledge-memory-hub/KnowledgeMemoryLive.tsx`
- `src/api/documents.ts`
- `backend/horizon/repositories/documents.py`
- `backend/horizon/routers/documents.py`
- `start.ps1`

**Modifiés**

- `src/App.tsx` (routes `/projects`, `/orchestrators`, pages live)
- `src/api/errors.ts` (`describeApiError` accepte `unknown`)
- `src/api/entities.ts` (`KnowledgeDocument`, `DocumentStatus`)
- `src/config/env.ts` (routes documents)
- `src/pages/agents-tools-catalog/AgentsToolsCatalog.tsx` (registre réel)
- `src/pages/model-manager/ModelManagerLive.tsx` (colonne de sélection + formulaire)
- `backend/app.py` (inclusion du routeur `documents`)
- `backend/horizon/schema.py` (migration 3)
- `backend/horizon/models.py` (`DocumentCreate`, `DocumentUpdate`)
- `backend/horizon/repositories/__init__.py`, `backend/horizon/routers/__init__.py`

Aucun fichier existant n'a été supprimé, déplacé ou renommé.



## 15. Adaptation Offline-First / Desktop (ajout 2026-11-09)

**Existant analysé** : backend FastAPI + SQLite locale, frontend React/Vite servi
uniquement par le serveur de développement. L'application fonctionnait hors ligne
de fait, sans aucune garantie explicite (ni détection réseau, ni file d'attente,
ni règle de conflit).

**Adaptations réalisées** (aucune fonctionnalité retirée) :

- `backend/app.py` : le backend sert le build `dist/` (montage `/assets` +
  fallback SPA) — un seul processus suffit, aucune ressource externe dans
  `index.html`. Version 0.3.0. Worker de synchronisation démarré/arrêté avec
  l'application (inactif par défaut).
- `backend/horizon/connectivity.py` : sonde TCP mesurée, jamais d'exception.
- `backend/horizon/sync_provider.py` : adaptateur fournisseur-agnostique
  (implémentation Supabase REST/PostgREST), clé lue uniquement dans `.env`.
- `backend/horizon/repositories/sync.py` : file `sync_outbox`, conflits
  `sync_conflicts`, état `sync_state`.
- `backend/horizon/sync_engine.py` : logique partagée push/pull (routes + worker).
- `backend/horizon/sync_worker.py` : synchronisation automatique au retour du
  réseau, activée par `HORIZON_SYNC_AUTO=1`.
- `backend/horizon/routers/sync.py` : routes `/api/v1/sync/*`.
- `backend/horizon/schema.py` : migration 4 `offline_first_sync` (additive).
- Écritures métier : `projects`, `orchestrators`, `missions`, `documents`
  enregistrent chaque create/update/delete dans la file locale.
- `src/api/sync.ts`, `src/api/entities.ts`, `src/config/env.ts`,
  `src/pages/sync-center/SyncCenter.tsx`, `src/App.tsx` : page `/sync` live.
- `HORIZON.ps1`, `HORIZON.bat`, `HORIZON-Stop.ps1` : lanceur d'application de
  bureau (fenêtre Edge/Chrome en mode application, profil dédié), arrêt propre.
- `index.html` : titre « HORIZON LOCAL AI », langue `fr`.
- `docs/OFFLINE_FIRST_ARCHITECTURE.md` : architecture, contrats, limites, tests.
- `backend/.env.example` : variables de synchronisation documentées.

**Tests réellement exécutés** : build 2105 modules ; 11 routes API en 200 ; 10
routes SPA en 200 ; `/api/v1/sync/status` 200 ; écriture projet en 201 suivie
d'une entrée de file ; push/pull en `not_configured` sans altérer les données ;
détection hors ligne vérifiée sur sonde fermée ; migration 4 appliquée ; données
existantes conservées ; lanceur ouvert en mode application.

**Non vérifié** : rendu visuel de la page `/sync` (aucun navigateur automatisé),
synchronisation réelle vers Supabase (aucun fournisseur configuré), coupure
réseau physique de bout en bout.

**Limites** : mono-fournisseur, pas de fusion automatique de conflits, `pull`
n'écrit pas en local (consignation seulement), lanceur dépendant d'Edge/Chrome.


### 15.1 Correctif « la page Synchronisation ne marche pas » (2026-11-09)

**Symptôme signalé** : dans la fenêtre de bureau ouverte, la page `/sync`
paraissait inopérante.

**Cause identifiée réellement** : ce n'était pas la page qui était cassée mais la
**fenêtre déjà ouverte**, qui exécutait un bundle JS antérieur. Vite vide le
dossier `dist/assets` à chaque build : l'ancien fichier `index-CLQiI9qW.js`
n'existait plus, donc tout rechargement de cette fenêtre aboutissait à une page
vide (le titre de la fenêtre était encore `%COMPONENT_NAME%`).

**Preuves** : `dist/assets` ne contient plus que `index-D6ltuPd6.js` (387 130 o) ;
la fenêtre ouverte portait le titre `%COMPONENT_NAME%` au lieu de
`HORIZON LOCAL AI` ; le rendu de `/sync` en navigateur sans interface contenait
bien tous les blocs attendus.

**Correctifs appliqués** :

1. `backend/app.py` : le shell HTML servi par le backend renvoie désormais
   `Cache-Control: no-store, no-cache, must-revalidate` (vérifié en HTTP), les
   fichiers `/assets` hachés restant cachables sans risque.
2. `HORIZON.ps1` : l'URL de la fenêtre porte la version courante lue depuis
   `/api/v1/system/desktop` (`?v=0.3.0`), ce qui force un chargement frais.
3. L'ancienne fenêtre (PID 15416) a été fermée et une nouvelle ouverte
   (PID 18656, titre « HORIZON LOCAL AI »).

**Vérifications après correctif** : `GET /` → 200 avec en-tête `no-store` ;
`GET /sync` → 200 avec `no-store` ; le journal backend montre la fenêtre fraîche
appelant `/api/v1/sync/status`, `/sync/queue` (pending et failed) et
`/sync/conflicts` — tous en 200 ; rendu DOM de `/sync` confirmé.

Conclusion : la page `/sync` fonctionne ; le défaut était un cache de bundle
côté fenêtre, désormais neutralisé à la source.


## 16. Poste de pilotage central, gestionnaire de thèmes et audit hybride (2026-11-09)

**Demande** : interface centrale unique de pilotage, thèmes clair/sombre/auto/
confort/contraste/personnalisé avec accents, et vérification réelle de
l'architecture hybride (pas seulement la présence du mode `offline_first`).

**Audit préalable** : 8 pages routées + `/sync` (navigation fragmentée) ;
couleurs figées dans chaque page (200 `border-white`, 158 `bg-white`,
140 `text-slate-500`, 57 `text-cyan-300`…) ; `main.tsx` forçait l'absence de
thème ; `index.css` importait une police Google distante ; `src/settings/theme.ts`
(généré) inutilisé et conservé intact.

**Réalisations**

- `src/pages/cockpit/Cockpit.tsx` : page **par défaut** (`/` → `/cockpit`).
  Zone centrale = conversation HORIZON CORE + planification réelle
  (`/core/plan`) ; panneau gauche = projets, missions, historique, accès rapide ;
  panneau droit = orchestrateurs, ressources, progression, **état des
  connexions**, informations utiles ; tiroirs secondaires (Modèles, Mémoire,
  Outils & agents, Sécurité, Synchronisation, Supervision, Paramètres) qui
  **réutilisent les pages existantes** — aucune fonctionnalité supprimée.
- `src/theme/` : modèle, provider, contrôles. 6 modes, 6 palettes d'accent,
  persistance `localStorage['horizon-local-ai:theme:v1']`, mode automatique
  (système puis horaires personnalisés) sans jamais écraser un choix manuel,
  `prefers-color-scheme` et `prefers-reduced-motion` respectés, transitions
  douces, focus renforcé en contraste élevé.
- `src/index.css` : jetons par thème, accents (assombris en clair), navigation
  unifiée par jetons, **passerelle de compatibilité** (156 sélecteurs
  `[class~=…]`) reliant les couleurs figées des pages existantes aux jetons du
  thème : les 9 pages suivent le thème **sans être réécrites**.
- `src/main.tsx` : plus aucun forçage de thème ; `App.tsx` : sélecteurs de thème
  et d'accent dans l'en-tête ; `ChatSessionContext` : `/cockpit` reconnu comme
  espace de conversation.

**Vérifications réellement exécutées**

| Vérification | Résultat |
|---|---|
| Build production | succès, **2110 modules**, CSS 72,00 kB, JS 421,62 kB |
| Rendu réel de `/cockpit` | DOM 30 233 caractères ; textes des 3 panneaux présents ; `data-theme` et `data-accent` appliqués |
| Appels déclenchés par le cockpit | `/projects`, `/orchestrators`, `/models`, `/system/status`, `/sync/status`, `/missions`, `/sessions` — tous 200 |
| CSS livré | blocs `[data-theme=light/comfort/contrast/custom]`, `[data-accent=*]`, 156 passerelles, `color-mix` ×214 |
| Aucune ressource distante | seul `https://tailwindcss.com` subsiste dans un commentaire CSS (police Google retirée) |
| **Hors ligne réel** (sonde `127.0.0.1:1`) | `/health`, `/projects`, `/sessions`, `/capabilities`, `/cockpit` → 200 ; `/sync/status` → `online:false` + erreur mesurée |
| Persistance locale | moteur arrêté puis relancé : 3 projets et 1 écriture en file retrouvés |
| Cycle de conflit | créé par le dépôt → `count` 1 via API → `resolved 1` via API → `count` 0 |
| Worker automatique | `HORIZON_SYNC_AUTO=1` : démarre (intervalle 45 s), ne plante pas, n'écrit rien sans fournisseur |
| Supabase / fournisseur IA | **non configurés** : `provider: none`, `push/pull` → `not_configured`, `/core/plan` → `no_model` |

**Statut final** : terminé — cockpit, thèmes, cohérence visuelle, hors ligne réel,
persistance, gestion de conflits. Partiel — reprise d'un envoi interrompu
(prérequis distant). Bloqué — connexion Supabase réelle, synchronisation
bidirectionnelle, continuité multi-machines et fournisseur IA : tous dépendent
d'un projet Supabase et/ou d'une clé d'API à fournir. Aucune connexion n'est
présentée comme active sans vérification.

Détail complet : `docs/UI_COCKPIT_AND_THEMES.md`.

## 17. HORIZON CENTRAL AI — identité, design system et motion (2026-11-09)

**Demande** : renommer l'application en HORIZON CENTRAL AI, améliorer l'interface
existant, mettre en place thèmes/palettes, motion design, et vérifier réellement
les capacités offline-first — sans reconstruire ni dégrader l'existant.

**Réalisé**

1. **Identité** : titre, métadonnées, marque de navigation, en-tête du poste de
   pilotage, libellé de version, titre de l'API (OpenAPI + Swagger), prompt de
   planification, lanceurs PowerShell/BAT, raccourci Windows (recréé sous le nom
   « HORIZON CENTRAL AI »), README et documents produit. Exceptions techniques
   documentées (chemins, nom npm, clés `localStorage`, `horizon.db`, `HORIZON_*`).
2. **Design system** (`src/index.css`) : jetons d'espacement/élévation/mouvement,
   composants communs (cartes, panneaux, KPI, badges, boutons, champs, listes,
   alertes, progression), finitions globales (barres de défilement, sélection,
   focus).
3. **Motion design** : apparition échelonnée des panneaux, transition de page,
   glissement des tiroirs, micro-interactions, indicateurs d'activité réservés aux
   opérations réelles ; neutralisation totale sous `prefers-reduced-motion`.
4. **Poste de pilotage** : bandeau de 4 indicateurs (projet actif, missions,
   orchestrateurs/fournisseurs/modèles, interventions) et bloc « Éléments
   nécessitant une décision ou une action » dérivé uniquement d'états mesurés.
5. **Navigation** : marque retravaillée, onglets en pilules, barre collante
   translucide, état actif teinté par l'accent, défilement sans barre visible.
6. **Supabase** : stratégie de migration contrôlée documentée
   (`docs/SUPABASE_MIGRATION_STRATEGY.md`) + outil d'export non destructif
   (`backend/tools/export_snapshot.py`, lecture seule, testé : 41 lignes, aucun
   appel réseau). Aucune migration exécutée.

**Tests réellement exécutés**

- Build : 2110 modules, CSS 87,52 kB, JS 424,83 kB.
- 8 scénarios de thème pilotés par CDP (préférence écrite, page rechargée,
  `getComputedStyle` mesuré) : fonds distincts conformes (sombre `rgb(10,11,16)`,
  clair `rgb(245,247,251)`, confort `rgb(20,22,28)`, contraste `rgb(0,0,0)`,
  personnalisé `rgb(15,20,32)`), contrastes **14,01 à 21,00** (WCAG AAA),
  persistance démontrée par rechargement, mode automatique conforme.
- `prefers-reduced-motion` forcé : animations neutralisées (`none`, 0 s) sur les
  8 scénarios.
- Passerelle de compatibilité mesurée sur une classe figée (`bg-[#090c13]` →
  `rgb(10,11,16)`), donc les pages existantes suivent bien le thème.
- 10 routes API et 11 routes SPA → 200 ; titre `HORIZON CENTRAL AI` ;
  `openapi.json` → « HORIZON CENTRAL AI — Core API ».
- Données locales intactes (3 projets, 1 orchestrateur, 1 mission, 1 document,
  6 sessions, file de synchronisation conservée).

**Incident traité** : disque `C:` à 0 Mo pendant les tests. Nettoyage de mes
propres artefacts (profils Chrome de test ≈57 Mo) et du cache npm (≈665 Mo) →
696 Mo libres ; aucune donnée du projet touchée.

**Non réalisé / bloqué** : synchronisation Supabase réelle et fournisseur IA
(prérequis humains) ; tests visuels pixel par pixel (aucun outil de capture) ;
capture d'écran comparative avant/après.
