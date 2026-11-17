# HORIZON LOCAL AI — ARBITRAGE ARCHITECTURAL CONSOLIDÉ

Date : 2026-11-09
Source : `07_AUDIT_CLASSEMENT\CARTOGRAPHIE_FONCTIONNELLE_HORIZON_2026-11-09.md`
Nature : **analyse seule**. Aucun fichier source modifié, aucun code généré, aucune installation, aucun compte connecté, aucune dépense engagée. Seul ce rapport est écrit.

## 0. Faits techniques mesurés pour cet arbitrage

Ces mesures conditionnent plusieurs décisions. Elles ont été relevées sur la machine cible.

| Mesure | Valeur | Impact sur les décisions |
|---|---|---|
| Espace libre sur `C:` | **64 Mo** sur 102 401 Mo (0,06 %) | Un modèle local est matériellement impossible sans libération d'espace |
| RAM totale / libre | **7,8 Go** / 1,5 Go | Un modèle local de taille utile (7B+) ne tiendrait pas avec le reste |
| `ollama` dans le PATH | **absent** | — |
| `llama-server` dans le PATH | **absent** | — |
| LM Studio dans le PATH | **absent** | — |
| Port 11434 (Ollama) en écoute | **0 connexion** | Aucun runtime local actif |
| Dépôt Git (`.git`) à la racine ou dans l'app | **aucun** | La synchronisation GitHub est impossible en l'état |
| `backend/.env.example` | contient déjà `HORIZON_LLM_BASE_URL`, `HORIZON_LLM_API_KEY`, `HORIZON_LLM_MODEL` | Le backend est déjà conçu pour un fournisseur **OpenAI-compatible générique** |
| `docs/contracts/capabilities.example.json` | 5 capacités déclarées | Modèle de statut déjà posé |

**Conséquence immédiate :** la vision « modèles locaux » reste un objectif de conception, mais **elle n'est pas exécutable sur cette machine aujourd'hui**. Toute recommandation doit le refléter sans l'inventer.

---

## A. TABLEAU DES NEUF DÉCISIONS

### DÉC-1 — Données de démonstration

| Colonne | Contenu |
|---|---|
| **Options** | (a) conserver en les marquant « DEMO » ; (b) retirer les valeurs fictives et afficher un état vide explicite ; (c) conserver sans marquage (statu quo) |
| **Recommandation** | **(a) conserver avec marquage explicite « DEMO / non connecté »**, puis basculer vers (b) page par page au fur et à mesure de leur raccordement réel |
| **Justification** | Retirer immédiatement les données (b) détruirait l'intérêt visuel de 4 pages sans rien apporter fonctionnellement, et violerait la consigne « ne pas reconstruire les interfaces ». Le statu quo (c) est inacceptable : le rapport de cartographie a prouvé que ces valeurs sont présentées comme réelles (latences 42/318 ms, CPU 34 %, GPU 71 %). Le marquage (a) préserve le design, supprime l'ambiguïté et prépare le raccordement. |
| **Risques** | Faible. Un marquage insuffisamment visible recréerait la confusion. Le marquage doit être textuel, pas seulement chromatique. |
| **Dépendances** | Aucune. Peut être appliqué indépendamment des 8 autres décisions. |

### DÉC-2 — Stockage des nouvelles entités

| Colonne | Contenu |
|---|---|
| **Options** | (a) même base SQLite `horizon.db` ; (b) base SQLite séparée par domaine ; (c) base serveur (PostgreSQL) |
| **Recommandation** | **(a) même base SQLite, mais avec des modules de code séparés par domaine** |
| **Justification** | Le volume visé (projets, missions, orchestrateurs, documents) reste dans l'ordre de quelques dizaines de milliers de lignes — très en deçà des limites pratiques de SQLite. Une base unique préserve la simplicité de déploiement (un fichier, sauvegarde ZIP déjà en place) et la transactionnalité entre entités liées. Le découpage demandé par la vision est un découpage de **modules et de contrats**, pas de fichiers de base. Une base séparée (b) multiplierait les sauvegardes et les incohérences ; PostgreSQL (c) impose un service supplémentaire sur une machine à 64 Mo libres. |
| **Risques** | Le monolithe de code actuel (`app.py`, 137 lignes) doit être découpé en modules pour que cette décision ne devienne pas un nouveau point de blocage. |
| **Dépendances** | Liée à DÉC-5 (une sécurité multi-utilisateur imposerait des tables d'identité, pas une base séparée) et à DÉC-9 (une entité Projet en base s'y ajoute naturellement). |

