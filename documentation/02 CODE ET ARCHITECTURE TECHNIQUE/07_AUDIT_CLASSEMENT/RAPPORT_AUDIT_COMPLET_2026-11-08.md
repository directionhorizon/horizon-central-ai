# HORIZON LOCAL AI — RAPPORT D'AUDIT COMPLET

Date : 2026-11-08
Portée : audit préparatoire en lecture seule + consolidation contrôlée
Racine officielle : `C:\Users\hp\HORIZON LOCAL AI`
Application source : `C:\Users\hp\Desktop\HORIZON_TEST_1.0.0\HORIZON_LOCAL_AI`
Destination cible : `C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI`

Aucun fichier original n'a été supprimé, déplacé, renommé ou modifié.
Aucune archive n'a été extraite dans les dossiers sources.
Aucune dépendance n'a été installée.

---

## A. Inventaire des emplacements et des archives

### A.1 Racine `C:\Users\hp\HORIZON LOCAL AI`

- 66 fichiers, 34 dossiers, 0,7 Mo.
- 50 fichiers hors `06 ARCHIVES`.
- Contenu : documentation `.md` (majoritairement des squelettes de 74 à 3 169 octets), 10 archives `.zip`, 5 fichiers `.bak`, 2 livrables d'audit CSV, 1 plan `.txt`.
- Aucun code source, aucun backend, aucun `package.json`.
- Quatre piliers présents : `01 FONCTIONNEMENT`, `02 CODE ET ARCHITECTURE TECHNIQUE`, `03 MÉMOIRE LOCALE`, `04 MÉMOIRE EN LIGNE`.

### A.2 Application `...\Desktop\HORIZON_TEST_1.0.0\HORIZON_LOCAL_AI`

