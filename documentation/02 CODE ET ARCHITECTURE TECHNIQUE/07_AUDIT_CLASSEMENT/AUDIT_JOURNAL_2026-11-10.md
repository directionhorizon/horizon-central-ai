# HORIZON CENTRAL AI — Journal d'exécution de l'audit et du plan de migration

**Date d'ouverture :** 2026-11-10
**Référentiel :** Politique de gouvernance des données v0.4 (10 nov. 2026)
**Règle d'exécution :** aucune migration, aucune modification métier, aucune suppression avant audit clos, sauvegardes vérifiées et validation explicite.

---

## 1. Cadrage (PHASE 1) — éléments constatés

| Élément | Constat | Preuve |
|---|---|---|
| Racine projet | `C:\Users\hp\HORIZON LOCAL AI` | dossier présent |
| Piliers | 01 FONCTIONNEMENT · 02 CODE ET ARCHITECTURE TECHNIQUE · 03 MÉMOIRE LOCALE · 04 MÉMOIRE EN LIGNE | listage |
| Dépôt de code | `02_CODE_SOURCE\HORIZON_LOCAL_AI` | dossier présent |
| Arborescence d'architecture | `01_ARCHITECTURE`, `02_CODE_SOURCE`, `03_MODULES`, `04_INTEGRATIONS`, `05_CONFIGURATION`, `06 ARCHIVES`, `06_TESTS`, `07_AUDIT_CLASSEMENT`, `07_PLANIFICATION`, `Architecture_Generale.md` | listage |
| Politique v0.4 | **présente** (pièce jointe de session, 15,5 Ko) — **absente de l'arborescence projet** | lecture intégrale |
| Dépôt Git | **AUCUN** (`fatal: not a git repository` sur les 3 niveaux testés) | `git rev-parse` |
| Fichiers de secrets | **aucun `.env` réel** ; seulement `backend\.env.example` et `.env.example` | listage + noms de clés uniquement |
| Clés Supabase | **absentes** de l'environnement (`HORIZON_SUPABASE_URL`/`_KEY` non définies) | booléens |
| GitHub CLI | **absent** (`gh` non reconnu) | `Get-Command gh` |
| RustDesk | 3 processus `rustdesk` actifs — **session avec le Production Workstation non prouvée** | `Get-Process` |
| Base locale | `backend\data\horizon.db` — 196 Ko, modifiée le 2026-11-09 18:44 | `Get-Item` |
| Archives | 6 `.md` de 336–509 octets (6–13 lignes : esquisses, pas des documents complets) + 10 archives ZIP (50–81 Ko) | `Get-ChildItem` + comptage de lignes |
| Espace disque | **C: 0,4 Go libres / 100 Go** — **D: 69,6 Go libres / 132,5 Go** | `Win32_LogicalDisk` |
| Volumétrie | 01 FONCTIONNEMENT : 17 fichiers · 02 CODE : 33 452 fichiers / 387,8 Mo · 03 MÉMOIRE LOCALE : 10 fichiers / 0,7 Mo · 04 MÉMOIRE EN LIGNE : 9 fichiers | comptage récursif |

### Anomalies relevées (à instruire, sans rien supprimer)
1. Six documents d'architecture de `06 ARCHIVES` sont des **esquisses** (336 à 509 octets, 6 à 13 lignes) : `Architecture_Generale_avant_fusion.md`, `Architecture_Logicielle.md`, `Composants_Modules.md`, `Environnement_Windows.md`, `Integrations_API.md`, `Plan_Implementation.md`. Ils ne contiennent pas l'architecture détaillée annoncée : **à reconstituer ou à déclarer obsolètes**, sans les supprimer.
2. Aucune version de la politique v0.4 dans le projet : elle doit avoir une source officielle unique (dépôt de gouvernance), conformément au §15 de la politique.
3. **C: ne dispose que de 0,4 Go libres.** Toute sauvegarde ou export de migration doit être écrit sur **D: (69,6 Go libres)** ou un support externe. Aucune migration ne doit démarrer sans cette destination validée.

