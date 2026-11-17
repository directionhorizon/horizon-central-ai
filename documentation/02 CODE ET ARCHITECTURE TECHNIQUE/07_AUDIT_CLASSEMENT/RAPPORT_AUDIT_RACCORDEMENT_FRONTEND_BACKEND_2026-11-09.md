# HORIZON LOCAL AI — AUDIT DU RACCORDEMENT FRONTEND / BACKEND

Date : 2026-11-09
Projet : `C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI`
Type : audit préparatoire, **lecture seule** — aucun fichier source modifié, créé ou supprimé (hors ce rapport).

---

## 1. FRONTEND — état réel

### 1.1 Structure

| Élément | Détail |
|---|---|
| Entrée | `src/main.tsx` → monte `<App />` dans `#root`, importe `./index.css` |
| Shell | `src/App.tsx` : navigation par état local `useState<PageId>('workbench')`, pas de routeur (aucune URL) |
| Contexte partagé | `src/shared/ChatSessionContext.tsx` (`ChatSessionProvider` / `useChatSession`) |
| Pages | 6 pages, une par espace, rendues conditionnellement dans `App.tsx` |
| Données partagées entre pages | uniquement le tableau `messages` du contexte |

### 1.2 Pages et dépendance à une API

| Page | Fichier | Lignes | Source des données | Besoin API |
|---|---|---|---|---|
| Main Workbench | `main-workbench/MainWorkbench.tsx` | 106 | contexte + `localStorage` | **oui** (sessions, messages) |
| AI Control Center | `ai-control-center/AIControlCenter.tsx` | 57 | contexte + état local | **oui** (sessions, messages, capacités) |
| Model Manager | `model-manager/ModelManager.tsx` | 190 | **constantes statiques** `PROVIDERS`, `USAGE_POINTS` | **oui** (modèles, préférence) |
| Knowledge & Memory Hub | `knowledge-memory-hub/KnowledgeMemoryHub.tsx` | 154 | **constantes statiques** `DOCUMENTS`, `GRAPH_POINTS` | **oui** (mémoire) |
| Agents & Tools Catalog | `agents-tools-catalog/AgentsToolsCatalog.tsx` | 77 | **constantes statiques** `environments`, `integrations` | **oui** (intégrations) |
| System Monitor | `system-monitor/SystemMonitor.tsx` | 91 | **constantes statiques** `initialNodes` | **oui** (métriques) |

### 1.3 Données simulées ou locales

| Type | Emplacement | Nature |
|---|---|---|
| Messages de conversation | `ChatSessionContext.tsx` lignes 23-27 (`initialMessages`) | 3 messages de démonstration injectés au premier chargement |
| Persistance | `ChatSessionContext.tsx` lignes 29, 34, 57 — clé `horizon-local-ai:shared-chat:v1` | `localStorage` uniquement, aucune synchronisation serveur |
| Fournisseurs de modèles | `ModelManager.tsx` `PROVIDERS` (3 entrées) | statique ; statuts `Not verified`, latences `42 ms` / `318 ms` / `—` |
| Graphique d'usage | `ModelManager.tsx` `USAGE_POINTS` | statique |
| Documents de mémoire | `KnowledgeMemoryHub.tsx` `DOCUMENTS` (5 entrées) | statique |
| Points du graphe | `KnowledgeMemoryHub.tsx` `GRAPH_POINTS` | statique |
| Environnements | `AgentsToolsCatalog.tsx` `environments` (3 entrées) | statique, états `Not connected` / `Needs verification` |
| Intégrations | `AgentsToolsCatalog.tsx` `integrations` | statique |
| Nœuds surveillés | `SystemMonitor.tsx` `initialNodes` (3 entrées) | statique ; `refresh()` ne change que le libellé `detail` |

**Aucun appel réseau n'existe** : 0 occurrence de `fetch(`, `axios`, `XMLHttpRequest`, `/api/` dans tout `src/`.

### 1.4 Interactions utilisateur nécessitant une API

