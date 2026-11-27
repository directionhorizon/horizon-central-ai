# Exécuteur d'orchestration multi-agents — 2026-11-27

## Objet
Moteur **générique** d'orchestration : il transforme une mission en travail réellement
réparti entre les agents d'un système. Il ne dépend d'aucun système particulier :
tout système `kind = horizon` peut l'activer avec ses propres agents.

Chaîne exécutée : **planifier → router → exécuter → suivre → consolider**.

## Activation (optionnelle, par système)
`PATCH /api/v1/orchestrators/{orchestrator_id}` avec :

```json
{ "config": { "orchestration": "multi-agent", "max_steps": 5 } }
```

- Sans ce drapeau, le moteur natif **mono-agent** reste utilisé (comportement inchangé).
- `max_steps` est borné entre 2 et 12 (plafond dur `MAX_STEPS_HARD`).
- MARKETING 360 est activé en production avec `max_steps = 5`.

## Déroulé
1. **Planifier** : le fournisseur LLM reçoit la mission **et la liste réelle des agents
   du système** (identifiant, nom, rôle, spécialité) ; il renvoie
   `{"steps": [{"title": ..., "agent_id": ...}]}`.
2. **Router** : chaque `agent_id` est **validé** contre les agents du système ; tout
   identifiant inconnu retombe sur l'agent coordinateur (aucun agent inventé).
3. **Exécuter** : chaque étape est exécutée par son agent via le moteur natif
   (`native_engine.run_mission(..., agent_id=...)`), avec les compétences effectives de
   cet agent uniquement.
4. **Suivre** : l'étape est persistée (`mission_steps.assigned_agent_id`) et l'exécution
   aussi (`orchestrator_runs.agent_id`), une ligne par étape et par agent.
5. **Consolider** : l'agent coordinateur produit la synthèse finale (contributions
   reçues, faits / estimations / hypothèses distingués). Le résultat consolidé devient
   la sortie de la mission ; l'usage est la somme des étapes et de la consolidation.

## Fichiers
- **Nouveau** : `backend/horizon/orchestrator_engine.py` (moteur).
- `backend/horizon/adapters/native_adapter.py` (bascule mono / multi selon la config).
- `backend/horizon/schema.py` (migrations **19** et **20**).
- `backend/horizon/repositories/missions.py` (colonne `assigned_agent_id`).
- `backend/horizon/repositories/runs.py` (colonne `agent_id`).

## Migrations (idempotentes, additives)
| Version | Nom | Effet |
| --- | --- | --- |
| 19 | `mission_steps_assigned_agent` | `mission_steps.assigned_agent_id TEXT DEFAULT ''` |
| 20 | `orchestrator_runs_agent` | `orchestrator_runs.agent_id TEXT DEFAULT ''` |

Aucune donnée existante n'est supprimée ni déplacée.

## Preuves vérifiées (production, 2026-11-27)
- **22/22** contrôles locaux passés (migrations, activation, routage, repli coordinateur,
  plan vide refusé, somme d'usage, aller-retour dépôt sur étapes et exécutions).
- **Mission réelle** `1acfa905-7d16-45f3-b5ab-137e4611d5ff`
  (« Campagne de lancement - test multi-agents ») : statut `completed` en ~62 s,
  **5 étapes, 5 agents différents**, 0 échec.
  - Market Intelligence → analyse marché/positionnement
  - Marketing Strategist → stratégie et plan de campagne
  - Marketing & Creative → concepts créatifs et messages
  - Digital Marketing → canaux et calendrier 4 semaines
  - Marketing Orchestrator → coordination de la livraison
- **6 exécutions** persistées : 5 par étape/agent + 1 dispatch consolidé
  (`engine = horizon-orchestrator`, `mode = multi-agent`, fournisseur *Gemini (Google)*,
  modèle `gemini-flash-lite-latest`, 17 004 tokens au total).

## Outils (mains) : attributions et tests réels
**40 attributions** vérifiées en ligne sur les 7 agents (recherche web, PDF, image,
fichiers, code, API, RSS, mémoire, planifier/déléguer, journalisation, supervision).

| Main | Statut | Test réel |
| --- | --- | --- |
| Recherche web | `ready` | **En ligne OK** — repli sans clé (DuckDuckGo), 3 résultats réels renvoyés |
| Générer une image | `ready` | **En ligne OK** — provider Pollinations, URL d'image réellement servie |
| Lire un PDF | `ready` | **Local OK** — PDF généré : 1 page, texte extrait, chemin hors espace de travail **refusé**. En ligne : réponse honnête `400` car aucun PDF n'existe dans l'espace de travail du serveur (pas un défaut) |

Distinction maintenue : **attribué ≠ opérationnel**. Une main attribuée est utilisable
par son agent ; elle n'est dite opérationnelle qu'après un test réel réussi.

## Limites honnêtes (état exact)
- Les agents **n'appellent pas encore les mains pendant une mission** : la boucle
  d'appel d'outils (`tool-plan`, `tool-delegate`, recherche, fichiers, images) reste à
  brancher dans `native_engine`. Aujourd'hui les mains sont exécutables via
  `POST /api/v1/tools/{tool_id}/run` et attribuées, mais pas encore mobilisées par le
  moteur au fil des étapes.
- L'exécution des étapes est **séquentielle** (dépendances respectées ; parallélisation
  possible plus tard).
- Aucune donnée n'est inventée : sans fournisseur LLM, sans agent actif ou sans plan
  exploitable, le moteur lève une erreur explicite et l'étape passe en `failed`.

## Suite
1. Boucle d'appel d'outils dans le moteur (une main = un appel réel, journalisé).
2. Test PDF en ligne après dépôt d'un document réel dans l'espace de travail du serveur.
3. Parallélisation des étapes indépendantes et reprise sur échec d'une étape.