- 47 fichiers, 15 dossiers, 0,14 Mo.
- Ni `node_modules`, ni `.venv`, ni `package-lock.json`.
- Fichiers cachés : `.gitignore`, `.prettierignore`, `.prettierrc`, `backend\.env.example`.
- Frontend React 19 / Vite 6 / TypeScript 5.7 / Tailwind 4.
- Backend FastAPI (`backend\app.py`, 5 987 octets).
- Documentation : `README.md`, `RELEASE_NOTES_1.0.0.md`, `SOURCE_MANIFEST.json`, `docs\contracts\` (2 fichiers).

### A.3 Archives — 10 fichiers, vérifiés par SHA256

`06 ARCHIVES\SOURCES_ORIGINALES` (6 exports MagicPath) :

| Archive | Taille | Entrées | Nature |
|---|---|---|---|
| Main Workbench.zip | 82 856 | 31 | Application Vite autonome |
| Model Manager.zip | 81 972 | 30 | Application Vite autonome |
| Agents & Tools Catalog.zip | 80 393 | 30 | Application Vite autonome |
| knowledge & Memory HUB.zip | 81 874 | 30 | Application Vite autonome |
| AI Control Center.zip | 76 854 | 27 | Application Vite autonome |
| System Monitor.zip | 76 915 | 27 | Application Vite autonome |

`06 ARCHIVES\VERSIONS` (4 livraisons) :

| Archive | Taille | Entrées | Nature |
|---|---|---|---|
| HORIZON_LOCAL_AI_Interfaces_Integration_v0.1.zip | 50 976 | 39 | Frontend seul |
| HORIZON_LOCAL_AI_Interfaces_Integration_v0.2.zip | 51 798 | 40 | Frontend seul |
| HORIZON_LOCAL_AI_Interfaces_Integration_v0.5.zip | 52 648 | 40 | Frontend seul |
| HORIZON_LOCAL_AI_1.0.0_2026-11-07.zip | 59 126 | 47 | Frontend + backend + docs |

Les 10 archives présentes dans `C:\Users\hp\Desktop\Nouveau dossier` ont des empreintes SHA256 identiques à celles listées ci-dessus. Ce sont les mêmes sources, pas des sources indépendantes. Aucune autre archive pertinente n'a été trouvée hors de ces deux emplacements.

### A.4 Point vérifié décisif

Les 47 fichiers de l'application du Bureau sont **identiques octet pour octet** à l'archive `HORIZON_LOCAL_AI_1.0.0_2026-11-07.zip` (47 identiques, 0 différent, 0 absent). Le dossier du Bureau est donc une copie de travail de l'archive 1.0.0, sans modification locale.

---

## B. Comparaison des 6 interfaces MagicPath avec les 6 pages intégrées

Méthode : comparaison octet par octet (SHA256), puis comparaison ligne à ligne en lecture UTF-8 correcte. Les faux écarts dus à l'encodage de lecture ont été écartés après vérification par égalité binaire.

| Interface MagicPath | Fichier source | Taille orig. | Taille intégrée | État |
|---|---|---|---|---|
| Main Workbench | `src/components/generated/MainWorkbench.tsx` | 10 049 | 8 422 | MODIFIÉ |
| Model Manager | `src/components/generated/ModelManager.tsx` | 15 477 | 15 410 | MODIFIÉ |
| Agents & Tools Catalog | `src/components/generated/AgentsToolsCatalog.tsx` | 7 480 | 7 350 | MODIFIÉ |
| Knowledge & Memory Hub | `src/components/generated/KnowledgeMemoryHub.tsx` | 13 580 | 13 511 | MODIFIÉ |
| AI Control Center | `src/components/generated/AIControlCenter.tsx` | 7 815 | 6 709 | MODIFIÉ |
| System Monitor | `src/components/generated/SystemMonitor.tsx` | 8 978 | 8 978 | IDENTIQUE |

### B.1 Détail des écarts

**Main Workbench** (155 → 106 lignes) :
- Retiré : imports et rendu de `SideNav`, `SystemHeader`, `ContextPanel`.
- Retiré : type `Message` local, `INITIAL_MESSAGES` (3 messages de démonstration), état local `useState`.
- Ajouté : `useChatSession` et `addUserMessage` depuis `shared/ChatSessionContext`.
- Modifié : « Live session » → « Prototype conversation », « Context synchronized » → « Local demo state ».
- Effet visuel : la colonne latérale (`ml-64`) et le panneau de contexte (`mr-80`) disparaissent.

**Model Manager** :
- Retiré : imports et rendu de `SideNav`, `SystemHeader`.
- Modifié : `ProviderStatus` passe de `'Online' | 'Offline'` à `'Not verified'` ; les 3 statuts fournisseurs et la latence passent de valeurs simulées à « Not verified » / « — ».
- Modifié : « Your configured inference endpoints » → « Example providers · endpoints are not connected ».
- Modifié : layout `ml-64 ... pt-24` → `mx-auto ... pt-8`.
- Effet : les faux états « Online/Offline » ont été volontairement supprimés pour ne pas simuler une connexion réelle.

**Agents & Tools Catalog** :
- Retiré : imports et rendu de `SideNav` (`activeLabel="Environment Manager"`) et `SystemHeader`.
- Modifié : layout `ml-64 ... pt-16` → `mx-auto`.
- Contenu métier conservé : registre d'environnements (`Environment`, `Local environment`, `Cloud environment`, `External orchestrators`).

**Knowledge & Memory Hub** :
- Retiré : imports et rendu de `SideNav` (`activeLabel="Knowledge Hub"`) et `SystemHeader`.
- Modifié : layout `ml-64 ... pt-24` → `mx-auto ... pt-8`.
- Contenu métier conservé : import/indexation de dossiers, cartes documentaires, moteur de contexte.

**AI Control Center** (76 → 57 lignes) :
- Retiré : en-tête `<header className="sticky top-0 ...">` avec icône `BrainCircuit`, indicateur d'état, titre « HORIZON / Control Center ».
- Retiré : type `Message` local et état local, remplacés par `useChatSession` (`messages`, `addUserMessage`, `resetSession`).
- Modifié : hauteur de layout `calc(100vh-4rem)` → `calc(100vh-5rem)`.
- Effet : le bandeau propre à l'écran disparaît, la navigation globale de `App.tsx` prend le relais.

### B.2 Composants orphelins créés par l'intégration (code mort, non supprimé)

13 fichiers existent sans être importés par aucune page :

- `src\pages\main-workbench\` : `SideNav.tsx`, `SystemHeader.tsx`, `LLMSelector.tsx`, `ContextPanel.tsx`
- `src\pages\model-manager\` : `SideNav.tsx`, `SystemHeader.tsx`, `LLMSelector.tsx`
- `src\pages\agents-tools-catalog\` : `SideNav.tsx`, `SystemHeader.tsx`, `LLMSelector.tsx`
- `src\pages\knowledge-memory-hub\` : `SideNav.tsx`, `SystemHeader.tsx`, `LLMSelector.tsx`

`LLMSelector` n'est importé que par `SystemHeader`, lui-même orphelin. Ces fichiers sont signalés, non supprimés.

### B.3 Meilleure base de référence par interface

| Interface | Base retenue | Motif |
|---|---|---|
| Main Workbench | Version intégrée | Contexte partagé requis par l'architecture ; layout d'origine récupérable dans le ZIP |
| Model Manager | Version intégrée | Statuts « Not verified » honnêtes ; le ZIP contient de fausses valeurs |
| Agents & Tools Catalog | Version intégrée | Contenu métier identique, layout cohérent avec la navigation globale |
| Knowledge & Memory Hub | Version intégrée | Idem |
| AI Control Center | Version intégrée | Évite le doublon d'en-tête avec la navigation globale |
| System Monitor | Source = intégrée | Fichiers identiques |

Aucune interface n'a été remplacée. Les originaux restent dans les ZIP.

---

## C. Comparaison des 4 versions

### C.1 Chronologie et contenu

| Version | Entrées | Frontend | Backend | Docs | Apport principal |
|---|---|---|---|---|---|
| v0.1 | 39 | 6 pages | non | non | Intégration initiale des 6 écrans, `App.tsx` 2 078 o, README 1 892 o |
| v0.2 | 40 | 6 pages | non | non | Ajout de `src/shared/ChatSessionContext.tsx` (2 746 o) ; contexte partagé Workbench ↔ Control Center |
| v0.5 | 40 | 6 pages | non | non | Refonte des 6 pages + contexte (3 679 o) + `App.tsx` 2 452 o |
| 1.0.0 | 47 | 6 pages | oui (4 fichiers) | oui (2 fichiers) | Ajout backend FastAPI + contrats API + notes de version |

### C.2 Différences fichier par fichier

**v0.2 par rapport à v0.1**
- Ajouté : `src/shared/ChatSessionContext.tsx`
- Modifiés : `package.json`, `README.md`, `src/App.tsx`, `AIControlCenter.tsx`, `MainWorkbench.tsx`
- Supprimés : aucun

**v0.5 par rapport à v0.2**
- Ajoutés : aucun
- Supprimés : aucun
- Modifiés : `package.json`, `README.md`, `src/App.tsx`, les 6 pages, `src/shared/ChatSessionContext.tsx`

**1.0.0 par rapport à v0.5**
- Ajoutés (7) : `backend/.env.example`, `backend/app.py`, `backend/README.md`, `backend/requirements.txt`, `docs/contracts/capabilities.example.json`, `docs/contracts/CORE_API_CONTRACT_v0.1.md`, `RELEASE_NOTES_1.0.0.md`
- Supprimés : aucun
- Modifiés : `.gitignore`, `package.json`, `README.md`
- Aucune page modifiée : les 6 pages de 1.0.0 sont identiques à celles de v0.5.

### C.3 Régressions et points à conserver

**Régressions identifiées** :
1. Aucune régression fonctionnelle entre versions : aucun fichier supprimé, aucune page dégradée entre v0.2, v0.5 et 1.0.0.
2. Régression documentaire : le `README.md` de 1.0.0 annonce la consolidation des versions « v0.1 à v0.7 ». Or seules v0.1, v0.2 et v0.5 existent en archive. **v0.3, v0.4, v0.6 et v0.7 sont absentes** : leur contenu n'est donc pas vérifiable.
3. Régression d'architecture visuelle entre MagicPath et l'intégration : disparition de `SideNav` / `SystemHeader` / `ContextPanel` dans les pages intégrées (voir B.1), avec 13 composants orphelins.
4. Le `README.md` 1.0.0 indique comme emplacement cible `02_CODE_SOURCE\HORIZON_APP`, alors que la destination retenue est `02_CODE_SOURCE\HORIZON_LOCAL_AI`. Incohérence documentaire, sans effet sur les fichiers.

**À conserver dans la version finale** : l'ensemble des 47 fichiers de 1.0.0 (frontend + backend + contrats), et les 6 ZIP MagicPath comme référence de conception.

---

## D. État réel de l'application frontend / backend

### D.1 Frontend

| Élément | Constat |
|---|---|
| Stack | React 19.0, Vite 6.2, TypeScript 5.7, Tailwind 4.0, Radix UI, lucide-react |
| Entrée | `src/main.tsx` → `src/App.tsx` |
| Routage | Aucun routeur : `useState<PageId>` avec 6 valeurs et affichage conditionnel |
| Navigation | Barre supérieure unique (`horizon-nav`), 6 boutons |
| État global | `ChatSessionProvider` (`ChatSessionContext`) |
| Persistance | `localStorage` uniquement (`STORAGE_KEY`) |
| Appels réseau | **0** — aucune occurrence de `fetch`, `axios`, `/api/`, `WebSocket`, `EventSource` dans `src` |
| Conséquence | Le frontend ne dialogue pas avec le backend. Toutes les données affichées sont locales ou de démonstration. |

### D.2 Backend (`backend\app.py`, 5 987 o)

| Élément | Constat |
|---|---|
| Framework | FastAPI 0.115.12, Uvicorn 0.34.0, Pydantic 2.11.3, python-dotenv 1.1.0, HTTPX 0.28.1 |
| Stockage | SQLite, tables `sessions` et `messages`, chemin `HORIZON_DATABASE_PATH` (défaut `./data/horizon.db`) |
| CORS | `HORIZON_CORS_ORIGINS` (défaut `http://localhost:5173,http://127.0.0.1:5173`) |
| Routes | 7 : `GET /api/v1/health`, `GET /api/v1/capabilities`, `POST /api/v1/sessions`, `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}`, `POST /api/v1/sessions/{id}/messages`, `POST /api/v1/sessions/{id}/reset` |
| LLM | Aucun. `/capabilities` renvoie `llm.default = not_configured` sauf si `HORIZON_LLM_BASE_URL` et `HORIZON_LLM_MODEL` sont définis, auquel cas `unverified` |
| Réponse IA | Aucune. `add_message` enregistre le message et renvoie `execution.status = "accepted_no_model"` avec un avertissement explicite |
| Authentification | **Aucune**. Pas de jeton, pas de rôle, pas de permission |
| Migrations | Aucune. Création des tables au démarrage via `init_db()` dans `lifespan` |
| Journalisation | Aucune. Pas de log applicatif, pas de trace d'audit |