| Interaction | Page | Comportement actuel | API nécessaire |
|---|---|---|---|
| Envoyer un message | Main Workbench | `addUserMessage()` → ajout local, aucune réponse générée | `POST /sessions/{id}/messages` |
| Nouvelle session | AI Control Center | `resetSession()` → remplace le tableau local | `POST /sessions`, `POST /sessions/{id}/reset` |
| Revenir sur une session | Workbench / Control Center | impossible (aucun historique) | `GET /sessions`, `GET /sessions/{id}` |
| Changer le mode de routage | AI Control Center | état local, aucun effet | `PUT /settings/model-selection` |
| Ajouter/sélectionner un fournisseur | Model Manager | formulaire local, aucun effet | `GET /models`, `PUT /settings/model-selection` |
| Importer / rechercher un document | Knowledge & Memory Hub | filtrage sur données statiques | `GET /memory/status`, `POST /memory/search` |
| Actualiser l'état des nœuds | System Monitor | réécrit un libellé local | `GET /system/metrics` |
| Vérifier les intégrations | Agents & Tools Catalog | liste statique | `GET /integrations` |
| Vérifier la santé du service | (aucune page) | — | `GET /health`, `GET /capabilities` |

### 1.5 Constat

Le frontend est **entièrement autonome** : aucune donnée ne provient du backend, aucune action n'a d'effet persistant. Les textes affichés le reconnaissent explicitement (« Interface preview », « No backend connection detected », « Monitoring is not connected yet »).

---

## 2. BACKEND — état réel

### 2.1 Les 7 routes implémentées (`backend/app.py`, 138 lignes)

| # | Méthode | Route | Entrée | Sortie | Codes |
|---|---|---|---|---|---|
| 1 | GET | `/api/v1/health` | — | `status, service, version, timestamp` | 200 |
| 2 | GET | `/api/v1/capabilities` | — | `schema_version, generated_at, capabilities[5]` | 200 |
| 3 | POST | `/api/v1/sessions` | `{"title": str 1-160}`, défaut « Nouvelle session » | `id, title, created_at, updated_at` | 201, 422 |
| 4 | GET | `/api/v1/sessions` | `?limit` 1-100, défaut 30 | `{"items":[...]}` | 200 |
| 5 | GET | `/api/v1/sessions/{id}` | — | session + `messages[]` | 200, 404 |
| 6 | POST | `/api/v1/sessions/{id}/messages` | `{"content": str 1-12000}` | `session_id, message, execution{status:"accepted_no_model"}, warnings[]` | 202, 404, 422 |
| 7 | POST | `/api/v1/sessions/{id}/reset` | — | `session_id, status:"reset", updated_at` | 200, 404 |

### 2.2 Infrastructure constatée

- Persistance SQLite, `HORIZON_DATABASE_PATH` (défaut `./data/horizon.db`), tables `sessions` et `messages`, clé étrangère `ON DELETE CASCADE`.
- CORS `CORSMiddleware` : origines `http://localhost:5173,http://127.0.0.1:5173`, méthodes `GET, POST, PUT`, en-têtes `Content-Type, Authorization`.
- Documentation interactive exposée : `/docs`, `/redoc`, `/openapi.json`.
- Aucune authentification, aucun jeton, aucun contrôle de permission.
- Aucune limite de débit, aucune journalisation applicative.
- Aucun appel LLM : message enregistré avec `accepted_no_model` + avertissement.

### 2.3 Limitations et fonctionnalités manquantes

| # | Manque | Impact |
|---|---|---|
| B1 | Pas de génération de réponse assistant | aucune réponse IA possible |
| B2 | `POST /sessions/{id}/messages` n'accepte que `content` | `attachments`, `client_message_id`, `model_preference` du contrat v0.1 sont ignorés (422 si envoyés) |
| B3 | `execution.status` renvoie `accepted_no_model` alors que le contrat prévoit `completed` | divergence de contrat |
| B4 | Champ `citations` absent de la réponse | divergence de contrat |
| B5 | Routes absentes : `/models`, `/settings/model-selection`, `/memory/status`, `/memory/search`, `/system/metrics`, `/integrations` | 6 fonctionnalités du contrat non implémentées |
| B6 | Aucune suppression de session | seul `reset` (vide les messages) existe |
| B7 | Aucun `client_message_id`, aucune idempotence | risque de doublons en cas de retentative |
| B8 | Aucune pagination des messages | `GET /sessions/{id}` renvoie tout |
| B9 | `GET /sessions` sans métadonnées de pagination (total, curseur) | plafond 100 sans indication de suite |
| B10 | Erreurs non structurées (format `HTTPException` par défaut) | formats hétérogènes côté client |
| B11 | `backend/README.md` : chemin erroné (`HORIZON_APP`) et caractères mal encodés | documentation inexacte |

