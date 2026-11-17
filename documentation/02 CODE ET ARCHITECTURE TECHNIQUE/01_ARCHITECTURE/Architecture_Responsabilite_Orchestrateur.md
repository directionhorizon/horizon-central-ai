# RESPONSABILITÉ OPÉRATIONNELLE — L'AGENT ORCHESTRATEUR

**Version 0.1 — 10 novembre 2026 — document de travail**
**Source du principe : décision humaine du 10 novembre 2026 (session d'audit).**
**Statut : principe de conception retenu. Aucune implémentation backend n'est réalisée.**
**Nature : principe d'architecture ET principe de gouvernance des données (double portée — voir §1.1).**
**Cadre : Politique de gouvernance des données v0.4, §4 et §13.**

---

## 1. Le principe, énoncé sans ambiguïté

> **La responsabilité opérationnelle est portée par l'AGENT ORCHESTRATEUR du système, pas par le système en tant qu'entité abstraite.**

Un système d'orchestration n'est pas un acteur : c'est un contenant. Ce qui décide, exécute,
assume et répond est un **agent orchestrateur** identifié, doté d'un rôle, d'un périmètre et de
droits. Le système est l'**environnement d'exécution** de cet agent ; l'agent est le **sujet
responsable**.

Conséquence immédiate : toute écriture, décision, livraison ou erreur doit pouvoir être
rattachée à **un agent nommé**, jamais à « le système » ou « HORIZON ».

### 1.1 Le principe a une double portée (décision humaine du 10/11/2026)

> Ce principe est **à la fois un principe d'architecture et un principe de gouvernance des données**.

Il ne se limite donc pas au code. Il gouverne aussi la donnée elle-même :

| Domaine de gouvernance (§ de la politique) | Ce que change l'agent responsable |
|---|---|
| Propriété et responsabilité (§4) | la responsabilité opérationnelle d'une ressource est portée par un **agent nommé**, pas par un système |
| Identification et métadonnées (§7) | tout enregistrement porte `agent_auteur`, `systeme`, `projet`, `provenance`, `version` |
| Classification et sécurité (§8) | c'est **l'agent producteur** qui signale nature, provenance, contexte, risques ; l'orchestrateur valide et assume |
| Cycle de vie et clôture (§9) | archiver, anonymiser ou supprimer est une **décision d'agent**, tracée et validée, jamais un effet de bord |
| Sauvegarde et continuité (§10) | l'agent responsable répond de l'intégrité et de la restaurabilité de son périmètre |
| Traçabilité et audit (§11) | un journal sans auteur n'est pas un journal : l'auteur est la clé de l'audit |
| Projet partagé et catalyseur (§5) | le catalyseur désigne **un agent responsable**, pas un système |
| Skills (§14) | un skill est rattaché à un agent ; il ne remplace ni la permission technique ni l'approbation humaine |

**Règle pratique** : une donnée dont on ne peut pas nommer l'agent auteur (ou l'humain auteur) est une
donnée **non gouvernée**, même si elle est correctement stockée. C'est ce critère qui départage une
« interface visible » d'une « fonctionnalité opérationnelle ».

## 2. Pourquoi ce principe est indispensable (§4 de la politique)

La politique distingue quatre notions qu'un backend naïf confond :

| Notion (§4) | Portée par | Erreur à éviter |
|---|---|---|
| Propriété métier | le **projet** | rattacher la donnée à l'agent ou au système |
| **Responsabilité opérationnelle** | **l'agent orchestrateur** | la rattacher au système, au projet ou à HORIZON |
| Droits de contribution | les agents contributeurs | donner à un contributeur des droits de responsable |
| Droit de supervision | HORIZON CENTRAL AI | confondre supervision et propriété |

Sans agent nommé, trois dérives deviennent inévitables :
1. **Responsabilité diluée** — une erreur ne peut être imputée à personne : ni correction, ni prévention.
2. **Permissions fausses** — on accorde des droits « au système », donc à tous ses agents, y compris
   ceux qui n'en ont pas besoin (violation du moindre privilège, §8).
