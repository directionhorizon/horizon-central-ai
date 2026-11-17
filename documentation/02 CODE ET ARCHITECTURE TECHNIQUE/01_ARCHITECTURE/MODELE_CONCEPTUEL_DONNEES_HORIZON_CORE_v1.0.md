# MODÈLE CONCEPTUEL DES DONNÉES — HORIZON CORE

> ⚠️ **DOCUMENT REMPLACÉ — NE PAS UTILISER.**
>
> Cette version (v1.0, 13 novembre 2026) partait d'une prémisse fausse : elle traitait HORIZON CORE comme s'il devait **héberger** les systèmes d'orchestration et stocker leurs données métier. Ce n'est pas son rôle. HORIZON CORE **facilite la création et l'intégration** de systèmes d'orchestration ; il ne les héberge pas et ne devient pas leur base de développement.
>
> **Version en vigueur :** `MODELE_CONCEPTUEL_DONNEES_HORIZON_CORE_v1.1.md` (même dossier).
>
> La v1.1 corrige le cadre, conserve l'inventaire factuel de l'existant, et propose un modèle en deux couches (noyau administratif stable + métadonnées déclaratives extensibles) compatible avec l'accueil de systèmes, projets, ressources et besoins non encore définis. Décision de stockage actée : option B, tout dans le cloud.
>

---

**Version 1.0 — 13 novembre 2026**
**Statut : proposition soumise à validation (livrable de la phase 5)**
**Autorité de validation : propriétaire du projet HORIZON CENTRAL AI**
**Documents de référence :**

- `HORIZON_CENTRAL_AI_Politique_Gouvernance_Donnees_Administratives_v1.0.md` (sections 4.1 à 4.7, 5, 14)
- `01_ARCHITECTURE/HORIZON_DATA_ARCHITECTURE_v0.2.md` (section 15, phases 3 à 12)
- Schéma physique réel du backend : `backend/horizon/schema.py` + base `backend/data/horizon.db`

---

## 0. Objet du document

La politique de gouvernance définit **comment gouverner** : catégories de données administratives, autorités, règles de séparation, de traçabilité et d'accès. Elle ne dit pas **quoi stocker concrètement**, ni sous quelle forme.

Ce document comble cet écart. Il répond à une seule question :

> **Quelles entités administratives HORIZON CORE doit-il conserver, avec quels attributs et quelles relations, pour que la politique soit applicable ?**

Il s'agit du **modèle conceptuel** : les entités, leurs responsabilités, leurs attributs obligatoires et leurs relations. Ce n'est ni un schéma physique, ni un script de migration, ni une décision de déploiement.

---

## 1. Ce que ce document ne fait pas — et pourquoi

La section 15.4 de l'architecture data est explicite :

> « Aucune structure technique ne doit être créée avant la validation de cette architecture cible. »

La politique, section 14, ajoute :

> « Aucune table, migration, permission ou modification backend n'est autorisée par la seule publication de cette politique. »

En conséquence, ce document :

- **ne crée aucune table** ;
- **ne modifie aucune migration** ;
- **ne touche pas au backend en production** ;
- **ne tranche pas** l'emplacement physique définitif (SQLite local vs Supabase) — il prépare cette décision.

Toute création de structure avant validation contredirait le cadre de gouvernance du projet lui-même. Ce document est donc un **livrable de conception**, pas une implémentation.

---

## 2. Inventaire de l'existant (constaté, non supposé)

**Base réelle :** `backend/data/horizon.db` — 200 704 octets — 19 tables — 5 migrations appliquées.

| # | Migration | Nom | Contenu |
|---|---|---|---|
| 1 | 1 | `projects_orchestrators_missions` | projets, orchestrateurs, missions, étapes |
| 2 | 2 | `sessions_project_link` | sessions rattachées aux projets |
| 3 | 3 | `documents_memory` | documents, mémoire |
| 4 | 4 | `offline_first_sync` | outbox, conflits, état de synchronisation |
| 5 | 5 | `integrations_registry` | registre des intégrations |

**Les 19 tables physiques :**

`documents` (1 ligne) · `integrations` (2) · `llm_providers` (1) · `messages` (9) · `mission_checkpoints` (1) · `mission_steps` (1) · `missions` (1) · `operation_log` (33) · `orchestrator_capabilities` (1) · `orchestrator_model_selection` (0) · `orchestrator_projects` (1) · `orchestrators` (1) · `projects` (3) · `schema_migrations` (5) · `sessions` (26) · `settings` (1) · `sync_conflicts` (1) · `sync_outbox` (1) · `sync_state` (0)