---

## 3. CORRESPONDANCE FRONTEND ↔ BACKEND

| Fonctionnalité frontend | Route backend | État du raccordement | Modifications nécessaires | Tests à réaliser |
|---|---|---|---|---|
| Envoyer un message (Main Workbench) | `POST /api/v1/sessions/{id}/messages` | **Aucun** — ajout local seulement | Service API + `POST` avec `content` ; gérer 202 + `execution.status` ; ne pas fabriquer de réponse assistant | message persisté en base, visible après rechargement, statut `accepted_no_model` affiché |
| Nouvelle session (AI Control Center) | `POST /api/v1/sessions` | **Aucun** — `resetSession()` local | créer la session côté serveur, conserver `session_id` dans le contexte | session créée 201, `id` conservé, session visible dans `GET /sessions` |
| Réinitialiser la conversation | `POST /api/v1/sessions/{id}/reset` | **Aucun** | confirmation UI puis appel ; vider le cache local seulement après succès | 200, messages vidés en base, UI cohérente |
| Historique des sessions | `GET /api/v1/sessions` | **Aucun** | liste déroulante ou panneau ; gérer `limit` | 200, liste ordonnée par `updated_at` décroissant |
| Recharger une session | `GET /api/v1/sessions/{id}` | **Aucun** | mapper la réponse backend vers `ChatMessage` (role, content, created_at → time) | 200, messages affichés dans l'ordre, 404 géré |
| État du service (aucune page) | `GET /api/v1/health` | **Aucun** | indicateur de santé dans le shell ou System Monitor | 200, latence mesurée, état « hors ligne » si échec |
| Registre des capacités (aucune page) | `GET /api/v1/capabilities` | **Aucun** | afficher les 5 capacités et leur statut réel | 200, statuts `available` / `not_configured` / `unverified` affichés |
| Liste des fournisseurs (Model Manager) | `GET /api/v1/models` | **Route inexistante** | créer la route côté backend avant tout raccordement | 200, liste vide ou réelle, aucun faux statut « disponible » |
| Mode de routage (AI Control Center) | `PUT /api/v1/settings/model-selection` | **Route inexistante** | créer la route ; persister le mode | 200, mode relu après redémarrage |
| Documents de mémoire (Knowledge Hub) | `GET /api/v1/memory/status`, `POST /api/v1/memory/search` | **Routes inexistantes** | créer les routes ; remplacer `DOCUMENTS` statique | 200, résultats réels, aucune donnée fabriquée |
| Métriques système (System Monitor) | `GET /api/v1/system/metrics` | **Route inexistante** | créer la sonde ; remplacer `initialNodes` | 200, mesures datées avec source identifiée |
| Intégrations (Agents & Tools) | `GET /api/v1/integrations` | **Route inexistante** | créer la route ; remplacer la liste statique | 200, état et permissions réels |

**Synthèse** : sur 12 fonctionnalités identifiées, **7 peuvent être raccordées aux routes existantes** (avec un travail frontend) et **5 dépendent de routes backend qui n'existent pas encore**.

---

## 4. ARCHITECTURE DE COMMUNICATION PROPOSÉE

Principe : **un seul point d'entrée réseau côté frontend**, une couche de session unique, aucune donnée métier codée en dur dans les pages. Les pages continuent d'être rendues comme aujourd'hui (aucun routeur imposé).

### 4.1 Couches proposées (fichiers à créer lors de l'implémentation)

```
src/
├─ config/
│  └─ env.ts                 URL de base, timeout, feature flags (import.meta.env)
├─ api/
│  ├─ http.ts                client HTTP unique (fetch), timeout, JSON, erreurs
│  ├─ errors.ts              ApiError normalisé (status, code, message, details)
│  ├─ types.ts               types alignés sur le contrat v0.1
│  ├─ sessions.ts            create/list/get/reset/message
│  └─ capabilities.ts        health / capabilities
├─ hooks/
│  ├─ useSessions.ts         liste, création, sélection
│  ├─ useSession.ts          session + messages
│  └─ useCapabilities.ts     santé + capacités
└─ shared/
   └─ ChatSessionContext.tsx  enrichi (session_id serveur) sans casser l'API actuelle
```