---

## 2. Tableau de suivi des phases

| Phase | Objet | Statut | Blocage / preuve |
|---|---|---|---|
| 1 | Cadrage, accès, blocages | **Terminé — à valider** | ce document |
| 2 | Audit Strategy Workstation (local, lecture seule) | **EXÉCUTÉE** | §8, §10.2, §10.3 — preuves mesurées le 2026-11-10 |
| 3 | Audit Production Workstation (RustDesk) | **BLOQUÉ** | session RustDesk non confirmée/autorisation requise |
| 4 | Consolidation, classification, plan de migration | À faire | dépend de 2 et 3 |
| 5 | Validation des architectures cibles | **BLOQUÉ partiellement** | Supabase : aucune clé ; GitHub : aucun dépôt/gh ; Drive : non vérifié |
| 6 | Sauvegardes et vérification | À faire | nécessite autorisation explicite |
| 7 | Migration Supabase | **BLOQUÉ** | `HORIZON_SUPABASE_URL` / `HORIZON_SUPABASE_KEY` absentes |
| 8 | Migration GitHub | **BLOQUÉ** | aucun dépôt Git local, `gh` absent, aucun compte vérifié |
| 9 | Migration Google Drive | **BLOQUÉ** | accès Drive non vérifié |
| 10 | Vérification croisée et registre | À faire | dépend de 7–9 |
| 11 | Évolutions backend | À faire | après audits + validation |
| 12 | Catalyseur projets inter-systèmes | À faire | après 11 |
| 13 | Catalogue des skills | À faire | audit préalable obligatoire |
| 14 | Finitions visuelles | À faire | après backend validé |
| 15 | Contrôle final et clôture | À faire | — |

---

## 3. Règles appliquées dès maintenant

- Lecture seule sur les sources ; aucune suppression, aucun déplacement.
- Aucun secret affiché, copié ou journalisé : seuls la présence et le nom des variables sont consignés.
- Aucune base Supabase, aucun dépôt GitHub, aucun espace Drive créés sans architecture validée.
- Une sauvegarde n'est déclarée utile qu'après vérification d'intégrité **et** de restauration.
- Toute action destructive, changement de droits ou bascule de production exige une validation explicite.

---

## 4. Décisions attendues de l'utilisateur

1. **RustDesk** : confirmer qu'une session vers le Production Workstation est ouverte et autorisée, et confirmer le périmètre GAMEFORGE / KING OF THE FOREST.
2. **Supabase** : fournir un projet et les variables d'environnement (côté serveur uniquement) *ou* autoriser l'audit sans migration.
3. **GitHub** : confirmer le compte/organisation cible et si l'installation de `gh` est autorisée (ou fournir un accès alternatif).
4. **Google Drive** : confirmer le compte et le point de montage/synchronisation local.
5. **Fichiers 0 Ko** : indiquer s'ils doivent être reconstitués depuis les ZIP ou considérés comme obsolètes.

---

## 6. Étendue réelle des accès (vérifiée le 2026-11-10)

Accès obtenus par autorisation déléguée (aucune clé saisie, aucun secret journalisé).