### 2.1 Couverture des catégories de la politique

| Catégorie (politique) | Couvert par l'existant ? | Table(s) concernée(s) |
|---|---|---|
| 4.1 Identité et référencement des systèmes | **Partiel** | `orchestrators` (nom, type, description, endpoint, version, statut, santé) |
| 4.2 Identités et responsabilités | **Non** | aucune table |
| 4.3 Référencement administratif des projets | **Partiel** | `projects` (id, nom, description, statut) |
| 4.4 Relations entre systèmes et projets | **Partiel** | `orchestrator_projects` (rôle) |
| 4.5 Configuration administrative centrale | **Partiel** | `settings` (clé/valeur) |
| 4.6 Gouvernance et décisions | **Non** | aucune table |
| 4.7 Traçabilité administrative | **Partiel** | `operation_log` (acteur, action, cible, résultat) |

### 2.2 Constat central

L'existant couvre correctement le **fonctionnement** (projets, missions, sessions, documents, synchronisation) mais ne couvre pas la **gouvernance** (identités, décisions, traçabilité administrative, systèmes d'orchestration comme entité).

Deux manques structurels, confirmés par le schéma :

1. **Le « système d'orchestration » n'existe pas comme entité.** La table `orchestrators` représente l'orchestrateur (le manager d'agents), pas le système d'orchestration (l'environnement autonome). La section 15.2 de l'architecture data impose pourtant de distinguer explicitement les deux notions. Aujourd'hui, la distinction est **perdue dans le schéma**.
2. **Aucune notion d'identité ni de décision.** La politique exige que « toute décision soit rattachée à une autorité identifiable, à un objet, à un périmètre, à une justification et à une période de validité » (4.6). Rien dans le schéma ne permet de porter cela.

---

## 3. Modèle conceptuel proposé

Sept entités administratives. Trois existent déjà et sont à **étendre**, quatre sont à **créer**.

### 3.1 Entités existantes à étendre

#### E1 — `projects` (existant, à étendre)

| Attribut | Statut | Justification |
|---|---|---|
| `id`, `name`, `description`, `status`, `created_at`, `updated_at` | existant | socle administratif déjà conforme à 4.3 |
| `responsible_system_id` | **à ajouter** | 4.3 impose « système d'orchestration responsable » ; 15.3 impose « la relation entre un système d'orchestration et les projets qu'il administre » |
| `authority_ref` | **à ajouter** | 4.3 impose « références vers les espaces de travail et sources faisant autorité » |

**Règle :** un projet a **exactement un** système responsable. Un projet partagé demeure une seule unité métier (4.3) ; la contribution d'un autre système ne transfère pas la responsabilité.

#### E2 — `orchestrators` (existant, à étendre)

| Attribut | Statut | Justification |
|---|---|---|
| `id`, `name`, `kind`, `description`, `endpoint`, `version`, `status`, `health_status`, `last_checked_at`, `config_json`, `created_at`, `updated_at` | existant | couvre 4.1 pour la partie technique |
| `system_id` | **à ajouter** | rattache l'orchestrateur à son système d'orchestration (15.2) |
| `administrative_state` | **à ajouter** | 4.1 impose « état administratif et historique de cet état », distinct de `health_status` (état technique) |

**Règle :** `health_status` prouve l'accessibilité technique ; `administrative_state` prouve l'état administratif. La politique (4.1) interdit de confondre les deux : « L'enregistrement central ne prouve pas que le système est techniquement accessible. »

#### E3 — `settings` (existant, à étendre)

| Attribut | Statut | Justification |
|---|---|---|
| `key`, `value`, `updated_at` | existant | couvre 4.5 pour les paramètres génériques |
| `scope` | **à ajouter** | 4.5 limite le périmètre aux « éléments génériques nécessaires à l'administration de HORIZON CORE » ; il faut pouvoir distinguer un paramètre central d'un paramètre de système |

**Interdit explicite (4.5) :** aucun secret, jeton ou credential dans cette table. Ils relèvent d'un mécanisme sécurisé distinct.

### 3.2 Entités à créer

#### E4 — `orchestration_systems` (à créer)

Entité de premier ordre exigée par la section 15.1.

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant stable (4.1) |
| `name` | oui | nom de référence (4.1) |
| `description` | oui | description et domaine d'activité (4.1) |
| `administrative_state` | oui | état administratif (4.1) |
| `environment` | oui | plateforme ou environnement de rattachement (4.1) |
| `responsible_orchestrator_id` | oui | référence de l'orchestrateur responsable (4.1) |
| `doc_refs` | non | références documentaires et techniques (4.1) |
| `registered_at`, `updated_at` | oui | dates d'enregistrement et de mise à jour (4.1) |