### 4.2 Service API frontend
- `http.ts` : une fonction `request<T>()` unique. Base URL depuis `import.meta.env.VITE_HORIZON_API_URL` (défaut `http://127.0.0.1:8000`). `AbortController` pour le timeout. Aucun secret, aucun jeton dans le code.
- Sérialisation JSON systématique, en-tête `Content-Type: application/json`.
- Les secrets restent côté backend (`HORIZON_LLM_API_KEY`).

### 4.3 Gestion des sessions
- `session_id` devient un état **serveur**, plus un simple tableau local.
- Premier chargement : `GET /sessions` → si vide, `POST /sessions` → conserver l'`id`.
- Le `session_id` courant est mémorisé dans `localStorage` comme simple repère (clé distincte, ex. `horizon-local-ai:current-session`) ; la référence reste le backend, conformément au §5 du contrat.
- `resetSession()` appelle `POST /sessions/{id}/reset` puis recharge la session.

### 4.4 Gestion des messages
- Envoi : `POST /sessions/{id}/messages` avec `{ content }`.
- Réponse 202 : afficher le message utilisateur **et** le statut `accepted_no_model` comme information, **jamais** comme réponse assistant.
- Rechargement : `GET /sessions/{id}` → mapping `created_at` ISO → libellé d'heure.
- Pièces jointes : le backend n'accepte pas `attachments`. Le frontend doit soit désactiver l'envoi de fichiers, soit afficher « pièce jointe non transmise ». **Aucun envoi silencieux.**

### 4.5 Gestion des erreurs
- `ApiError` normalisé : `{ status, code, message, details }`.
- Distinguer : réseau injoignable (backend arrêté), 404 session inconnue, 422 validation, 5xx serveur.
- Réessai automatique **uniquement** sur erreur réseau et opérations idempotentes (`GET`). Pas de réessai sur `POST` sans `client_message_id`.
- Aucune erreur silencieuse : bandeau ou message inline dans la page concernée.

### 4.6 Configuration des URL backend
- `VITE_HORIZON_API_URL` dans `.env.local` (jamais versionné), défaut `http://127.0.0.1:8000`.
- CORS backend à aligner sur l'origine réelle : `http://localhost:5173` (Vite écoute sur `::1`, donc `127.0.0.1` ne répond pas en dev).
- Changement d'hôte sans modification de code.

### 4.7 Gestion des états de chargement
- États explicites : `idle`, `loading`, `success`, `error`.
- Boutons désactivés pendant l'appel, indicateur de progression, squelette pour l'historique.
- Pas d'état optimiste non réconcilié : après un `POST`, relire la session pour confirmer la persistance.

### 4.8 Extensibilité vers d'autres fournisseurs (OpenRouter, modèles locaux)
Le frontend **ne doit jamais connaître** un fournisseur. Il envoie une intention et lit une `execution` normalisée.

```
React → /api/v1/sessions/{id}/messages → HORIZON Core
                                          └─ LLM Manager (interne)
                                               ├─ adaptateur OpenAI-compatible
                                               ├─ adaptateur OpenRouter
                                               ├─ adaptateur local (Ollama / llama.cpp)
                                               └─ politique de routage + fallback
```

- Un seul contrat côté client ; les adaptateurs sont ajoutés côté backend.
- `execution` porte déjà `provider_id`, `model_id`, `fallback_used` : le frontend pourra les afficher sans être modifié.
- Aucun raccordement OpenRouter réalisé à ce stade (contrainte respectée).

---

## 5. PLAN D'EXÉCUTION