| Plateforme | Compte | Étendue constatée | Observation |
|---|---|---|---|
| **Supabase** | compte lié (`ca_KtHLn72Lxkk6`) | **1 projet** : `nzila-crm` (ref `ymqdmfsqtkmlmwffqskt`, eu-central-1, Postgres 17.6, `ACTIVE_HEALTHY`) | Aucun projet nommé « mayela » : le nom diffère — **à confirmer** |
| **GitHub** | `directionhorizon` (compte personnel, **pas d'organisation**) | **4 dépôts**, droits admin : `horizon-ai-core` (privé, Python, 4 Ko), `mayela-crm` (privé, HTML, 2 178 Ko), `Event-light` (public, vide), `THE100TRAL` (public, Kotlin) | Aucun dépôt de gouvernance ni de système ; l'accès n'est pas limité à un dépôt |
| **Google Drive** | `direction.horizon.cg@gmail.com` | Drive complet du compte ; racine thématique : `MES RESEAUX SOCIAUX`, `USAGE PERSONNEL`, `MON PREMIER PROJET HORIZON` (contenant `SYSTEME D'AUTOMATISATION DU PROJET`, `WEBINAR PROSPECTION 03.08.2026`…) | Aucune arborescence `HORIZON/système/projet` : à créer, pas à migrer telle quelle |

### Constats à instruire
1. **Divergence de nom** : Supabase `nzila-crm` vs GitHub `mayela-crm`. Un même projet doit avoir une identité unique et traçable (§7). Confirmer s'il s'agit du même produit, d'un renommage ou de deux projets distincts.
2. **`horizon-ai-core` existe sur GitHub (4 Ko) mais aucun dépôt Git local** : le code local n'est relié à aucun historique. Divergence à résoudre avant toute publication.
3. **Aucune structure cible** (dépôt de gouvernance, dépôts système, espaces Drive par système) : création soumise à validation.
4. **Compte GitHub personnel** : une future organisation sera nécessaire pour les dépôts système/partagés (§3.2), ou une justification explicite pour rester en compte personnel.

## 7. Décisions appliquées et chronologie reconstituée (2026-11-10)

### 7.1 Renommage Supabase — EXÉCUTÉ
- Projet `nzila-crm` → **`mayela-crm`** (id `40029531`, ref `ymqdmfsqtkmlmwffqskt`).
- **Le `ref` est inchangé** → URL, clés, chaînes de connexion de l'app MAYELA **non impactées**. Aucune rotation, aucune coupure.
- Motif : l'identité du projet doit être unique et traçable (§7) ; l'ancien nom était un oubli de renommage, confirmé par le responsable.

### 7.2 `horizon-ai-core` — nature réelle constatée (lecture seule)
6 fichiers, aucune logique métier :
`.env.example` (33 o) · `.gitignore` (83 o) · `README.md` (828 o) · `main.py` (1 509 o) · `render.yaml` (321 o) · `requirements.txt` (44 o).
→ Ce n'est pas « HORIZON », c'est une **amorce de déploiement cloud** (Render) d'un service vide. Créée le 2026-11-02, soit **avant** la politique v0.4 (2026-11-10) et avant tout cœur fonctionnel.
→ Conséquence de gouvernance : un artefact ambigu ne doit pas devenir la cible du vrai code par défaut. **Statut à statuer** (conserver figé / archiver en lecture / devenir cible ultérieure). Non supprimé.
→ Signal pilier 04 (mémoire en ligne) : `render.yaml` implique une intention de déploiement hors local, non couverte par la politique actuelle.

### 7.3 Chronologie reconstituée à partir des traces
| Date | Trace | Lecture |
|---|---|---|
| 2026-07-14 | Drive `MON PREMIER PROJET HORIZON` > `SYSTEME D'AUTOMATISATION DU PROJET` | L'intention « système » précède le code |
| 2026-07 → 08 | Interfaces MagicPath (Workbench, Control Center, Model Manager, System Monitor, Knowledge HUB, Agents Catalog) | La maquette précède l'implémentation |
| 2026-10-21 | `mayela-crm` — dernier push | Le seul projet produisant de la valeur réelle |
| 2026-11-02 | `horizon-ai-core` — coquille de déploiement | Tentative de « mise en ligne » avant cœur fonctionnel |
| 2026-11-07 | Release locale 1.0.0 + `SOURCE_MANIFEST.json` | Première consolidation locale |
| 2026-11-09/10 | Refonte UI workspace, intégrations, privacy, **politique v0.4** | La règle arrive après les artefacts |

**Conclusion** : HORIZON CENTRAL AI est l'app hybride d'assistance et de supervision (prototype local, backend v0.4.0) ; **HORIZON** est le nom abstrait de référence de l'entreprise future, qui portera plusieurs projets. MAYELA est le premier projet réel et **son système responsable est identifié : le système d'orchestration existant dans Hermès**, candidat n°1 à l'intégration comme premier système supervisé. La politique v0.4 étant postérieure aux artefacts, elle doit être appliquée **rétroactivement** (classer l'existant), pas seulement au futur.