3. **Trace inutilisable** — un journal qui dit « le système a supprimé X » ne permet ni audit, ni
   arbitrage, ni retour arrière (§11).

## 3. Déclinaison sur le modèle organisationnel (§2)

```
HORIZON CENTRAL AI  (supervision, arbitrage, métadonnées — ne possède pas les données)
        │
        ├── Système d'orchestration  (environnement : capacités, outils, connecteurs)
        │         │
        │         └── AGENT ORCHESTRATEUR  ◄── sujet responsable (§4)
        │                   │
        │                   ├── agents subordonnés (contributeurs, périmètre limité)
        │                   └── PROJET  (unité métier : propriété métier)
        │                              └── ressources (documents, code, médias, décisions)
        │
        └── ...
```

Un même projet peut être touché par plusieurs agents de plusieurs systèmes → **projet partagé**
(§5), avec **un** agent responsable désigné et des agents contributeurs déclarés.

## 4. Conséquences techniques — ce que le backend doit pouvoir représenter

*Ceci décrit un besoin de modèle, pas un schéma validé. Le §13 impose cartographie, analyse
d'impact, proposition, tests et validation avant toute modification.*

### 4.1 Entités minimales à représenter
- **agent** : identifiant stable, nom, système d'appartenance, rôle, périmètre, statut, version,
  date de dernière vérification.
- **affectation (assignment)** : agent ↔ projet ↔ rôle (responsable / contributeur), avec dates et
  autorisations. Un seul responsable actif par projet à un instant donné.
- **délégation** : droits accordés à un agent, portée, expiration, motif, décision de référence.
- **décision** : agent auteur, objet, justification, conséquence, statut de validation humaine.
- **exécution (run)** : agent, action, cible, résultat, erreurs, ressources touchées.
- **preuve (evidence)** : rattachement à une décision ou à une exécution, sans contenu sensible.

### 4.2 Règles que le backend doit faire respecter
1. **Aucune écriture anonyme** : tout enregistrement porte un `agent_id` (ou `human_id`) auteur.
2. **Un seul responsable actif** par projet ; tout changement laisse une trace de décision.
3. **Le système n'est jamais auteur** : il fournit le contexte d'exécution, l'agent signe.
4. **Séparation responsabilité / supervision** : HORIZON CENTRAL AI lit, agrège, arbitre, mais
   n'écrit pas dans le périmètre métier d'un agent sans décision tracée.
5. **Permissions par agent**, jamais par système ni par projet global.
6. **Secrets inaccessibles aux agents** : l'agent reçoit une capacité, pas une clé (§8).
7. **Réversibilité** : une action destructrice exige une décision validée et un point de retour.
8. **Agents subordonnés** : périmètre hérité mais **jamais** élargi implicitement.

### 4.3 Points d'API à prévoir (proposition, non implémentée)
- `GET/POST /api/v1/agents` — registre des agents (identité, rôle, périmètre, statut).
- `GET/POST /api/v1/assignments` — affectations agent ↔ projet, avec rôle et dates.
- `POST /api/v1/decisions` + `GET /api/v1/decisions?project=` — décisions tracées.
- `GET /api/v1/agents/{id}/runs` — exécutions par agent.
- Toute route d'écriture existante reçoit une attribution d'auteur obligatoire.

### 4.4 Impacts sur le schéma existant (à vérifier, pas à supposer)
Le schéma actuel (migration 5, table `integrations`) ne modélise **aucune** de ces entités.
Avant d'ajouter une table, l'audit doit vérifier : les tables existantes de sessions/messages,
la présence éventuelle de champs d'auteur, et le coût réel d'une migration SQLite. **Ne pas
dupliquer** une notion déjà portée ailleurs, et **ne pas** créer d'abstraction prématurée (§13).

---

## 5. Ce que ce principe change dans la lecture de l'existant

### 5.1 MAYELA CRM
- **Projet** : MAYELA CRM (propriété métier).
- **Système** : le système d'orchestration existant dans Hermès (environnement d'exécution).
- **Agent responsable** : **l'Orchestrateur** — c'est son nom. Il n'est pas « l'agent de MAYELA » :
  c'est l'orchestrateur du système, qui peut porter plusieurs projets.
