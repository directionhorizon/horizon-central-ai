# MARKETING 360 — état en ligne au 2026-11-27

Ce document décrit **l'état réel et vérifié** du système d'orchestration
MARKETING 360 sur le serveur en ligne. Il ne décrit pas la spécification
(voir `Marketing_360_Orchestration_System_SPEC_v1.1.md`). Aucune valeur secrète
n'y figure.

## 1. Contexte de la mise en ligne

| Élément | Valeur |
| --- | --- |
| Serveur | `https://horizon.mayela-crm.com` |
| Version du service | `0.4.0` (`/api/v1/health` → `ok`) |
| Canal de déploiement | GitHub `main` → workflow `Deploy app` (`deploy-app.yml`) |
| Commit porteur | `51ad258` — `feat(orchestrateurs): semer le systeme MARKETING 360 (spec v1.1) au demarrage` |
| Mécanisme | Le serveur fait `git fetch/reset --hard origin/main` puis `systemctl restart horizon` ; **le backend sème les systèmes au démarrage**. |

Supabase et Vercel **ne créent pas** d'orchestrateur : Supabase sert la
synchronisation/mémoire en ligne, Vercel héberge le CRM MAYELA. La création se
fait dans le backend (HORIZON CORE) à partir du code versionné.

## 2. Ce qui a été ajouté au code

Dans `backend/horizon/schema.py` (couche données/migrations — **le moteur
d'exécution n'est pas modifié**) :

- `MARKETING_360_SEED` : la fiche du système ;
- `MARKETING_360_AGENTS` : 7 agents (1 coordinateur `orchestrator` + 6
  `specialist`) ;
- `MARKETING_360_ORCHESTRATOR_SKILLS` : 6 compétences rattachées au système ;
- `MARKETING_360_AGENT_SKILLS` : 22 compétences propres aux agents ;
- `_ensure_marketing_360(db)`, appelée par `run_migrations()` après le catalogue
  de compétences.

C'est **additif et idempotent** : aucune édition locale n'est écrasée, un second
passage ne crée aucun doublon, et une compétence absente du catalogue est
ignorée. C'est exactement le mécanisme déjà utilisé pour `FIRST AGENTIC SYSTEM`.

## 3. État en ligne vérifié (lectures sans authentification)

### Orchestrateur — `GET /api/v1/orchestrators`

| Champ | Valeur |
| --- | --- |
| `id` | `system-marketing-360` |
| `name` | `MARKETING 360` |
| `kind` | `horizon` |
| `version` | `1.1.0` |
| `status` | `active` |
| `health_status` | `unverified` |
| `created_at` | `2026-11-27T09:55:30Z` |
| `skills` | 6 compétences rattachées au système |

### Agents — `GET /api/v1/agents`

11 agents en ligne au total : `FIRST AGENTIC SYSTEM` (4) + **MARKETING 360 (7)**.

| `id` | `role` | `name` |
| --- | --- | --- |
| `agent-marketing-360-orchestrateur` | `orchestrator` | Marketing Orchestrator |
| `agent-marketing-360-strategist` | `specialist` | Marketing Strategist |
| `agent-marketing-360-intelligence` | `specialist` | Market Intelligence |
| `agent-marketing-360-digital` | `specialist` | Digital Marketing |
| `agent-marketing-360-creative` | `specialist` | Marketing & Creative |
| `agent-marketing-360-performance` | `specialist` | Marketing Performance & Automation |
| `agent-marketing-360-traditional` | `specialist` | Traditional Marketing |

### Compétences — `GET /api/v1/agents/{id}/skills`

| Agent | Compétences |
| --- | --- |
| orchestrateur | 6 |
| strategist | 3 |
| intelligence | 2 |
| digital | 4 |
| creative | 2 |
| performance | 3 |
| traditional | 2 |
| **Total agents** | **22** |

## 4. Diagnostic du déploiement (GitHub Actions)

Run `45977646680` (commit `51ad258`), job `deploy` :

- **success** : construire l'interface, préparer SSH, déployer `dist`,
  **mettre à jour le code et redémarrer**, **vérifier le service et tester les
  fournisseurs LLM** ;
- **skipped** : « Vérifier une mission de bout en bout » (aucun
  `HORIZON_ADMIN_TOKEN` configuré côté serveur) ;