### DÉC-3 — Contrat API : `accepted_no_model` vs `completed`

| Colonne | Contenu |
|---|---|
| **Options** | (a) aligner le contrat sur le code (`accepted_no_model` conservé) ; (b) aligner le code sur le contrat (`completed`) ; (c) conserver les deux : `accepted_no_model` quand aucun modèle, `completed` quand un modèle a répondu |
| **Recommandation** | **(c) conserver les deux états**, et mettre à jour le document de contrat pour les déclarer explicitement |
| **Justification** | L'état `accepted_no_model` n'est pas un défaut : c'est une garantie anti-hallucination validée par les tests réels. Le supprimer (b) reviendrait à autoriser une réponse `completed` sans modèle, ce qui contredit le principe « ne jamais fabriquer une réponse assistant de succès ». Le figer (a) empêcherait tout branchement LLM futur. La solution (c) préserve la garantie et ouvre la voie : `accepted_no_model` reste l'état par défaut sans fournisseur, `completed` devient possible uniquement après une exécution réelle. Le contrat v0.1 doit être corrigé, pas le code. |
| **Risques** | Le champ `citations` prévu au contrat n'existe pas ; il doit être soit ajouté, soit déclaré optionnel. Le document actuel décrit un état cible, pas l'état réel : il doit être daté et marqué « cible ». |
| **Dépendances** | Directe avec DÉC-4 (sans fournisseur, `completed` n'a aucun sens) et avec DÉC-8 (le service de planification devra produire des statuts). |

### DÉC-4 — Premier fournisseur LLM

| Colonne | Contenu |
|---|---|
| **Options** | (a) Ollama local ; (b) fournisseur distant OpenAI-compatible ; (c) service local plus léger (llama.cpp / LM Studio) ; (d) aucun fournisseur pour l'instant, uniquement l'adaptateur |
| **Recommandation** | **(d) puis (b)** : construire d'abord l'**adaptateur OpenAI-compatible générique**, sans choisir de fournisseur ; brancher ensuite un fournisseur **distant OpenAI-compatible**, le premier étant un **choix stratégique de l'utilisateur** (coût). **(a) Ollama est écarté sur cette machine** (64 Mo libres, 1,5 Go de RAM libre, runtime absent). |
| **Justification** | L'indépendance fournisseur exigée par la vision s'obtient par un **adaptateur unique OpenAI-compatible**, déjà anticipé par `backend/.env.example` (`HORIZON_LLM_BASE_URL`, `HORIZON_LLM_API_KEY`, `HORIZON_LLM_MODEL`). Ollama est le meilleur choix pour l'indépendance, mais il exige plusieurs Go d'espace et de RAM — indisponibles ici. Construire l'adaptateur sans fournisseur permet de ne pas bloquer le développement et de ne pas engager de dépense. |
| **Risques** | Un fournisseur distant implique un coût et une dépendance réseau. Le stockage de la clé doit rester côté serveur (`.env` local, jamais dans le frontend). |
| **Dépendances** | Bloque DÉC-3 (`completed`), F1 (CORE) et le Budget Manager. Ne peut pas précéder DÉC-5 (protection de la clé). |

### DÉC-5 — Sécurité : authentification locale simple ou multi-utilisateur

| Colonne | Contenu |
|---|---|
| **Options** | (a) authentification locale simple (un utilisateur, secret local) ; (b) architecture multi-utilisateur (identités, rôles, sessions) ; (c) aucune authentification, réseau local uniquement |
| **Recommandation** | **(a) authentification locale simple, conçue pour évoluer vers (b)** : un identifiant unique, une permission par opération, un journal d'opérations, sans infrastructure multi-utilisateur |
| **Justification** | HORIZON est aujourd'hui mono-utilisateur, sur `127.0.0.1`, avec une base SQLite locale. Construire (b) immédiatement ajouterait des tables d'identité, de rôles et de sessions sans besoin démontré, alors que le backend n'a **aucune** couche d'authentification. (c) est exclu dès qu'une clé API ou une opération sensible entre en jeu. La solution (a) couvre le besoin réel (protéger la clé, tracer les opérations, autoriser les actions sensibles) et laisse le modèle de données prêt pour (b) : une table `principals` avec une seule ligne reste compatible avec une extension multi-lignes. |
| **Risques** | Une authentification « simple » mal délimitée devient une fausse sécurité. Elle doit être explicite : localhost uniquement, secret dans `.env`, refus par défaut de toute opération de niveau 3 ou 4 sans confirmation. |
| **Dépendances** | Bloque DÉC-4 (protection de la clé), F6 (validation/déploiement) et toutes les opérations sensibles. Compatible avec DÉC-2 (même base). |

### DÉC-6 — Composants orphelins (13 fichiers)

| Colonne | Contenu |
|---|---|
| **Options** | (a) supprimer après sauvegarde ; (b) réintégrer dans les pages ; (c) laisser en place (statu quo) |
| **Recommandation** | **(c) laisser en place pour l'instant**, avec une décision de suppression (a) prise **après** validation de DÉC-7 (document d'architecture de référence) |
| **Justification** | Ces 13 fichiers (`SideNav` ×4, `SystemHeader` ×4, `LLMSelector` ×4, `ContextPanel` ×1) sont du code mort, mais ils proviennent des exports MagicPath d'origine et pourraient redevenir utiles si DÉC-7 conclut à une réintégration de la navigation d'origine. Les supprimer maintenant serait irréversible sans repasser par les archives. La règle du projet interdit toute suppression non validée. Le coût de les laisser est nul (ils ne sont pas bundlés). |
| **Risques** | Dette de maintenance légère ; faux sentiment de modularité. Aucun risque fonctionnel. |
| **Dépendances** | Dépend de DÉC-7. Indépendant des 7 autres décisions. |