- **MAYELA n'est pas la condition sine qua non de ce système** : le système existe indépendamment, avec
  son propre périmètre ; MAYELA est **une affectation parmi d'autres**. Un système sans projet affecté
  reste un système valide ; un projet sans orchestrateur affecté n'a pas de responsable opérationnel.
- **Statut réel** : responsable désigné (l'Orchestrateur), **intégration dans HORIZON CENTRAL AI en
  attente** — capacité de supervision non vérifiée.

### 5.2 KING OF THE FOREST
- **Projet** : jeu vidéo.
- **Système** : GAMEFORGE — **conceptualisé, non mis sur pied** (état confirmé par décision humaine).
- **Agent responsable** : **inexistant** à ce jour. Le projet est donc, en l'état, **sans système
  opérationnel et sans agent responsable**.
- Conséquence de gouvernance : KOF ne peut pas être déclaré « projet partagé » (§5) ni recevoir
  d'agent contributeur avant qu'un agent responsable existe. La création de GAMEFORGE est un
  **prérequis**, pas une conséquence, de la coordination.

### 5.3 HORIZON CENTRAL AI
N'est **ni** un projet **ni** un système d'orchestration. C'est l'**app de supervision**. Elle ne doit
donc jamais apparaître comme « agent responsable » d'un projet : elle **supervise** des agents
responsables. Confondre les deux ferait d'elle un orchestrateur déguisé — ce que la politique
exclut explicitement (« aucun orchestrateur codé en dur »).

---

## 6. Propositions pour améliorer le travail (dans le cadre de la politique, sans la modifier)

### P1 — Nommer l'agent responsable avant toute automatisation
Aucun workflow automatisé sur un projet tant que son agent responsable n'est pas nommé, avec
périmètre et droits écrits. **Coût** : faible (une fiche). **Gain** : supprime la responsabilité
diluée, qui est le risque le plus coûteux à corriger après coup.

### P2 — Une fiche d'agent obligatoire, courte et vérifiable
Une page par agent : identité, système, rôle, périmètre, projets affectés, capacités autorisées,
interdits explicites, date de dernière vérification. **Coût** : faible. **Gain** : rend les permissions
auditables sans lire le code.

### P3 — Signature systématique des écritures
Toute écriture porte un auteur (agent ou humain) et un identifiant de décision. **Coût** : moyen
(touche les routes d'écriture). **Gain** : rend le journal d'audit exploitable, condition d'un
arbitrage fiable par HORIZON CENTRAL AI.

### P4 — Séparer « désigné » de « opérationnel » dans le registre
Deux champs distincts : *responsable désigné* et *agent opérationnel vérifié*. **Coût** : quasi nul.
**Gain** : empêche de déclarer une capacité inexistante — l'erreur la plus fréquente de ce projet.

### P5 — Un test de gouvernance par migration
Avant chaque évolution backend : « cette table respecte-t-elle le §4 ? ». **Coût** : faible.
**Gain** : évite les schémas qui mélangent projet, système et agent — refonte coûteuse ensuite.

### P6 — Ne pas construire GAMEFORGE pour « remplir » KOF
Le besoin de KOF doit être décrit avant la conception de GAMEFORGE (§14 : aucun skill sans besoin
démontré). L'ordre inverse produit un orchestrateur sans usage.

---

## 7. Points restant à valider (humain)

1. **Périmètre de l'Orchestrateur** (système Hermès) : quels projets il porte réellement, quelles capacités,
   quelles limites — indépendamment de MAYELA, qui n'en est qu'une affectation.
2. **GAMEFORGE** : périmètre fonctionnel minimal attendu par KOF, avant conception.
3. **Modèle d'affectation** : un seul agent responsable actif par projet — accepté ?
4. **Attribution d'auteur** : obligatoire sur toutes les écritures, ou seulement sur les actions
   significatives ?
5. **Statut de ce document** : référence de conception, à valider avant tout développement backend.

*Aucune modification backend n'a été effectuée. Ce document est un cadre de conception, pas une preuve
d'implémentation.*