- **failure** : « Vérifier les outils payants (Stripe et images) » — **sans
  rapport** avec MARKETING 360 (ce test n'invoque pas les orchestrateurs) ; il
  dépend des secrets/providers de paiement et d'images.

Conclusion : **le déploiement du commit a réussi** et a bien semé MARKETING 360
en ligne ; le run est rouge uniquement à cause de l'étape outil-paiement.

## 5. Mission de test en ligne — RÉUSSIE (2026-11-27)

`HORIZON_ADMIN_TOKEN` ayant été fourni (écriture autorisée), la mission de test a
été **créée puis exécutée sur le serveur en ligne** avec le fournisseur **Gemini**
déjà actif.

| Champ | Valeur |
| --- | --- |
| Mission | `ed205b79-b48a-43af-a3ae-e8818ed16672` — « Test operationnel Marketing 360 » |
| Système d'orchestration | `system-marketing-360` |
| Projet | `project-default` |
| Run | `native-6d98fef4-414b-4f7c-883f-77dbc402f944` |
| Statut mission / run | `completed` / `completed` |
| Agent exécutant (runtime) | `Marketing Orchestrator` |
| Fournisseur / modèle | `Gemini (Google)` / `gemini-flash-lite-latest` |
| Jetons | 478 (prompt) + 944 (complétion) = 1 422 |
| Durée | ~15 s (12:56:44 → 12:56:59 UTC) |
| Sortie | « MARKETING 360 — RAPPORT D'ORCHESTRATION » (3 770 caractères) |
| Erreur | (vide) |

La sortie réelle mobilise les compétences héritées (analyse d'audience, campagne
marketing) et signale explicitement les compétences non sollicitées.

**Cause de l'échec local précédent** (`Délai dépassé après 120 s.`) : elle tenait
au **modèle local** (LM Studio / `qwen3.5-4b`), plus lent que le délai
`DEFAULT_TIMEOUT_S = 120 s` codé dans `horizon/llm.py`. En ligne, Gemini
`gemini-flash-lite-latest` répond en **~11 s** : le délai n'est pas atteint.
**Aucune modification du moteur n'a été nécessaire.**

## 6. Limites connues (à ne pas masquer)

1. **Écriture protégée par jeton.** Créer/lancer une mission exige
   `HORIZON_ADMIN_TOKEN` (ou une session Google). La lecture reste ouverte.
2. **Moteur mono-agent à l'exécution.** `native_adapter.dispatch()` appelle
   `run_mission()` **sans** `agent_id` : sans étape, c'est l'agent
   **coordinateur** qui exécute (le `runtime` du run le nomme). La table
   `orchestrator_runs` n'a pas de colonne `agent_id`, donc une exécution
   n'enregistre pas par ligne quel agent a produit quel résultat : ne pas
   présenter MARKETING 360 comme une collaboration multi-agents effective.

## 7. Vérifications reproductibles

```powershell
Invoke-RestMethod https://horizon.mayela-crm.com/api/v1/health
Invoke-RestMethod https://horizon.mayela-crm.com/api/v1/orchestrators
Invoke-RestMethod https://horizon.mayela-crm.com/api/v1/agents
Invoke-RestMethod https://horizon.mayela-crm.com/api/v1/agents/agent-marketing-360-digital/skills
```

## 8. Reprise (procédure de référence)

Déjà effectuée le 2026-11-27 (voir §5). Pour une prochaine mission : fournir
`HORIZON_ADMIN_TOKEN` (secret GitHub côté serveur, ou variable locale pour
appeler l'API), puis :
1. vérifier `GET /api/v1/projects` (projet cible, ex. `project-default`) ;
2. créer la mission rattachée à `system-marketing-360` ;
3. lancer la mission (fournisseur Gemini déjà actif : `gemini-flash-lite-latest`) ;
4. lire `missions.status` et `orchestrator_runs` et rapporter la sortie réelle.

## 9. Sauvegarde

La base du serveur n'est pas exposée. En local, `backend/data/horizon.db`
conserve une copie de travail, avec `horizon.db.bak_20261127_021130` et
`horizon.db.bak-marketing360`. Le présent document ne modifie aucune donnée.
