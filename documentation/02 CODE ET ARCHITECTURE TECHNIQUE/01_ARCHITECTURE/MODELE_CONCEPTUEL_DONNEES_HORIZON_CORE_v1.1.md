# MODÈLE CONCEPTUEL DES DONNÉES — HORIZON CORE

**Version 1.1 — 13 novembre 2026**
**Statut : proposition soumise à validation (livrable de la phase 5)**
**Remplace : v1.0 (même jour) — cadre corrigé après recadrage du propriétaire**

**Décision de stockage actée : option B — tout dans le cloud.**
Motifs retenus : le disque C sature vite ; HORIZON CENTRAL AI doit être utilisé sur plusieurs appareils ; la gouvernance ne doit pas dépendre d'un appareil allumé.

**Documents de référence :**

- `HORIZON_CENTRAL_AI_Politique_Gouvernance_Donnees_Administratives_v1.0.md` (sections 4.1 à 4.7, 5, 14)
- `01_ARCHITECTURE/HORIZON_DATA_ARCHITECTURE_v0.2.md` (section 15, phases 3 à 12)
- Schéma physique réel : `backend/horizon/schema.py` + base `backend/data/horizon.db`

---

## 0. Objet du document

La politique de gouvernance dit **comment gouverner**. L'architecture data dit **dans quel ordre** le faire. Aucune des deux ne dit **ce que le registre doit contenir concrètement**.

Ce document le dit. Il définit le registre administratif de HORIZON CORE : quelles entités, quels attributs, quelles relations — et surtout **comment ce registre reste ouvert** pour accueillir des systèmes, projets, ressources et besoins qui n'existent pas encore.

---

## 1. Cadre corrigé — ce que HORIZON CORE n'est pas

Cette section corrige une erreur de la v1.0. Elle est la plus importante du document.

**HORIZON CORE n'est pas une base de développement.** Il n'héberge pas les systèmes d'orchestration, il ne stocke pas leurs données métier, il ne devient pas leur backend. Les systèmes d'orchestration sont des environnements autonomes, responsables de leurs propres données.

**HORIZON CORE est une application qui facilite la création et l'intégration de systèmes d'orchestration.** Sa fonction est de rendre possible, lisible et gouvernable la coexistence de plusieurs systèmes, plusieurs projets, plusieurs ressources et plusieurs besoins — y compris ceux qui n'existent pas encore.

Conséquence directe sur le registre :

> Le registre ne contient **pas** une liste figée de ce qu'il faut ranger. Il contient **de quoi décrire** tout système, tout projet, toute ressource et tout besoin — présents ou futurs — sans qu'il faille modifier le schéma à chaque nouveauté.

C'est la différence entre un **classeur** et un **catalogue**. La v1.0 proposait un catalogue : un jeu d'entités fermé, dérivé des 7 catégories de la politique. C'était trop rigide pour une app dont le métier est précisément d'accueillir l'imprévu. La v1.1 propose un classeur : un petit noyau stable, plus un mécanisme d'extension.

**Ce que le registre contient, et ce qu'il ne contient jamais :**

| Le registre contient | Le registre ne contient jamais |
|---|---|
| L'existence administrative d'un système | Les données métier d'un système |
| Le rattachement d'un projet à son système responsable | Les documents, livrables ou fichiers d'un projet |
| Les identités et les rôles | Les secrets, jetons, clés, mots de passe |
| Les décisions et leur justification | L'état technique temps réel des systèmes |
| Les événements administratifs | Les journaux techniques d'exécution |
| Les métadonnées déclarées par chaque système | Le contenu de ces métadonnées |

---

## 2. Inventaire de l'existant (constaté, non supposé)

**Base réelle :** `backend/data/horizon.db` — 200 704 octets — 19 tables — 5 migrations appliquées.

| Migration | Nom | Contenu |
|---|---|---|
| 1 | `projects_orchestrators_missions` | projets, orchestrateurs, missions, étapes |
| 2 | `sessions_project_link` | sessions rattachées aux projets |
| 3 | `documents_memory` | documents, mémoire |
| 4 | `offline_first_sync` | outbox, conflits, état de synchronisation |
| 5 | `integrations_registry` | registre des intégrations |