### D.3 Communication frontend ↔ backend

Non établie. Le contrat `docs\contracts\CORE_API_CONTRACT_v0.1.md` et l'exemple `capabilities.example.json` décrivent l'API, mais aucun code frontend ne les consomme. C'est un raccordement à faire, non un existant.

---

## E. État des 8 espaces fonctionnels

| # | Espace prévu | Page | Backend | État réel | Preuve |
|---|---|---|---|---|---|
| 1 | Main Workbench | Oui | partiel (sessions/messages) | **Interface seule, non raccordée** | Aucun appel API ; messages en `localStorage` |
| 2 | AI Control Center | Oui | non | **Interface seule, simulée** | Conversation locale partagée, `resetSession` local |
| 3 | Model Manager | Oui | non | **Interface seule, statuts neutralisés** | 3 fournisseurs d'exemple, `Not verified` |
| 4 | Environment Manager | Non (absorbé dans Agents & Tools Catalog) | non | **Absent en tant qu'espace** | 0 occurrence de « Environment Manager » dans `src` |
| 5 | Knowledge & Memory | Oui | non | **Interface seule, simulée** | Import/indexation sans backend |
| 6 | System Memory Store | Non | non | **Absent** | 0 occurrence de « System Memory » |
| 7 | Task Manager | Non | non | **Absent** | 0 occurrence de « Task Manager » |
| 8 | Security & Permissions | Non | non | **Absent** | 0 occurrence de « Security » / « Permissions » |