**Règle :** cette table ne stocke **aucune** donnée métier, aucun document de projet, aucun livrable. Elle porte l'existence administrative du système, rien de plus.

#### E5 — `identities` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de l'identité (4.2) |
| `nature` | oui | humaine ou technique (4.2) |
| `display_name` | oui | identification lisible |
| `created_at`, `updated_at` | oui | traçabilité |

**Interdit explicite (4.2) :** « Les secrets d'authentification, clés privées, jetons et mots de passe ne font jamais partie de ces données de registre. » Aucune colonne de secret.

#### E6 — `role_assignments` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de l'affectation |
| `identity_id` | oui | identité concernée (4.2) |
| `role` | oui | rôle et périmètre de responsabilité (4.2) |
| `system_id` | non | rattachement éventuel à un système (4.2) |
| `valid_from`, `valid_to` | oui | période de validité de l'affectation (4.2) |
| `granted_by` | oui | autorité ayant accordé le rôle (4.2) |

**Règle :** une affectation sans période de validité est invalide. La révocation se traduit par une `valid_to` renseignée, jamais par une suppression de ligne — la traçabilité l'exige (4.7).

#### E7 — `governance_decisions` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de la décision |
| `authority_id` | oui | autorité identifiable (4.6) |
| `object_type`, `object_id` | oui | objet de la décision (4.6) |
| `scope` | oui | périmètre (4.6) |
| `decision_type` | oui | demande, autorisation, refus, révocation, arbitrage, validation, évaluation (4.6) |
| `justification` | oui | justification (4.6) |
| `valid_from`, `valid_to` | oui | période de validité (4.6) |
| `created_at` | oui | horodatage |

**Règle :** aucune décision ne peut exister sans les cinq éléments imposés par 4.6 : autorité, objet, périmètre, justification, période de validité.

#### E8 — `administrative_events` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de l'événement |
| `event_type` | oui | changement de responsabilité, de statut, de rattachement, de configuration, d'autorisation (4.7) |
| `object_type`, `object_id` | oui | objet concerné |
| `actor_id` | oui | identité ou autorité à l'origine |
| `detail` | non | contexte de l'événement |
| `occurred_at` | oui | horodatage |

**Règle de séparation (4.7) :** cette table est **distincte** de `operation_log`. `operation_log` trace l'exploitation technique (33 entrées aujourd'hui) ; `administrative_events` trace la gouvernance. Les mélanger rendrait les deux illisibles et violerait 4.7.

### 3.3 Entité de relation à créer

#### E9 — `project_contributions` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `project_id` | oui | projet concerné |
| `system_id` | oui | système contributeur déclaré (4.3) |
| `role` | oui | nature de la contribution |
| `declared_by` | oui | autorité ayant déclaré la contribution |
| `valid_from`, `valid_to` | oui | période de validité |

**Règle (4.4) :** « Une relation enregistrée ne constitue pas une permission d'accès. » Cette table déclare une contribution ; elle n'accorde aucun droit. L'accès relève d'une décision distincte, limitée et révocable (`governance_decisions`).

---

## 4. Relations du modèle

```
orchestration_systems 1 ──── n orchestrators          (un système contient ses orchestrateurs)
orchestration_systems 1 ──── n projects               (responsable_system_id)
orchestration_systems 1 ──── n role_assignments       (rattachement éventuel)
projects              1 ──── n project_contributions  (systèmes contributeurs)
projects              1 ──── n missions               (existant)
projects              1 ──── n documents              (existant)
projects              1 ──── n sessions               (existant)
identities            1 ──── n role_assignments
identities            1 ──── n governance_decisions   (en tant qu'autorité)
governance_decisions  n ──── 1 objet (projet, système, identité, relation)
administrative_events n ──── 1 objet (tout objet administratif)
```

**Chaîne de responsabilité complète :** système d'orchestration → orchestrateur responsable → identités affectées → décisions et événements. C'est cette chaîne que la politique rend obligatoire et que le schéma actuel interrompt au niveau de l'orchestrateur.

---

## 5. Invariants à faire respecter par le backend