### DÉC-7 — Documentation architecturale de référence

| Colonne | Contenu |
|---|---|
| **Options** | (a) `02 CODE ET ARCHITECTURE TECHNIQUE\Architecture_Generale.md` (495 o) ; (b) `01_ARCHITECTURE\Architecture_Generale.md` (585 o) ; (c) `06 ARCHIVES\DOCUMENTS_HISTORIQUES\Architecture_Generale_avant_fusion.md` (336 o) |
| **Recommandation** | **(b) `01_ARCHITECTURE\Architecture_Generale.md`** comme document de référence |
| **Justification** | C'est le plus complet des trois : il conserve les trois espaces (Windows / Drive / GitHub) et détaille explicitement la séparation en quatre blocs (cœur, outils et modules, intégrations externes, espaces de mémoire). Il est déjà classé dans le dossier `01_ARCHITECTURE`, ce qui correspond à son rôle. (a) est une version antérieure moins détaillée du même contenu ; (c) est un brouillon pré-fusion, explicitement archivé. |
| **Risques** | Les trois documents doivent rester en place (aucune suppression) ; (a) et (c) doivent être marqués « versions antérieures » pour éviter toute réutilisation. |
| **Dépendances** | Influence DÉC-6 (réintégration ou non de la navigation d'origine). Aucun impact sur les 7 autres décisions. |

### DÉC-8 — Ordre de développement : F2 avant F4 ou F4 avant F2

| Colonne | Contenu |
|---|---|
| **Options** | (a) F2 (Orchestration Manager) d'abord ; (b) F4 (Execution & Continuity) d'abord ; (c) les deux en parallèle |
| **Recommandation** | **(a) F2 d'abord, puis F4** — avec un socle minimal de F4 (modèle de mission) construit **pendant** F2 |
| **Justification** | F4 a besoin du registre d'orchestrateurs pour réattribuer une mission : sans registre, la « réattribution » n'a aucune cible. Inversement, F2 n'a pas besoin de la continuité pour exister. Le socle minimal de F4 (tables `missions` et `checkpoints`) doit toutefois être créé en même temps que le registre, parce que la fiche d'un orchestrateur doit référencer les missions qui lui sont confiées. (c) en parallèle multiplierait les décisions de schéma non stabilisées. |
| **Risques** | Si F4 est totalement absent, F2 livre un registre inutilisable. D'où la recommandation d'un **socle F4 minimal** dans la même étape. |
| **Dépendances** | Dépend de DÉC-2 (schéma de base) et de DÉC-9 (l'entité Projet est le conteneur des missions). |

### DÉC-9 — Gestion des projets : entité autonome ou étiquette de session

| Colonne | Contenu |
|---|---|
| **Options** | (a) entité `projects` autonome en base ; (b) simple étiquette `project_id` sur les sessions ; (c) aucune notion de projet |
| **Recommandation** | **(a) entité `projects` autonome**, avec rattachement des sessions, missions et documents à un projet |
| **Justification** | La vision exige « gestion autonome des projets et de leurs ressources », « continuité après remplacement d'orchestrateur » et « mémoire propre à chaque projet ». Une simple étiquette (b) rend impossible le rattachement d'un orchestrateur à plusieurs projets, le suivi des ressources par projet et la reprise d'un projet après remplacement. (c) contredit directement la vision. L'entité autonome est aussi le point d'ancrage naturel de la mémoire centrale par projet (F5). |
| **Risques** | Coût de migration : les sessions existantes n'ont pas de `project_id`. Une valeur par défaut (« Projet par défaut ») suffit à migrer sans perte. |
| **Dépendances** | Bloque F2, F4, F5 et le Budget Manager. Compatible avec DÉC-2 (même base). |

---

## B. COHÉRENCE GLOBALE

### B.1 Vérification de compatibilité croisée

| Paire | Compatible ? | Point de vigilance |
|---|---|---|
| DÉC-1 (a) + DÉC-7 (b) | **Oui** | Le document de référence doit mentionner que les données d'écran sont des démonstrations marquées |
| DÉC-2 (a) + DÉC-9 (a) | **Oui** | L'entité `projects` s'ajoute à la base existante sans rupture |
| DÉC-2 (a) + DÉC-5 (a) | **Oui** | La table `principals` (une ligne) cohabite avec les autres |
| DÉC-3 (c) + DÉC-4 (d) | **Oui** | Sans fournisseur, seul `accepted_no_model` est émis ; `completed` reste déclaré |
| DÉC-4 (d) + DÉC-5 (a) | **Oui, ordre imposé** | La protection de la clé doit précéder le branchement du fournisseur |
| DÉC-6 (c) + DÉC-7 (b) | **Oui** | La décision de suppression attend le document de référence |
| DÉC-8 (a) + DÉC-9 (a) | **Oui** | Le registre et le projet partagent le même schéma |
| DÉC-1 (a) + DÉC-4 (b) | **Oui** | Le jour où un fournisseur est branché, les valeurs « DEMO » doivent être remplacées par des valeurs mesurées |

### B.2 Contradictions détectées et résolues

| # | Contradiction potentielle | Résolution retenue |
|---|---|---|
| X1 | DÉC-4 recommande « aucun fournisseur » alors que DÉC-3 autorise `completed` | Ce n'est pas une contradiction : `completed` est **déclaré** dans le contrat mais **jamais émis** tant qu'aucun fournisseur n'est branché. Le contrat décrit les états possibles, pas l'état courant. |
| X2 | DÉC-5 « authentification simple » vs vision « permissions centralisées par projet, machine, opération » | Résolu par le modèle de données : la table `principals` unique + une table `permissions` multi-lignes permettent une gestion par projet dès la première version, sans infrastructure multi-utilisateur. |
| X3 | DÉC-2 « base unique » vs vision « évolution vers microservices » | Résolu : base unique **aujourd'hui**, modules de code séparés **dès maintenant**, extraction possible plus tard sans réécriture des contrats. |
| X4 | DÉC-4 écarte Ollama vs vision « indépendance fournisseur » | Résolu : Ollama reste **supporté par conception** via l'adaptateur OpenAI-compatible ; il est seulement **non installable** sur cette machine pour cause d'espace disque. La décision est réversible. |

### B.3 Verdict de cohérence

Les neuf recommandations forment un ensemble **cohérent et non contradictoire**. Trois contraintes d'ordre s'imposent :

1. **DÉC-5 avant DÉC-4** (protéger la clé avant de la brancher).
2. **DÉC-9 avant DÉC-8** (le projet est le conteneur des missions et du registre).
3. **DÉC-7 avant DÉC-6** (le document de référence décide du sort des composants orphelins).

---

## C. ARCHITECTURE RÉSULTANTE

### C.1 Effet sur les six fonctions

| Fonction | Effet des décisions | Ce qui devient possible |
|---|---|---|
| **F1 CORE** | DÉC-3 (statuts), DÉC-4 (adaptateur), DÉC-9 (projet) | Compréhension d'une demande rattachée à un projet, production d'une mission persistée, décision de routage vers un orchestrateur enregistré |
| **F2 Orchestration Manager** | DÉC-8 (en premier), DÉC-9 (projet), DÉC-2 (schéma) | Registre d'orchestrateurs, fiche de capacités, affectation à plusieurs projets sans duplication |
| **F3 Builder** | DÉC-8 (après F2), DÉC-6 (après DÉC-7) | Génération soumise à validation, sans risque de produire des composants redondants |
| **F4 Continuité** | DÉC-8 (socle minimal dès F2), DÉC-2 | Missions, étapes, points de contrôle, verrous, reprise et réattribution |
| **F5 Mémoire** | DÉC-9 (projet), DÉC-2 | Mémoire centrale par projet + mémoire spécialisée laissée à chaque orchestrateur |
| **F6 Validation** | DÉC-5 (sécurité d'abord), DÉC-3 (statuts) | Journal d'opérations, workflow d'autorisation, versions et rollback |

### C.2 Effet sur les services transversaux

| Service | Effet |
|---|---|
| Security & Permissions | Créé en priorité (DÉC-5) : table `principals` (1 ligne), table `permissions` par projet/machine/opération, journal |
| Model Manager | Reposera sur l'adaptateur OpenAI-compatible unique (DÉC-4) ; sélection et fallback côté serveur |
| Budget Manager | Devient mesurable dès qu'un fournisseur est branché (DÉC-4) ; compteurs par projet (DÉC-9) |
| Monitoring & Notification | Peut s'appuyer sur les métriques réelles une fois les pages marquées DEMO retirées (DÉC-1) |
| Resource Discovery / Project Infrastructure / Remote Production / Synchronization | Restent absents ; leur conception dépend de DÉC-9 (projet) pour le rattachement des ressources |

### C.3 Effet sur les cinq couches

| Couche | État après décisions |
|---|---|
| 1 — Interface | Inchangée (aucune reconstruction). 4 pages marquées DEMO (DÉC-1), 2 pages raccordées |
| 2 — HORIZON CORE | Créée progressivement : service de planification après le registre (DÉC-8) |
| 3 — Services transversaux | Le module de code est séparé dès maintenant (DÉC-2), même si la base reste unique |
| 4 — Connecteurs / adaptateurs | L'adaptateur OpenAI-compatible unique (DÉC-4) sert de patron pour tous les autres adaptateurs, y compris Hermes |
| 5 — Infrastructure | Inchangée localement ; le déploiement distant reste à concevoir (aucun dépôt Git aujourd'hui) |

### C.4 Effet sur la base de données

Base unique `horizon.db` (DÉC-2), avec des tables ajoutées par domaine :

| Domaine | Tables | Décision liée |
|---|---|---|
| Existant | `sessions`, `messages` | conservées telles quelles |
| Identité | `principals`, `permissions` | DÉC-5 |
| Projets | `projects`, `project_resources` | DÉC-9 |
| Orchestrateurs | `orchestrators`, `orchestrator_capabilities`, `orchestrator_projects` | DÉC-8 |
| Missions | `missions`, `mission_steps`, `checkpoints`, `locks` | DÉC-8 |
| Mémoire | `documents`, `document_chunks`, `provenance` | DÉC-9 |
| Validation | `operation_log`, `versions`, `deployments` | DÉC-5 |
| Budget | `usage_records` | DÉC-4 |

**Migration :** `sessions` reçoit un `project_id` nullable avec un « Projet par défaut » créé automatiquement. Aucune donnée existante n'est supprimée.

### C.5 Communications entre modules

- **Synchrone** pour les opérations immédiates (création de session, envoi de message, lecture d'état).
- **Asynchrone** pour les missions longues, avec état persistant en base — la continuité ne doit pas dépendre de la mémoire conversationnelle.
- Un seul point de sortie réseau côté frontend (`src/api/http.ts`), conservé.
- Les contrats entre modules restent des contrats HTTP versionnés (`/api/v1`), compatibles avec une extraction future en microservices.

### C.6 Modèles IA et fournisseurs

- **Un adaptateur unique OpenAI-compatible** couvre Ollama, OpenRouter, OpenAI, Azure, vLLM, LM Studio, llama.cpp.
- Le fournisseur est **une configuration serveur** (`.env`), jamais une valeur frontend.
- Le choix du fournisseur n'affecte pas le frontend : celui-ci ne lit que `execution` (`status`, `provider_id`, `model_id`, `fallback_used`).
- **Ollama reste supporté** mais non installable sur cette machine (64 Mo libres). La décision est réversible dès que l'espace disque le permet.

### C.7 Sécurité et permissions

- Authentification locale simple, **refus par défaut** de toute opération de niveau 3 ou 4 sans confirmation explicite (conforme à `Regles_Securite.md`).
- Aucun secret dans le frontend ; clé API uniquement dans `.env` côté serveur.
- Journal d'opérations : identité, cible, résultat, horodatage, sans donnée sensible.
- Permissions exprimées par triplet (projet, machine, opération) — compatible avec une future extension multi-utilisateur.

---

## D. FEUILLE DE ROUTE CONSOLIDÉE

> Ordonnée par dépendances réelles issues des neuf décisions. Chaque étape a un critère de validation vérifiable.

| Étape | Contenu | Décisions appliquées | Prérequis | Critère de validation |
|---|---|---|---|---|
| **E0** | Valider les 9 décisions (tableau §F) | toutes | — | Validation signée |
| **E1** | Marquer les données de démonstration sur les 4 pages statiques | DÉC-1 | E0 | Aucune valeur fictive présentée comme réelle |
| **E2** | Désigner le document de référence et marquer les 2 autres « antérieurs » | DÉC-7 | E0 | Un seul document de référence identifiable |
| **E3** | Schéma de données : `projects`, `principals`, `permissions`, `orchestrators`, `missions`, `checkpoints` (conception écrite, sans code) | DÉC-2, DÉC-5, DÉC-8, DÉC-9 | E0 | Schéma validé et documenté |
| **E4** | Sécurité locale simple : authentification, permissions, journal | DÉC-5 | E3 | Opération de niveau 3 refusée sans confirmation |
| **E5** | Découpage du backend en modules (sessions, capabilities, projects, orchestrators) sans changer les contrats | DÉC-2 | E3 | Les 7 routes existantes répondent à l'identique |
| **E6** | Registre d'orchestrateurs + entité Projet + affectation multiple | DÉC-8, DÉC-9 | E3, E5 | Un orchestrateur associé à 2 projets sans duplication |
| **E7** | Raccordement de la page Agents & Tools Catalog au registre réel | DÉC-1 | E6 | Données réelles affichées, marquage DEMO retiré sur cette page |
| **E8** | Socle F4 : missions, étapes, points de contrôle, verrous | DÉC-8 | E6 | Une mission interrompue reprend sans perte |
| **E9** | Adaptateur LLM OpenAI-compatible générique (aucun fournisseur branché) | DÉC-4 | E4 | Test avec un faux endpoint local réussi |
| **E10** | `/models`, `/settings/model-selection`, capacités réelles | DÉC-4 | E9 | `llm.default` passe de `not_configured` à un statut vérifié |
| **E11** | Service de planification HORIZON CORE (demande → mission) | DÉC-3, DÉC-4 | E8, E10 | Une demande produit une mission persistée avec statut explicite |
| **E12** | Mémoire documentaire + `/memory/status` + `/memory/search` | DÉC-9 | E6 | Recherche réelle sur documents réels, provenance affichée |
| **E13** | Validation & déploiement + rollback + journal | DÉC-5 | E4 | Rollback exécuté et documenté |
| **E14** | Monitoring réel + Budget | DÉC-4 | E10 | Métriques horodatées avec source identifiée |
| **E15** | Orchestration Builder | DÉC-8 | E13 | Un orchestrateur généré passe la validation de E13 |

**Chemin critique :** E0 → E3 → E4 → E5 → E6 → E8 → E9 → E10 → E11. Les étapes E1, E2 et E7 peuvent avancer en parallèle sans bloquer.

**Note sur l'espace disque :** l'étape E9 ne nécessite aucun téléchargement de modèle. Toute étape impliquant un modèle local (Ollama) est **impossible** tant que `C:` n'a pas d'espace libre (64 Mo aujourd'hui).

---

## E. ARBITRAGES UTILISATEUR

> Répartition en trois catégories. Aucune de ces décisions n'a été appliquée : le projet est inchangé.

### E.1 Décisions techniques recommandables directement (aucune validation stratégique requise)

| Décision | Recommandation | Pourquoi elle ne demande pas d'arbitrage stratégique |
|---|---|---|
| **DÉC-3** — Contrat API | Conserver les **deux** états (option c) : `accepted_no_model` sans fournisseur, `completed` seulement après une exécution réelle | C'est le comportement réel du code, conservé et documenté. Aligner le code sur `completed` reviendrait à déclarer achevée une exécution qui n'a pas eu lieu. Aucun coût, aucun accès externe : seule la documentation de contrat est mise à jour. |
| **DÉC-6** — Composants orphelins | Les laisser en place (option c) | Aucun impact fonctionnel. Supprimer exige une sauvegarde et une décision documentaire préalable (DÉC-7). Le statu quo est le choix le moins risqué. |
| **DÉC-7** — Documentation de référence | `01_ARCHITECTURE\Architecture_Generale.md` | Choix documentaire interne, réversible, sans effet sur le code. |
| **DÉC-8** — Ordre F2 avant F4 | F2 (registre d'orchestrateurs) avant F4 | Contrainte technique : F4 doit attribuer une mission à un orchestrateur enregistré. Sans registre, F4 ne peut pas être testé de bout en bout. Aucun coût. |
| **DÉC-2** — Stockage | Base SQLite existante, schéma étendu | Le volume attendu (registre, projets, missions) reste très inférieur aux limites pratiques de SQLite. Aucune nouvelle dépendance, aucune infrastructure supplémentaire. |

### E.2 Décisions stratégiques nécessitant votre approbation

| Décision | Question à trancher | Ce qui change selon la réponse |
|---|---|---|
| **DÉC-1** — Données de démonstration | Marquer « DEMO » (recommandé) ou retirer ? | Marquer conserve la valeur de démonstration et l'honnêteté de l'affichage ; retirer impose de remplacer par des états vides. Choix produit. |
| **DÉC-4** — Premier fournisseur LLM | Adaptateur OpenAI-compatible générique (recommandé) puis brancher un fournisseur distant ? Ou attendre de disposer d'un modèle local ? | Détermine si HORIZON produit des réponses IA dans cette phase. Un fournisseur distant implique un compte, une clé et une dépense. |
| **DÉC-5** — Sécurité | Authentification locale simple (recommandé) ou architecture multi-utilisateur dès maintenant ? | Le multi-utilisateur multiplie la complexité (identités, rôles, sessions) sans bénéfice immédiat pour un usage mono-poste. Choix de périmètre. |
| **DÉC-9** — Gestion des projets | Entité Projet autonome en base (recommandé) ou simple étiquette de session ? | Une entité autonome est nécessaire pour la vision (ressources, mémoire et budget par projet) mais alourdit le schéma initial. Choix d'ambition. |

### E.3 Décisions impliquant une dépense, un accès externe ou une opération sensible

| Décision | Nature du risque | Prérequis avant exécution |
|---|---|---|
| **DÉC-4** (si fournisseur distant) | Dépense récurrente, compte externe, clé API, données envoyées à un tiers | Votre autorisation explicite, choix du fournisseur, plafond de budget, politique de données |
| **DÉC-4** (si modèle local) | Téléchargement de plusieurs Go — **impossible aujourd'hui** (64 Mo libres) | Libération d'espace disque ou changement de volume de stockage |
| **DÉC-5** (authentification) | Introduction d'un mécanisme d'accès : risque de verrouillage, secret à gérer | Validation du modèle de sécurité, procédure de récupération documentée |
| **DÉC-6** (si suppression) | Suppression de 13 fichiers — opération destructrice | Sauvegarde vérifiée + confirmation explicite |
| **DÉC-1** (si retrait) | Perte de la valeur de démonstration des interfaces | Confirmation explicite |

---

## F. TABLEAU UNIQUE DE VALIDATION

> Un seul passage en revue. Colonne « Validation » à compléter par vous : **OK**, **OK avec réserve**, ou **Refusé**.

| # | Décision | Recommandation retenue | Catégorie (§E) | Impact projet | Validation |
|---|---|---|---|---|---|
| 1 | **DÉC-1** Données de démonstration | Marquer « DEMO » sans retirer (option a) | Stratégique | Frontend uniquement, 4 pages | ☐ |
| 2 | **DÉC-2** Stockage | Étendre la base SQLite existante (option a) | Technique | Schéma de données | ☐ |
| 3 | **DÉC-3** Contrat API | Conserver les deux états : `accepted_no_model` + `completed` (option c) | Technique | Documentation de contrat seulement | ☐ |
| 4 | **DÉC-4** Fournisseur LLM | Adaptateur OpenAI-compatible générique d'abord, fournisseur choisi ensuite | Stratégique + dépense | Backend, `.env` | ☐ |
| 5 | **DÉC-5** Sécurité | Authentification locale simple, évolutive (option a) | Stratégique | Backend, schéma | ☐ |
| 6 | **DÉC-6** Composants orphelins | Laisser en place, décision différée (option c) | Technique | Aucun | ☐ |
| 7 | **DÉC-7** Documentation | `01_ARCHITECTURE\Architecture_Generale.md` (option b) | Technique | Documentation | ☐ |
| 8 | **DÉC-8** Ordre de développement | F2 avant F4 (option a) | Technique | Feuille de route | ☐ |
| 9 | **DÉC-9** Gestion des projets | Entité Projet autonome en base (option a) | Stratégique | Schéma, API, UI | ☐ |

### Conditions de levée avant développement

1. **Les 9 cases validées** — aucune étape de la feuille de route (E0) ne démarre sans cela.
2. **DÉC-4 :** préciser si un fournisseur distant est autorisé, avec plafond de budget, ou si la phase reste sans IA.
3. **DÉC-5 :** préciser le périmètre (mono-poste ou multi-utilisateur).
4. **Espace disque :** toute étape avec modèle local exige davantage que 64 Mo libres sur `C:`.
5. **Absence de dépôt Git :** aucun point de retour automatique n'existe. Une sauvegarde manuelle doit précéder l'étape E3 (modification du schéma).

---

## G. INFORMATIONS MANQUANTES (non inventées)

| Élément | Statut |
|---|---|
| Espace disque réellement disponible pour un modèle local | Inconnu — 64 Mo libres mesurés sur `C:`, aucun autre volume vérifié |
| Choix du fournisseur LLM distant | Non décidé par vous — aucune préférence enregistrée |
| Volumétrie prévue (projets, missions, orchestrateurs) | Non fournie — les recommandations de stockage reposent sur une hypothèse d'usage mono-poste |
| Contenu des deux versions concurrentes d'`Architecture_Generale.md` | Non comparées ligne à ligne — seule la désignation du document de référence est recommandée |
| Dépôt Git ou système de versionnement | Absent — vérifié |

**Statut du rapport :** complet (sections 0, A, B, C, D, E, F, G). Aucun fichier source modifié, aucun code généré, aucune installation, aucun compte connecté, aucune dépense. Le seul fichier écrit est ce rapport.