Bilan : 5 espaces ont une interface (dont 1 partiellement adossée à un backend existant mais non consommé), 4 sont absents. Aucun espace n'est opérationnel de bout en bout. Aucune interface ne prouve une fonctionnalité.

---

## F. État de l'architecture documentaire (4 piliers)

| Pilier | Fichiers | État | Constat |
|---|---|---|---|
| `01 FONCTIONNEMENT` | 17 | Squelettes + 5 `.bak` | Contenus courts (74 à 3 169 o) ; doublons de nom entre la racine du pilier et les sous-dossiers |
| `02 CODE ET ARCHITECTURE TECHNIQUE` | 15 | Squelettes + archives | `02_CODE_SOURCE` vide (1 README de 139 o) alors qu'il est la destination du code |
| `03 MÉMOIRE LOCALE` | 8 | Squelettes | `06_CACHE` et `07_SAUVEGARDES` vides |
| `04 MÉMOIRE EN LIGNE` | 9 | Squelettes | Aucun contenu réel |

Relations entre documentation et code : **aucune correspondance directe**. Les documents d'architecture décrivent Windows + Google Drive + GitHub privé, sans jamais décrire les 8 espaces fonctionnels ni les 6 interfaces MagicPath. Le document `Architecture_Generale.md` existe en deux versions :
- `01_ARCHITECTURE\Architecture_Generale.md` — 585 o, modifiée le 08/11 à 00:12 ;
- `02 CODE ET ARCHITECTURE TECHNIQUE\Architecture_Generale.md` — 495 o, version antérieure.