### 7.4 Écarts de gouvernance constatés (à instruire)
1. **Système responsable de MAYELA : désigné, non opérationnel.** Le système d'orchestration Hermès est nommé responsable, mais il n'est **pas encore intégré** dans HORIZON CENTRAL AI → responsabilité *déclarée*, capacité de supervision *non vérifiée*. Ne pas confondre les deux dans le registre. Statut à porter : « responsable désigné — intégration en attente ».
2. **Aucune source autoritaire déclarée** par projet (DB ? code ? média ?).
3. **Aucune convention de nommage** : `mayela-crm` (produit), systèmes, gouvernance — à formaliser.
4. **Aucun historique Git local** → tout classement resterait irréversible.
5. **Risque de publication massive** : 387,8 Mo / 33 452 fichiers, dont `node_modules`, `.venv`, `dist` ; `.gitignore` de `horizon-ai-core` = 83 o, très insuffisant ; `.env` présent en local → fuite possible si envoi brut.

### 7.5 Prochaine action
**PHASE 2 — audit local lecture seule** : inventaire, classement, registre systèmes/projets, cartographie backend/skills, détection doublons/orphelins, scan de *présence* de secrets. Aucune écriture hors projet local, aucune migration.

## 8. Phase 2 — audit local lecture seule (exécuté 2026-11-10)

### 8.1 Localisation réelle — trois copies divergentes (CONSTAT CRITIQUE)
| # | Chemin | `src/App.tsx` | Nature |
|---|---|---|---|
| **A** | `C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI` | **8 970 o** — 09/11 18:50 | **source de travail réelle** |
| B | `C:\Users\hp\Desktop\HORIZON_TEST_1.0.0\HORIZON_LOCAL_AI` | 2 452 o — 07/11 19:33 | export figé 1.0.0, 33 fichiers |
| C | `C:\Users\hp\Desktop\Nouveau dossier\HORIZON_LOCAL_AI_Interfaces_Integration` | 2 452 o — 07/11 19:19 | archive antérieure |

- B et C ne contiennent **ni `backend/horizon/`, ni base, ni l'UI du 09/11** : ce sont des états antérieurs, pas le projet.
- Le référentiel de projet désignait B comme « projet » : **écart de référentiel**, corrigé ici. Aucun fichier supprimé ni déplacé.
- À valider : déclarer **A = source de travail**, **B et C = archives** (statut explicite, pas de suppression).

### 8.2 Inventaire de A
- `node_modules` : **32 241 fichiers / 366,7 Mo** (93 % du volume) → exclu de toute publication.
- `backend` 1 059 fichiers / 18,1 Mo · `src` 63 fichiers / 0,4 Mo · `docs` 16 fichiers / 0,8 Mo · `dist` 3 fichiers / 0,5 Mo.
- `backend/horizon/` : 12 modules (`auth`, `connectivity`, `core`, `db`, `llm`, `metrics`, `models`, `schema` 12 442 o, `sync_engine`, `sync_provider`, `sync_worker`) + **7 repositories** + **13 routers** + `tools/export_snapshot.py`.
- Base locale : `backend\data\horizon.db` **196 Ko** + snapshot JSON 15,2 Ko (09/11 15:55).
- **Aucun fichier `.env`** : seulement 2 `.env.example` (380 o / 1 840 o) → **aucun secret en clair sur disque**, mode local-only par défaut.