1. **Unicité de responsabilité** — un projet a exactement un système responsable, jamais zéro, jamais deux.
2. **Séparation administration / métier** — aucune table administrative ne contient de document, livrable ou donnée métier de projet.
3. **Séparation état technique / état administratif** — `health_status` et `administrative_state` sont deux colonnes distinctes, jamais fusionnées.
4. **Aucun secret dans le registre** — ni dans `settings`, ni dans `identities`, ni ailleurs dans le périmètre administratif.
5. **Validité temporelle** — toute affectation et toute décision porte une période de validité ; la révocation est une date de fin, pas une suppression.
6. **Décision complète ou rejetée** — une décision sans autorité, objet, périmètre, justification ou période de validité est refusée à l'écriture.
7. **Relation ≠ permission** — une contribution déclarée n'ouvre aucun accès ; l'accès exige une décision.
8. **Traçabilité non destructive** — les événements administratifs ne sont ni modifiés ni supprimés.

---

## 6. Traduction physique cible — décision à prendre, pas encore prise

Le modèle conceptuel ci-dessus est indépendant du stockage. Trois options restent ouvertes, à trancher en phase 5 :

| Option | Principe | Avantage | Risque |
|---|---|---|---|
| **(a) Local d'abord** | tout dans SQLite, synchronisé vers Supabase | fonctionne hors ligne, cohérent avec l'existant | dépend d'un appareil allumé pour la gouvernance |
| **(b) Registre distant d'abord** | tables administratives dans Supabase, référence unique | gouvernance disponible 24/24, indépendante de l'appareil | nécessite une authentification et une politique d'accès réelles |
| **(c) Hybride séparé** | administration dans Supabase, métier en local | séparation nette, conforme à 4.5 | deux mécanismes de synchronisation à maintenir |

**Recommandation d'expert : option (c).** Elle est la seule qui matérialise réellement la séparation que la politique impose entre registre administratif et données opérationnelles. Elle rend aussi la gouvernance indépendante de l'état d'allumage d'un appareil, ce qui est la condition d'un pilotage 24/24.

Cette recommandation **n'est pas une décision**. Elle doit être validée avant toute création de table.

---

## 7. Séquence de réalisation

| Étape | Contenu | Statut |
|---|---|---|
| **Phase 5 (ce document)** | valider le modèle conceptuel, trancher l'option de stockage | **en cours** |
| Phase 6 | sauvegardes de la base actuelle | à faire |
| Phase 7 | migration des données existantes vers le modèle validé | à faire |
| Phase 8-10 | vérifications : rattachements, identifiants, responsabilités, provenance, autorisations | à faire |
| Phase 11 | implémentation backend : modèles, relations, API, contrôles d'accès, journalisation | à faire |
| Phase 12 | catalyseur inter-systèmes : projets partagés, contributeurs, autorisations | à faire |

**Point d'attention :** la base actuelle contient 1 document, 3 projets, 26 sessions, 9 messages et 33 entrées de journal. Le volume de migration est faible — c'est le bon moment pour valider le modèle, avant que les données ne se multiplient.

---

## 8. Ce qui reste à décider (phase 5)

1. **Option de stockage** : (a), (b) ou (c) — voir section 6.
2. **Nommage des entités** : les noms proposés ici sont conceptuels ; les noms physiques seront arrêtés avec le schéma.
3. **Autorité d'approbation** : qui valide ce modèle, et sous quelle forme la validation est consignée.
4. **Articulation avec l'authentification** : la politique (14) signale que ce point reste ouvert. `identities` suppose une authentification réelle ; elle n'existe pas encore dans le backend.
5. **Périmètre de `administrative_events`** : faut-il journaliser aussi les consultations, ou seulement les changements ? La politique parle de « changements » (4.7) ; la consultation n'est pas citée.

---

## 9. Vérifications attendues après implémentation

Conformément à la section 15.6 de l'architecture data, le modèle devra permettre de vérifier que :

- HORIZON CORE identifie les systèmes d'orchestration enregistrés.
- Chaque projet est rattaché à son système responsable, de façon unique.
- Les systèmes contributeurs d'un projet partagé sont identifiables.
- Les relations et responsabilités sont consultables et auditables.
- Les accès inter-systèmes restent interdits par défaut et exigent une décision de HORIZON CORE.
- L'isolation des données des systèmes et des projets est préservée.
- Aucun secret n'est présent dans le périmètre administratif.

---

**Conclusion.** La politique dit comment gouverner ; ce document dit quoi stocker pour que cette gouvernance soit possible. Il ne crée rien : il fixe le modèle à valider. Tant qu'il n'est pas validé, aucune table ne doit être ajoutée — c'est la règle que le projet s'est lui-même donnée.