**Les 19 tables physiques :**

`documents` (1 ligne) · `integrations` (2) · `llm_providers` (1) · `messages` (9) · `mission_checkpoints` (1) · `mission_steps` (1) · `missions` (1) · `operation_log` (33) · `orchestrator_capabilities` (1) · `orchestrator_model_selection` (0) · `orchestrator_projects` (1) · `orchestrators` (1) · `projects` (3) · `schema_migrations` (5) · `sessions` (26) · `settings` (1) · `sync_conflicts` (1) · `sync_outbox` (1) · `sync_state` (0)

### 2.1 Point favorable pour l'option B

Le code contient déjà une couche de synchronisation hors-ligne (`sync_outbox`, `sync_state`, `sync_conflicts`) et `sync.py` désigne **Supabase comme stockage de référence distant**. L'option B n'est donc pas un renversement d'architecture : c'est l'aboutissement de ce que le code prévoit déjà. La base locale devient un cache de travail, le cloud devient la référence.

### 2.2 Couverture des catégories de la politique

| Catégorie (politique) | Couvert ? | Table(s) concernée(s) |
|---|---|---|
| 4.1 Identité et référencement des systèmes | Partiel | `orchestrators` (nom, type, description, endpoint, version, statut, santé) |
| 4.2 Identités et responsabilités | **Non** | aucune table |
| 4.3 Référencement administratif des projets | Partiel | `projects` (id, nom, description, statut) |
| 4.4 Relations entre systèmes et projets | Partiel | `orchestrator_projects` (rôle) |
| 4.5 Configuration administrative centrale | Partiel | `settings` (clé/valeur) |
| 4.6 Gouvernance et décisions | **Non** | aucune table |
| 4.7 Traçabilité administrative | Partiel | `operation_log` (acteur, action, cible, résultat) |

### 2.3 Constat central

L'existant couvre le **fonctionnement** (projets, missions, sessions, documents, synchronisation) mais pas la **gouvernance**. Deux manques structurels :