### 8.3 Rédundances constatées (à traiter — aucune suppression sans décision)
- `LLMSelector.tsx` **×4**, tous 3 936 o (agents-tools-catalog, knowledge-memory-hub, main-workbench, model-manager) → doublons stricts.
- `SystemHeader.tsx` **×3**, tous 2 535 o → doublons stricts.
- `SideNav.tsx` **×4** (2 461 / 2 794 / 2 927 / 2 927 o) → 2 doublons stricts + 2 variantes.
- 3 paires « Live / statique » : `ModelManager` (15 410 / 17 641), `SystemMonitor` (8 978 / 9 486), `KnowledgeMemoryHub` (13 511 / 12 187).
- Monolithes : `Cockpit.tsx` **37 939 o**, `src/index.css` **47 337 o**.
→ **63 fichiers `src` pour ~40 contenus distincts.**

### 8.4 État du build — VÉRIFIÉ (item clos)
`_tsc.log` = **0 octet** (aucun diagnostic) · `_vite.log` = « ✓ built in 15.86s », 2 118 modules · `dist/` produit (index.html 0,56 kB, css 99,70 kB, js 455,16 kB).
→ `npm run build` **réussi, 0 erreur TypeScript**. La crainte d'erreurs TS non résolues est levée.

### 8.5 Journaux à la racine du projet (à classer vers `03 MÉMOIRE LOCALE\05_JOURNAUX`)
`_build_p8.log` 91 o · `_tsc.log` 0 o · `_vite.log` 1 048 o · `backend_out.log` **136 023 o** · `backend_err.log`, `offline_*`, `worker_*` (202–416 o) · `data/uvicorn.log` 3 488 o.
→ Aucun secret attendu, mais `backend_out.log` est volumineux : à inspecter avant tout envoi ou archivage.

### 8.6 Suite immédiate
Classification A/B/C + registre systèmes/projets, puis **étape 2 du §12 : audit Production Workstation via RustDesk**, périmètre à confirmer (GAMEFORGE / KING OF THE FOREST). **Aucune modification backend sans annonce préalable.**

## 9. Modèle d'entités — référence (correction de ma formulation)

La politique distingue **propriété métier** (le projet), **responsabilité opérationnelle** (le système) et **droit de supervision** (HORIZON CORE) — §4. Ma note du §7.4 était ambiguë : le tableau ci-dessous fait référence.

| Niveau | Entité | État réel | Nature |
|---|---|---|---|
| Supervision | **HORIZON CENTRAL AI** | prototype local v0.4.0 | **application** hybride d'assistance ; coordonne et supervise les systèmes, ne les remplace pas |
| Système | **Système d'orchestration existant dans Hermès** | **existant**, non intégré — candidat n°1 | système d'orchestration |
| Projet | **MAYELA CRM** | app en ligne (Supabase `mayela-crm`, GitHub `mayela-crm`) | **projet** (une app) |
| Système | **GAMEFORGE** | **conceptualisé, non mis sur pied** — à créer dans HORIZON CENTRAL AI | système d'orchestration |
| Projet | **KING OF THE FOREST** | jeu vidéo, fichiers à inventorier sur la Production Workstation | **projet** (un jeu) |

**Règles à ne plus confondre :**
- MAYELA CRM **n'est pas** le système Hermès ; elle est le projet dont ce système a la responsabilité.
- GAMEFORGE **n'est pas** KING OF THE FOREST ; c'est le système responsable de ce projet.
- GAMEFORGE n'existe pas encore → **aucun audit fonctionnel possible**. Seul un inventaire des fichiers du projet KING OF THE FOREST est pertinent aujourd'hui.
- Un système peut exister sans être intégré (Hermès) ; un système peut être conceptualisé sans exister (GAMEFORGE). Ces deux états doivent apparaître distinctement dans le registre.
- HORIZON CENTRAL AI ne devient pas « responsable » d'un projet : elle supervise le système qui l'est.