| Étape | Contenu | Fichiers concernés | Dépend de | Critère de validation |
|---|---|---|---|---|
| 1 | Config d'environnement frontend | `src/config/env.ts` (nouveau), `.env.local` (local, non versionné), `.env.example` (doc) | — | URL lue depuis l'environnement, aucun secret |
| 2 | Client HTTP + erreurs | `src/api/http.ts`, `src/api/errors.ts`, `src/api/types.ts` (nouveaux) | 1 | `GET /health` → 200 ; URL invalide → `ApiError` explicite |
| 3 | Endpoints sessions/messages | `src/api/sessions.ts`, `src/api/capabilities.ts` (nouveaux) | 2 | appels typés compilent, `npm run build` passe |
| 4 | Contexte de session serveur | `src/shared/ChatSessionContext.tsx` (modifié, API publique conservée) | 3 | aucune régression sur les 6 pages ; `session_id` serveur présent |
| 5 | Raccordement Main Workbench | `src/pages/main-workbench/MainWorkbench.tsx` (modifié) | 4 | message → 202 → relecture → persistance confirmée |
| 6 | Raccordement AI Control Center | `src/pages/ai-control-center/AIControlCenter.tsx` (modifié) | 4 | session créée côté serveur, identique dans les deux vues |
| 7 | Indicateur santé/capacités | `src/App.tsx` ou bandeau dédié (modifié) | 3 | `/health` et `/capabilities` affichés avec statut réel |
| 8 | Vérification CORS et erreurs | aucun fichier modifié | 5, 6 | préflight OPTIONS accepté ; backend arrêté → message clair côté UI |
| 9 | Nouvelles routes backend modèles/réglages | `backend/app.py` (modifié) | — | `GET /models` et `PUT /settings/model-selection` → 200 |
| 10 | Raccordement Model Manager | `src/pages/model-manager/ModelManager.tsx` (modifié) | 9 | liste réelle, aucun statut « disponible » non vérifié |
| 11 | Routes mémoire / métriques / intégrations | `backend/app.py` (modifié) | — | 4 routes → 200, données datées et source identifiée |
| 12 | Raccordement Knowledge Hub, System Monitor, Agents & Tools | 3 pages (modifiées) | 11 | données réelles ; mentions « prototype » retirées seulement si vérifiées |

**Ordre recommandé** : 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8, puis 9 → 10, puis 11 → 12.
Aucune étape ne doit démarrer avant validation de la précédente. **Les étapes 1 à 8 ne touchent pas au backend** et suffisent à rendre la conversation réellement persistante.

---

## 6. BLOCAGES ET POINTS À TRANCHER

| # | Blocage / décision | Nature |
|---|---|---|
| C1 | Le backend ne produit aucune réponse assistant (`accepted_no_model`). Raccorder le frontend rendra la conversation persistante mais **toujours sans réponse IA**. | fonctionnel — décision produit nécessaire |
| C2 | 5 fonctionnalités sur 12 dépendent de routes backend inexistantes. Les raccorder exige de modifier `backend/app.py`, ce qui sort du périmètre « frontend seul ». | architectural |
| C3 | Divergence de contrat : `execution.status` renvoie `accepted_no_model` au lieu de `completed` ; `citations` absent. Le contrat v0.1 doit être aligné ou le backend corrigé. | documentaire / contrat |
| C4 | Les pièces jointes ne sont pas acceptées par le backend. Le bouton trombone ne peut pas fonctionner sans nouvelle route ou nouveau champ. | fonctionnel |
| C5 | Aucune authentification ni permission côté backend. Toute personne sur la machine peut appeler l'API locale. À traiter avant tout usage réel de données sensibles. | sécurité |
| C6 | Origine CORS : Vite écoute sur `::1` ; l'origine réelle en dev est `http://localhost:5173`. La valeur `127.0.0.1` présente dans la configuration actuelle ne correspond pas au serveur de développement réel. | configuration |
| C7 | Le frontend n'a **aucun routeur** : impossible de partager un lien vers une session ou une page. Un `session_id` ne peut pas être transmis par URL. | architecture frontend — décision nécessaire |
| C8 | Aucun test automatisé frontend (pas de Vitest, pas de Playwright dans `package.json`). La validation restera manuelle sauf ajout d'outillage. | outillage |
| C9 | Le workspace Cline actif est `C:\Users\hp\AppData\Local\Cline` : les règles de projet HORIZON ne sont pas chargées dans cette session. | process |

---

## 7. FICHIERS EXAMINÉS (lecture seule)

`src/App.tsx`, `src/main.tsx`, `src/shared/ChatSessionContext.tsx`, `src/settings/theme.ts`, `src/settings/types.d.ts`, les 6 pages de `src/pages/*`, `backend/app.py`, `backend/.env.example`, `backend/README.md`, `docs/contracts/CORE_API_CONTRACT_v0.1.md`, `docs/contracts/capabilities.example.json`, `package.json`, `vite.config.ts`, `tsconfig.app.json`.

**Aucun fichier de ces sources n'a été modifié, créé ou supprimé.** Seul ce rapport a été créé, sur votre demande explicite.