1. **Le « système d'orchestration » n'existe pas comme entité.** `orchestrators` contient l'orchestrateur (le manager d'agents), pas le système (l'environnement autonome). La §15.2 de l'architecture impose de distinguer les deux. Le schéma a perdu cette distinction.
2. **Aucune notion d'identité ni de décision.** La §4.6 exige que toute décision porte autorité, objet, périmètre, justification et période de validité. Rien ne peut la porter aujourd'hui.

---

## 3. Principe de conception : noyau stable + extension ouverte

C'est le cœur de la v1.1.

Le registre repose sur **deux couches** :

**Couche 1 — le noyau administratif.** Un petit nombre d'entités stables, qui ne changent pas quand un nouveau système arrive : le système, le projet, l'identité, la décision, l'événement. Ces entités portent uniquement ce que la politique rend obligatoire.

**Couche 2 — les métadonnées déclaratives.** Chaque système déclare ce dont il a besoin (ses ressources, ses besoins, ses attributs propres) dans un champ de métadonnées extensible. HORIZON CORE conserve et gouverne cette déclaration, sans en imposer la forme.

**Pourquoi ce choix :** ton app doit accueillir des systèmes d'orchestration différents, avec des ressources et des besoins différents. Si chaque nouveau besoin exigeait une nouvelle table, le schéma deviendrait ingérable — exactement le problème des « trop de fichiers impossibles à gérer » que tu as identifié. Le noyau stable évite cette dérive ; les métadonnées déclaratives permettent l'accueil sans migration.

**Limite explicite de cette approche :** les métadonnées déclaratives ne peuvent pas porter de logique métier ni de contraintes fortes. Ce qui doit être contraint (unicité de responsabilité, validité temporelle, séparation des secrets) reste dans le noyau, en colonnes typées. Le reste est déclaratif.

---

## 4. Le noyau administratif

### 4.1 Entités existantes à étendre

#### E1 — `projects` (existant, à étendre)

| Attribut | Statut | Justification |
|---|---|---|
| `id`, `name`, `description`, `status`, `created_at`, `updated_at` | existant | conforme à 4.3 |
| `responsible_system_id` | **à ajouter** | 4.3 : « système d'orchestration responsable » |
| `authority_ref` | **à ajouter** | 4.3 : « références vers les sources faisant autorité » |
| `metadata` | **à ajouter** | déclaration libre du projet (couche 2) |

**Règle :** un projet a exactement un système responsable. Un projet partagé reste une seule unité métier ; la contribution d'un autre système ne transfère pas la responsabilité (4.3).

#### E2 — `orchestrators` (existant, à étendre)

| Attribut | Statut | Justification |
|---|---|---|
| `id`, `name`, `kind`, `description`, `endpoint`, `version`, `status`, `health_status`, `last_checked_at`, `config_json`, `created_at`, `updated_at` | existant | couvre 4.1 côté technique |
| `system_id` | **à ajouter** | rattache l'orchestrateur à son système (15.2) |
| `administrative_state` | **à ajouter** | 4.1 : « état administratif », distinct de `health_status` |

**Règle :** `health_status` prouve l'accessibilité technique ; `administrative_state` prouve l'état administratif. La politique (4.1) interdit de les confondre.

#### E3 — `settings` (existant, à étendre)

| Attribut | Statut | Justification |
|---|---|---|
| `key`, `value`, `updated_at` | existant | couvre 4.5 pour les paramètres génériques |
| `scope` | **à ajouter** | distinguer un paramètre central d'un paramètre de système |

**Interdit (4.5) :** aucun secret, jeton ou credential dans cette table.

### 4.2 Entités à créer

#### E4 — `orchestration_systems` (à créer)

Entité de premier ordre exigée par la §15.1. C'est le « classeur » de chaque système.

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant stable (4.1) |
| `name` | oui | nom de référence (4.1) |
| `description` | oui | description et domaine d'activité (4.1) |
| `administrative_state` | oui | état administratif (4.1) |
| `environment` | oui | plateforme ou environnement de rattachement (4.1) |
| `responsible_orchestrator_id` | oui | orchestrateur responsable (4.1) |
| `doc_refs` | non | références documentaires et techniques (4.1) |
| `metadata` | non | déclaration libre du système (couche 2) |
| `registered_at`, `updated_at` | oui | dates d'enregistrement et de mise à jour (4.1) |

**Règle :** aucune donnée métier, aucun document de projet, aucun livrable. Cette table porte l'existence administrative du système, rien de plus.

#### E5 — `identities` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de l'identité (4.2) |
| `nature` | oui | humaine ou technique (4.2) |
| `display_name` | oui | identification lisible |
| `created_at`, `updated_at` | oui | traçabilité |

**Interdit (4.2) :** « Les secrets d'authentification, clés privées, jetons et mots de passe ne font jamais partie de ces données de registre. » Aucune colonne de secret.

#### E6 — `role_assignments` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de l'affectation |
| `identity_id` | oui | identité concernée (4.2) |
| `role` | oui | rôle et périmètre de responsabilité (4.2) |
| `system_id` | non | rattachement éventuel à un système (4.2) |
| `valid_from`, `valid_to` | oui | période de validité (4.2) |
| `granted_by` | oui | autorité ayant accordé le rôle (4.2) |

**Règle :** une affectation sans période de validité est invalide. La révocation est une date de fin, jamais une suppression — la traçabilité l'exige (4.7).

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

**Règle :** aucune décision sans les cinq éléments de la §4.6 — autorité, objet, périmètre, justification, période de validité.

#### E8 — `administrative_events` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `id` | oui | identifiant de l'événement |
| `event_type` | oui | changement de responsabilité, statut, rattachement, configuration, autorisation (4.7) |
| `object_type`, `object_id` | oui | objet concerné |
| `actor_id` | oui | identité ou autorité à l'origine |
| `detail` | non | contexte |
| `occurred_at` | oui | horodatage |

**Séparation (4.7) :** cette table est **distincte** de `operation_log`. `operation_log` trace l'exploitation technique (33 entrées) ; `administrative_events` trace la gouvernance. Les mélanger rendrait les deux illisibles.

### 4.3 Entité de relation à créer

#### E9 — `project_contributions` (à créer)

| Attribut | Obligatoire | Justification |
|---|---|---|
| `project_id` | oui | projet concerné |
| `system_id` | oui | système contributeur déclaré (4.3) |
| `role` | oui | nature de la contribution |
| `declared_by` | oui | autorité ayant déclaré la contribution |
| `valid_from`, `valid_to` | oui | période de validité |

**Règle (4.4) :** « Une relation enregistrée ne constitue pas une permission d'accès. » Cette table déclare une contribution ; elle n'accorde aucun droit. L'accès relève d'une décision distincte (`governance_decisions`).

### 4.4 Le mécanisme d'extension (couche 2)

Le champ `metadata` de `orchestration_systems` et de `projects` est un objet libre (JSON) dans lequel un système déclare :

- ses ressources propres (ce qu'il utilise, sans que HORIZON CORE en connaisse le détail) ;
- ses besoins déclarés (ce qu'il attend de l'écosystème) ;
- ses attributs spécifiques (ce qui n'a de sens que pour lui).

**Ce que HORIZON CORE fait de ces métadonnées :** il les conserve, les versionne et les rend consultables pour la gouvernance. Il ne les interprète pas et n'en impose pas la structure.

**Ce qu'il n'en fait pas :** il ne les utilise pas pour exécuter des opérations, il n'y cherche pas de logique métier, il ne les considère pas comme une source de vérité opérationnelle.

**Pourquoi c'est la bonne réponse à ton besoin :** un nouveau système d'orchestration peut s'enregistrer et déclarer ses ressources et besoins **sans qu'aucune table ne soit créée**. C'est exactement ce qui permet à l'app de faciliter l'intégration plutôt que de la contraindre.

---

## 5. Relations du modèle

```
orchestration_systems 1 ──── n orchestrators          (un système contient ses orchestrateurs)
orchestration_systems 1 ──── n projects               (responsible_system_id)
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

**Chaîne de responsabilité :** système → orchestrateur responsable → identités affectées → décisions et événements. C'est cette chaîne que la politique rend obligatoire et que le schéma actuel interrompt au niveau de l'orchestrateur.

---

## 6. Invariants à faire respecter par le backend

1. **Unicité de responsabilité** — un projet a exactement un système responsable, jamais zéro, jamais deux.
2. **Séparation administration / métier** — aucune table administrative ne contient de document, livrable ou donnée métier de projet.
3. **Séparation état technique / état administratif** — `health_status` et `administrative_state` restent deux colonnes distinctes.
4. **Aucun secret dans le registre** — ni dans `settings`, ni dans `identities`, ni ailleurs dans le périmètre administratif.
5. **Validité temporelle** — toute affectation et toute décision porte une période de validité ; la révocation est une date de fin, pas une suppression.
6. **Décision complète ou rejetée** — une décision sans autorité, objet, périmètre, justification ou période de validité est refusée à l'écriture.
7. **Relation ≠ permission** — une contribution déclarée n'ouvre aucun accès ; l'accès exige une décision.
8. **Traçabilité non destructive** — les événements administratifs ne sont ni modifiés ni supprimés.
9. **Extension sans migration** — un nouveau système, une nouvelle ressource ou un nouveau besoin doit pouvoir être déclaré sans créer de table.

---

## 7. Traduction physique — option B retenue

**Décision : tout dans le cloud.** Supabase est la source de référence. La base SQLite locale devient un cache de travail, pas une source de vérité.

**Ce que cela implique concrètement :**

| Aspect | Conséquence |
|---|---|
| Source de vérité | Supabase. Le registre administratif y vit. |
| Fonctionnement hors ligne | Le cache local permet de travailler ; les écritures partent dans `sync_outbox` et remontent à la reconnexion. La couche existe déjà (migration 4). |
| Multi-appareils | Chaque appareil lit et écrit le même registre. Les conflits sont détectés par `sync_conflicts` (déjà présent). |
| Disque C | Le cache local reste léger : seules les métadonnées administratives y transitent, pas les données métier des systèmes. |
| Gouvernance 24/24 | Assurée : le registre est accessible sans qu'un appareil soit allumé. |

**Point de vigilance honnête :** l'option B déplace la dépendance. Elle ne dépend plus d'un appareil, mais elle dépend de Supabase. La politique (§4.5) exige que les secrets soient conservés dans un mécanisme sécurisé distinct — cela reste à mettre en place, et c'est un prérequis, pas une option.

**Point de vigilance sur l'authentification :** la politique (§14) signale que l'articulation avec l'authentification reste ouverte. Avec l'option B, ce point devient bloquant : un registre central accessible depuis plusieurs appareils exige une authentification réelle. `identities` la suppose ; elle n'existe pas encore dans le backend. L'usage réel est mono-utilisateur (une seule personne, plusieurs appareils) : il ne s'agit donc pas de gérer des comptes multiples, mais de permettre à un même propriétaire de se connecter depuis chaque appareil et de révoquer une session perdue.

---

## 8. Séquence de réalisation

| Étape | Contenu | Statut |
|---|---|---|
| **Phase 5 (ce document)** | valider le modèle conceptuel ; option B actée | **en cours** |
| Phase 6 | sauvegardes de la base actuelle | à faire |
| Phase 7 | migration des données existantes vers le modèle validé | à faire |
| Phase 8-10 | vérifications : rattachements, identifiants, responsabilités, provenance, autorisations | à faire |
| Phase 11 | implémentation backend : modèles, relations, API, contrôles d'accès, journalisation | à faire |
| Phase 12 | catalyseur inter-systèmes : projets partagés, contributeurs, autorisations | à faire |

**Contexte de migration :** 1 document, 3 projets, 26 sessions, 9 messages, 33 entrées de journal. Volume faible — c'est le bon moment pour valider, avant que les données ne se multiplient.

---

## 9. Ce qui reste à décider (phase 5)

1. **Authentification** — prérequis de l'option B. Usage réel constaté : **un seul utilisateur humain**, propriétaire du registre, qui accède depuis plusieurs appareils. La question n'est donc pas « qui a le droit » (réponse : une seule personne) mais « comment ce propriétaire prouve son identité depuis chaque appareil, et comment les sessions se révoquent si un appareil est perdu ». La politique §14 laisse le mécanisme ouvert ; le choix du cloud le rend bloquant. `identities` n'a donc pas besoin d'être multi-utilisateurs au départ : une identité humaine unique suffit, avec la possibilité d'en ajouter sans changer le schéma.
2. **Mécanisme de secrets** — distinct du registre, exigé par §4.5. À choisir avant toute mise en production.
3. **Nommage des entités** — les noms proposés sont conceptuels ; les noms physiques seront arrêtés avec le schéma Supabase.
4. **Autorité d'approbation** — qui valide ce modèle, et sous quelle forme la validation est consignée.
5. **Périmètre de `administrative_events`** — journaliser seulement les changements (comme le dit §4.7), ou aussi les consultations ?
6. **Stratégie de conflits** — la table `sync_conflicts` existe ; la règle de résolution (dernier écrivain gagne, arbitrage manuel, ou décision de gouvernance) reste à définir.

---

## 10. Vérifications attendues après implémentation

Conformément à la §15.6 de l'architecture data, le modèle devra permettre de vérifier que :

- HORIZON CORE identifie les systèmes d'orchestration enregistrés.
- Chaque projet est rattaché à son système responsable, de façon unique.
- Les systèmes contributeurs d'un projet partagé sont identifiables.
- Les relations et responsabilités sont consultables et auditables.
- Les accès inter-systèmes restent interdits par défaut et exigent une décision de HORIZON CORE.
- L'isolation des données des systèmes et des projets est préservée.
- Aucun secret n'est présent dans le périmètre administratif.
- Un nouveau système peut s'enregistrer et déclarer ses ressources et besoins sans création de table.

---

**Conclusion.** La politique dit comment gouverner. Ce document dit ce que le registre contient pour que cette gouvernance soit possible — un noyau stable de cinq entités administratives, plus un mécanisme d'extension qui permet d'accueillir l'imprévu sans migration. Le stockage est acté : tout dans le cloud. Aucune table n'est créée tant que ce modèle n'est pas validé — c'est la règle que le projet s'est lui-même donnée.