### 9.1 Nettoyage disque C: — exécuté sous ma responsabilité
Suppression des 4 profils Edge créés par mes outils de diagnostic (`_hz_desktop_profile`, `_hz_measure_profile`, `_hz_ovf_profile`, `_hz_txt_profile`) sous `C:\Users\hp\AppData\Local\Cline`. Aucun lien avec le projet. Les profils verrouillés par un processus Edge en cours sont conservés.

### 9.2 Principe d'architecture reçu le 10 novembre (décision humaine)

> **La responsabilité opérationnelle est portée par l'AGENT ORCHESTRATEUR du système, pas par le système en tant qu'entité abstraite.**

Conséquences retenues, à porter dans le backend (aucune modification effectuée) :
- le **système** est l'environnement d'exécution ; l'**agent orchestrateur** est le sujet responsable ;
- toute écriture doit porter un auteur identifiable (agent ou humain) — jamais « le système » ;
- les permissions s'attachent à l'**agent**, pas au système ni au projet global ;
- un seul **agent responsable actif** par projet ; les autres agents sont contributeurs avec périmètre limité ;
- HORIZON CENTRAL AI **supervise** des agents responsables, elle n'est jamais responsable d'un projet ;
- distinction obligatoire dans le registre : *responsable désigné* vs *agent opérationnel vérifié*.

Document de référence créé : `01_ARCHITECTURE\Architecture_Responsabilite_Orchestrateur.md`
(principe, modèle organisationnel, conséquences backend, 6 propositions, 5 points à valider).

### 9.3 Lecture corrigée des deux projets

| | MAYELA CRM | KING OF THE FOREST |
|---|---|---|
| Nature | projet (unité métier) | projet (unité métier) |
| Système responsable | système d'orchestration **existant dans Hermès** | **GAMEFORGE** — conceptualisé, **non créé** |
| Agent responsable | **l'Orchestrateur** (nom de l'agent) | **inexistant** — GAMEFORGE n'est pas créé |
| Statut de gouvernance | désigné (système), agent non identifié | **sans système ni agent responsable** |
| Intégration HORIZON CENTRAL AI | en attente, candidat n°1 | non planifiée |

Point de gouvernance nouveau : KOF **ne peut pas** être déclaré « projet partagé » (§5) ni recevoir
d'agents contributeurs avant l'existence d'un agent responsable. La création de GAMEFORGE est un
**prérequis**, pas une conséquence.

### 9.4 Nature du principe — précision du 10/11/2026
Le principe « la responsabilité opérationnelle est portée par l'agent orchestrateur, pas par le système »
a une **double portée** explicitement confirmée :
- **principe d'architecture** → modèle d'entités, attribution d'auteur, permissions par agent, API ;
- **principe de gouvernance des données** → classification, métadonnées, provenance, conservation,
  clôture, sauvegarde, traçabilité : chaque acte de gouvernance est imputable à un agent nommé.

Corollaire retenu : *une donnée dont l'agent auteur (ou l'humain auteur) ne peut pas être nommé est une
donnée non gouvernée, même correctement stockée.*

Emplacement : `01_ARCHITECTURE\Architecture_Responsabilite_Orchestrateur.md` §1.1 (tableau de
déclinaison sur §4, §5, §7, §8, §9, §10, §11, §14).
La politique v0.4 **n'a pas été modifiée** : ce principe la décline, il ne la remplace pas.

### 9.5 Audit distant — outil prêt et testé
`AUDIT_DISTANT_KING_OF_THE_FOREST.ps1` : lecture seule, paramètres `-Days`, `-Roots`, `-OutFile`.
- Syntaxe validée (parseur PowerShell : 0 erreur, encodage UTF-8 avec BOM).
- **Exécution réelle de bout en bout** sur périmètre borné : 19 fichiers, CSV généré, aucune écriture hors rapport.
- À exécuter sur la **Production Workstation** (RustDesk) pour l'inventaire réel du projet KING OF THE FOREST.