Les deux sont conservées. La comparaison et la décision documentée restent à faire.

---

## G. Doublons, incohérences, fichiers manquants et risques

### G.1 Doublons exacts (SHA256) — 5 groupes, tous dans le pilier 02

| Empreinte | Fichiers identiques |
|---|---|
| ECB2F30CD13C | `01_ARCHITECTURE\Architecture_Logicielle.md` ↔ `06 ARCHIVES\DOCUMENTS_HISTORIQUES\Architecture_Logicielle.md` |
| C6A69F8AEF3F | `03_MODULES\Composants_Modules.md` ↔ `DOCUMENTS_HISTORIQUES\Composants_Modules.md` |
| 0648AEF8A2F6 | `04_INTEGRATIONS\Integrations_API.md` ↔ `DOCUMENTS_HISTORIQUES\Integrations_API.md` |
| 13E60B4B4EB5 | `05_CONFIGURATION\Environnement_Windows.md` ↔ `DOCUMENTS_HISTORIQUES\Environnement_Windows.md` |
| 446C3F190E7F | `DOCUMENTS_HISTORIQUES\Plan_Implementation.md` ↔ `07_PLANIFICATION\Plan_Implementation.md` |

Conséquence : `DOCUMENTS_HISTORIQUES` n'est pas un historique de versions distinctes. C'est une copie de 4 documents actifs. Aucune suppression effectuée.