### 9.6 Catalogue des skills v0.3 reçu — cartographie backend réalisée
Corrections apportées (décision humaine du 10/11/2026) :
- l'agent responsable du système Hermès **s'appelle « Orchestrateur »** — ce n'est pas « l'agent de MAYELA » ;
- **MAYELA CRM n'est pas la condition sine qua non** de ce système : le système existe indépendamment,
  MAYELA est une **affectation parmi d'autres**. Un système sans projet reste valide ; un projet sans
  orchestrateur affecté n'a pas de responsable opérationnel ;
- métaphore validée (catalogue §2.1) : HORIZON CENTRAL AI est un **groupe**, chaque système une entité
  opérationnelle, son **Orchestrateur en est le directeur général**, sans diriger le groupe.

Livrable : `03_MODULES\CARTOGRAPHIE_SKILLS_v0.3_BACKEND_2026-11-10.md`.

**Découverte majeure** : le backend contient déjà la bonne *forme* du principe —
`orchestrators` (entité), `orchestrator_projects(orchestrator_id, project_id, role)` (affectation),
`orchestrator_capabilities`, et `operation_log(actor, action, target_type, target_id, result, detail)`
(auteur tracé). Il ne manque pas une abstraction : il manque la **sémantique** (`role='responsable'`
unique au lieu de `member`, auteur rattaché aux ressources).

**Bilan honnête** : 30 capacités examinées — 1 vérifiée (4.19 journalisation), 12 partielles, 16 absentes, 1 à vérifier.
Aucun skill n'existe au sens du catalogue (contrat entrée/sortie, responsable, tests) : ce qui existe est
de l'**infrastructure de registre**, pas de la **capacité de gouvernance**.

### 10.1 Étape 3 du §12 exécutée — consolidation et classification
Périmètre : `C:\Users\hp\HORIZON LOCAL AI`, hors `node_modules`/`.venv`/`__pycache__`/`dist`/`.git`.
**241 fichiers / 3,6 Mo** — 02 CODE 204, 01 FONCTIONNEMENT 17, 03 MÉMOIRE 10, 04 MÉMOIRE 9, racine 1.
Livrables : `INVENTAIRE_CONSOLIDE_2026-11-10.csv` (241 lignes) et `CLASSIFICATION_CORPUS_2026-11-10.md`.

**Découvertes qui changent la lecture :**
1. `06 ARCHIVES\DOCUMENTS_HISTORIQUES` ne contient **aucune version antérieure** : 5 des 6 fichiers sont
   identiques octet pour octet à des documents **encore vivants**. L'archive documentaire est vide de
   valeur historique tout en donnant l'illusion du contraire.
2. `01 FONCTIONNEMENT` existe en **trois versions par document** : coquille en racine (440–630 o), version
   réelle en sous-dossier (1 601–3 169 o), résidu `.bak` (226–616 o). La version riche est la moins visible.
3. `SystemHeader.tsx` est dupliqué **×4** (2 535 o) — le comptage MD5 corrige l'estimation antérieure de 3.
   `LLMSelector.tsx` ×4 (3 936 o) confirmé.
4. `.clinerules.md` est un **DOSSIER** contenant `HORIZON_TOKEN_OPTIMIZATION.md`, identique au fichier
   `.clinerules` → la règle « optimisation de tokens » **n'est pas chargée** comme règle projet.
5. `avant-cockpit.png` et `apres-cockpit.png` ont la **même empreinte** : la preuve visuelle avant/après
   n'existe pas. Aucune affirmation de comparaison ne peut s'appuyer dessus.
6. **26 fichiers** (1 base `.db`, 13 journaux, 12 archives) ne doivent jamais entrer dans un dépôt de code.

Le pilier 01 ne fait que 17 fichiers et le pilier 04 en fait 9 : la **mémoire en ligne n'est pas encore
documentée**, ce qui est cohérent avec l'absence de connecteurs réels.

### 10.2 Étape 5 du §12 — sauvegarde vérifiée (exécutée)
Destination : `D:\HORIZON_BACKUP_2026-11-10` (D: disposait de 69,6 Go ; C: n'a que 0,41 Go libres).
Périmètre : 243 fichiers / 3,68 Mo — exclut `node_modules`, `.venv`, `__pycache__`, `dist`, `.git`
(dossiers reconstruits, non conservés).

| Contrôle | Résultat |
|---|---|
| Copie | `robocopy /E` code de sortie 1 (succès : 0–7) |
| Comparaison SHA256 source ⇄ copie | **243 / 243 identiques, 0 écart** |
| Manifeste | `_MANIFESTE_SHA256.csv` écrit dans la sauvegarde (chemin, taille, empreinte) |
| Test de restauration | `schema.py` restauré dans un dossier temporaire → **identique SHA256**, puis temporaire supprimé |

La sauvegarde est donc **vérifiée et restaurable** au sens du §10 — pas seulement « existante ».
Limite explicite : elle ne couvre **pas** `node_modules` (reconstructible par `npm install`) ni `.venv`.
Une seconde copie indépendante des plateformes (§10) reste à prévoir : elle n'existe pas encore.

### 10.3 Supabase — inventaire lecture seule (prérequis migration, exécuté)
Projet `mayela-crm` (ref `ymqdmfsqtkmlmwffqskt`, eu-central-1, ACTIVE_HEALTHY).

| Élément | Constat |
|---|---|
| Schémas | **8** · **76 tables** · 3 vues |
| `Schema privé` (nom littéral, avec espace) | 6 tables : BASE PROSPECTS EVENTS, BD PROSPECTS ACTIONS, BD PROSPECTS FACEBOOK, **BD PROSPECTS MAPS (205 lignes, 40 Ko)**, BD PROSPECTS SUIVI, BD PROSPECTS TIKTOK |
| `public` | 424 Ko — `social_*`, `tasks`, `tik_*` + 3 vues : `horizon_leads_cross_channel_duplicates`, `social_accounts_safe`, `v_campaign_spend` |
| `storage` | 1 bucket, **4 objets** |
| `supabase_migrations` | **19** migrations appliquées |

**Constat 1 — volume négligeable, normalisation lourde.** La base entière pèse moins de 500 Ko.
Une « migration Supabase » n'est donc pas un transfert de masse : c'est une **normalisation**. Les
identifiants actuels sont incompatibles avec une architecture cible propre :
- schéma nommé **« Schema privé »** (espace + mot français) au lieu d'un identifiant technique ;
- tables nommées **avec des espaces** (« BD PROSPECTS MAPS »), donc à quoter systématiquement ;
- aucune colonne `project_id` visible dans les noms de tables : l'isolation par projet (§3.1) n'est pas
  démontrable en l'état.

**Constat 2 — un artefact HORIZON est déjà dans `public`** : la vue `horizon_leads_cross_channel_duplicates`.
Du « horizon » préexiste donc dans le projet avant toute gouvernance : à recenser, pas à dupliquer.

**Constat 3 — limite d'outillage.** `SUPABASE_GET_TABLE_SCHEMAS` n'adresse que le schéma `public` et
échoue sur les noms avec espaces. L'inventaire **colonne par colonne** du schéma privé exige une requête
SQL directe : ce n'est pas disponible ici, et je ne le simule pas.

### 10.4 État des migrations — AUCUNE EXÉCUTION
Étapes 6 (Supabase), 7 (GitHub), 8 (Drive) : **non engagées**. Prérequis du §12 : audit distant manquant
(étape 2), validation des cibles manquante (étape 4). Aucune écriture, aucun `APPLY_A_MIGRATION`, aucun
transfert, aucune création de dépôt.

## 5. Prochaine action

Démarrer la **PHASE 2** (audit Strategy Workstation, lecture seule) sans attendre les accès distants, puisqu'elle ne dépend pas de RustDesk, Supabase ni GitHub.