### G.2 Doublons de nom sans doublon de contenu (pilier 01)

`Vision_Mission_Objectifs.md`, `Principes_Fonctionnement.md`, `Catalogue_Fonctionnel.md`, `Gestion_Priorites.md` existent en deux exemplaires de contenus différents : une version courte à la racine du pilier, une version longue dans un sous-dossier. Ce sont de vraies versions distinctes, à conserver toutes les deux.

### G.3 Doublons dans l'application

`LLMSelector.tsx` (3 936 o) et `SystemHeader.tsx` (2 535 o) sont copiés à l'identique dans 4 dossiers de pages. `SideNav.tsx` existe en 2 variantes (2 927 o et 2 461 o). Ce sont des copies d'intégration, non des versions.

### G.4 Incohérences relevées

1. `SOURCE_MANIFEST.json` cite `magicpath-project.zip` alors que l'archive réelle est `Model Manager.zip`.
2. `SOURCE_MANIFEST.json` annonce `MainWorkbench.tsx` à 10 049 o et `ModelManager.tsx` à 15 477 o, valeurs des ZIP MagicPath, alors que les fichiers livrés mesurent 8 422 o et 15 410 o. Le manifeste décrit un état antérieur à l'intégration.
3. Le plan de classement `PLAN_CLASSEMENT_LOCAL.txt` annonce 58 fichiers alors que la racine en contient 66. Le chiffre 58 correspond aux lignes de `INVENTAIRE_LOCAL.csv`.
4. Le plan de classement propose une destination `06_VERSIONS_ET_SAUVEGARDES` qui n'existe pas ; le dossier réel est `06 ARCHIVES`.
5. Le `README.md` 1.0.0 indique `02_CODE_SOURCE\HORIZON_APP` comme cible, alors que la cible retenue est `HORIZON_LOCAL_AI`.
6. Le `README.md` 1.0.0 revendique la consolidation de v0.1 à v0.7, alors que 4 versions intermédiaires sont absentes des archives.
7. `DOUBLONS_EXACTS.csv` (livrable d'audit antérieur) est vide alors que 5 groupes de doublons existent.
8. `02_CODE_SOURCE` ne contient aucun code, alors que c'est le point d'accueil prévu de l'application.

### G.5 Fichiers manquants

- `package-lock.json` ou `yarn.lock` : absent de l'application livrée. Les 6 ZIP MagicPath contiennent chacun un `yarn.lock` de 173 062 o ; la livraison 1.0.0 ne l'a pas repris. **Les versions exactes des dépendances ne sont donc pas verrouillées.**
- 4 versions intermédiaires (v0.3, v0.4, v0.6, v0.7) citées mais introuvables.
- Aucun test automatisé : `06_TESTS\Plan_Tests.md` (163 o) est un squelette, sans fichier de test.
- Aucun fichier de migration de base, aucun script de démarrage.

### G.6 Risques

| Risque | Niveau | Détail |
|---|---|---|
| Dépendances non verrouillées | élevé | Absence de lockfile : `npm install` peut produire un arbre différent de celui validé |
| Build non certifié | moyen | Le README indique que `npm run build` n'a pas été exécuté faute de dépendances installées. Ce point n'est pas vérifié à ce stade |
| Aucun test automatisé | moyen | Impossible de détecter une régression par exécution |
| Frontend non raccordé | élevé | 0 appel API : le backend est inutilisé par l'interface |
| 4 espaces absents | élevé | Environment Manager, System Memory Store, Task Manager, Security & Permissions |
| Absence d'authentification | moyen | Backend sans jeton ni rôle ; à traiter avant toute exposition réseau |
| Code mort (13 composants) | faible | Aucun impact d'exécution, poids de maintenance |
| Doublons documentaires | faible | Aucune perte, mais risque de divergence future |

---

## H. Architecture consolidée proposée

```
C:\Users\hp\HORIZON LOCAL AI\
├─ 01 FONCTIONNEMENT\                                   inchangé, .bak conservés
├─ 02 CODE ET ARCHITECTURE TECHNIQUE\
│  ├─ 01_ARCHITECTURE\          documents d'architecture + contrats API
│  ├─ 02_CODE_SOURCE\
│  │  └─ HORIZON_LOCAL_AI\      application complète (47 fichiers)
│  ├─ 03_MODULES\ 04_INTEGRATIONS\ 05_CONFIGURATION\    .env.example uniquement
│  ├─ 06 ARCHIVES\              10 ZIP + DOCUMENTS_HISTORIQUES, inchangés
│  ├─ 06_TESTS\ 07_AUDIT_CLASSEMENT\ 07_PLANIFICATION\
├─ 03 MÉMOIRE LOCALE\07_SAUVEGARDES\   sauvegardes ZIP de cette consolidation
└─ 04 MÉMOIRE EN LIGNE\                                inchangé
```

Aucune arborescence parallèle n'est créée : uniquement des sous-dossiers déjà existants.

---

## I. Plan de consolidation exécuté

| # | Source | Destination | Action |
|---|---|---|---|
| 1 | Rapports d'audit | `07_AUDIT_CLASSEMENT\` | Création de 4 fichiers de rapport et d'inventaire |
| 2 | `C:\Users\hp\HORIZON LOCAL AI` (66 fichiers) | `03 MÉMOIRE LOCALE\07_SAUVEGARDES\` | ZIP créé dans `%TEMP%` puis déplacé (évite l'auto-inclusion) |
| 3 | `...\Desktop\HORIZON_TEST_1.0.0\HORIZON_LOCAL_AI` (47 fichiers) | `03 MÉMOIRE LOCALE\07_SAUVEGARDES\` | ZIP créé puis déplacé |
| 4 | `...\Desktop\HORIZON_TEST_1.0.0\HORIZON_LOCAL_AI` (47 fichiers) | `02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI` | Copie par `Copy-Item -Recurse`, original conservé |
| 5 | Vérification | — | 47 fichiers attendus, SHA256 identiques |

Non exécuté volontairement, en attente de décision : extraction des archives, factorisation des composants orphelins, raccordement frontend/backend, création des 4 espaces manquants.

---

## J. Contrôles à effectuer après consolidation

1. **Intégrité des sauvegardes** : ouverture par `ZipFile.OpenRead` sur les 2 ZIP, comparaison du nombre d'entrées avec la source (66 et 47).
2. **Intégrité de la copie** : SHA256 des 47 fichiers copiés comparés aux 47 SHA256 de la source ; 0 fichier manquant, 0 altéré.
3. **Structure** : arborescence de `02_CODE_SOURCE\HORIZON_LOCAL_AI` conforme (frontend `src`, backend `backend`, docs `docs`).
4. **Non-régression des originaux** : empreintes de la racine et de l'application du Bureau inchangées après opération.
5. **Dépendances** : confirmer la présence de `package.json` et `backend\requirements.txt` dans la copie ; signaler l'absence de lockfile.
6. **Cohérence documentaire** : aligner le `README.md` sur le chemin réel (`HORIZON_LOCAL_AI`) et sur le nombre réel de versions disponibles.

---

## K. Contrôles réellement exécutés et résultats

### K.1 Sauvegardes ZIP

| Archive | Emplacement | Octets | Fichiers | Dossiers vides | SHA256 identiques | Altérés | Manquants |
|---|---|---|---|---|---|---|---|
| HORIZON_RACINE_2026-11-08.zip | `03 MÉMOIRE LOCALE\07_SAUVEGARDES` | 684 541 | 71 | 2 | 71 | 0 | 0 |
| HORIZON_APP_BUREAU_2026-11-08.zip | `03 MÉMOIRE LOCALE\07_SAUVEGARDES` | 59 126 | 47 | 0 | 47 | 0 | 0 |

Les deux archives s'ouvrent correctement (`ZipFile.OpenRead`), sans erreur. Le contenu de chaque fichier archivé a été comparé à la source par SHA256 : 0 écart.

Note : la sauvegarde de la racine a été créée dans `%TEMP%` puis déplacée, afin que le ZIP ne s'inclue pas lui-même. Les deux archives ont d'abord été créées sans extension à cause d'un défaut de génération de commande, puis renommées en `.zip`. Aucun original n'a été renommé.

### K.2 Copie de l'application

| Contrôle | Résultat |
|---|---|
| Destination | `C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI` |
| Fichiers attendus | 47 |
| Fichiers présents | 47 |
| SHA256 identiques | 47 |
| Fichiers altérés | 0 |
| Fichiers manquants | 0 |
| Fichiers en trop | 0 |
| Empreinte globale du dossier copié | `76233EB66A3161B4E06F76B92A49F31DB59656EF37CA0D6FD22F6A204B8BA5F9` |
| Structure racine | `src\`, `backend\`, `docs\`, 14 fichiers à la racine |

Incident corrigé : le premier `Copy-Item` a créé un niveau de dossier supplémentaire (`HORIZON_LOCAL_AI\HORIZON_LOCAL_AI`). La copie a été remontée d'un niveau par déplacement de mon propre artefact, puis le dossier vide supprimé. L'original sur le Bureau n'a pas été touché.

### K.3 Non-régression des originaux

| Contrôle | Résultat |
|---|---|
| Application du Bureau | 47 fichiers, inchangés |
| 5 fichiers `.bak` | SHA256 identiques à l'audit du 07/11 (559341DFEA65, 1C851353853A, 78F21ED360BA, AD5A2A41C24D, C45BAD613A36) |
| 10 archives `.zip` | Tailles et empreintes inchangées |
| Racine | 120 fichiers après opération (73 fichiers d'origine + 47 fichiers copiés) |

### K.4 Fichiers créés par cette phase

| Fichier | Octets |
|---|---|
| `07_AUDIT_CLASSEMENT\RAPPORT_AUDIT_COMPLET_2026-11-08.md` | 22 238 |
| `07_AUDIT_CLASSEMENT\COMPARAISON_6_INTERFACES.csv` | 2 073 |
| `07_AUDIT_CLASSEMENT\COMPARAISON_VERSIONS.csv` | 979 |
| `07_AUDIT_CLASSEMENT\DOUBLONS_EXACTS_CORRIGE.csv` | 1 698 |
| `07_AUDIT_CLASSEMENT\INVENTAIRE_APPLICATION_47_FICHIERS.csv` | 5 007 |
| `03 MÉMOIRE LOCALE\07_SAUVEGARDES\HORIZON_RACINE_2026-11-08.zip` | 684 541 |
| `03 MÉMOIRE LOCALE\07_SAUVEGARDES\HORIZON_APP_BUREAU_2026-11-08.zip` | 59 126 |
| `02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI\` (47 fichiers) | 0,14 Mo |

Aucun fichier existant n'a été supprimé, déplacé, renommé ou modifié. Aucune archive originale n'a été extraite ni réécrite.

### K.5 Blocages et points en suspens

1. **Deux versions de `Architecture_Generale.md`** coexistent (585 o et 495 o). Décision documentaire non prise, les deux sont conservées.
2. **Aucune installation de dépendances** n'a été faite, conformément aux consignes. Le build TypeScript/Vite et l'exécution du backend ne sont donc pas vérifiés à ce stade.
3. **Absence de lockfile** dans l'application : point à traiter avant tout `npm install`.
4. **4 versions intermédiaires** (v0.3, v0.4, v0.6, v0.7) citées par le README mais introuvables.
