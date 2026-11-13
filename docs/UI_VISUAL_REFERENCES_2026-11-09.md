# PHASE 12 — Références visuelles : cartographie et application

Date : 2026-11-09 · Build : 2117 modules (CSS 98,46 kB / JS 455,70 kB)
Captures : `docs/captures/avant-*.png` et `docs/captures/apres-*.png` (1440 × 950, via CDP).

---

## 1. Cartographie page par page

| Référence | Page cible | Page réelle retenue | Statut |
|---|---|---|---|
| 1 — Enterprise AI Platform | Poste de pilotage, supervision | `/cockpit` | **partielle** (voir §6) |
| 2 — Ask Me Anything | Main Workbench, accueil conversationnel | `/workbench` | **appliquée** |
| 3 — Workflow Builder | Missions, orchestration, workflows | `/orchestrators` | **appliquée** |
| 4 — Systems Overview | Vue d'ensemble des projets | `/projects` | **appliquée** |

Aucune page n'a été reconstruite : les compositions ont été **insérées** au-dessus des contenus
existants, qui restent fonctionnels (formulaires, sélection, rafraîchissement).

## 2. Composants réutilisables créés

| Composant | Rôle | Source de données |
|---|---|---|
| `src/components/MissionWorkflow.tsx` | Blocs d'étapes reliés, statuts, panneau de configuration | `GET /api/v1/missions`, `GET /api/v1/missions/{id}`, `GET /api/v1/orchestrators` |
| `src/components/ProjectOverview.tsx` | Bandeau de synthèse, cartes de projets, chronologie | `GET /api/v1/projects`, `GET /api/v1/missions` |
| `src/components/AskHero.tsx` | Accueil épuré + onde animée | `useChatSession()` (`status`, `execution.provider_id`, `messages`) |
| `src/components/CoreActivity.tsx` (phase précédente) | États réels du moteur + pipeline | mission active, exécution |

Classes CSS ajoutées (jetons de thème existants uniquement) : `wf-canvas`, `wf-chain`, `wf-link`,
`wf-start`, `wf-node*`, `so-header`, `so-kpi*`, `so-card`, `so-bar`, `so-dot*`, `ask-hero`,
`ask-frame*`, `ask-title`, `ask-wave*`, `ask-hint` + `@keyframes ask-breathe`.

## 3. Adaptations appliquées

### Référence 3 → orchestration (Workflow Builder)
- Colonne de missions réelles (sélection) · **canvas horizontal de blocs** (une carte par étape
  enregistrée, connecteurs entre étapes, couleur par statut `pending/running/completed/failed/skipped`,
  orchestrateur affecté sur chaque bloc) · **panneau de configuration latéral** (statut, priorité,
  orchestrateur, étapes terminées, points de contrôle, mise à jour) · messages explicites pour
  `paused`, `failed`, `running`, `completed`.
- Une mission sans étape affiche un message explicite : **aucun bloc inventé**.
- Branches : non représentées, car le modèle de données ne décrit pas de branches
  (`mission_steps` est une séquence ordonnée). Aucune branche fictive n'a été dessinée.

### Référence 4 → projets (Systems Overview)
- Bandeau de synthèse : projets, actifs, missions, en cours (chiffres réels).
- **Cartes de projets** : statut, description, nombre de missions et d'orchestrateurs,
  progression = `missions terminées / missions du projet` (aucune valeur inventée).
- **Chronologie** : 7 dernières missions triées par `updated_at`, pastille colorée par statut.
- Les listes et formulaires existants restent accessibles sous la vue d'ensemble.

### Référence 2 → workbench (Ask Me Anything)
- En-tête réduit ; titre principal remplacé par un **cadre centré** « Demandez ce que vous
  voulez… », largeur maximale 620 px, une seule surface.
- **Onde animée** : animée **uniquement** pendant une requête réelle (`status === 'loading'`) ;
  au repos statique et atténuée. `prefers-reduced-motion` désactive l'animation.
- Message sous l'onde : état réel du moteur (« aucun fournisseur IA configuré » tant que
  `execution.provider_id` est absent).
- Le cadre disparaît dès le premier message : la conversation reprend la priorité.

## 4. Captures avant / après

| Page | Avant | Après | Preuve de rendu réel (mesuré dans le DOM) |
|---|---|---|---|
| cockpit | **non disponible** (voir note) | `apres-cockpit.png` (132 Ko) | `ws-shell` présent, 0 débordement |
| workbench | `avant-workbench.png` (55 Ko) | `apres-workbench.png` (99 Ko) | `ask-frame` = 1, 0 débordement |
| projects | `avant-projects.png` (88 Ko) | `apres-projects.png` (120 Ko) | `.so-card` = 4 (3 projets + chronologie), 0 débordement |
| orchestrators | `avant-orchestrators.png` (68 Ko) | `apres-orchestrators.png` (80 Ko) | `.wf-node` = 1 (1 étape réellement en base) |

Les compteurs sont issus de `document.querySelectorAll(...)` exécuté dans la page réelle (CDP).

> **Note d'exactitude sur le cockpit** — `avant-cockpit.png` et `apres-cockpit.png` ont le **même
> MD5** (`BA7D1E37EA5B77A3018508539E52E921`) : la capture dite « avant » a en réalité été prise
> après la refonte des panneaux de la phase 2 (le fichier a été conservé pour ne rien supprimer).
> Aucune image « avant » authentique du cockpit n'existe donc pour cette phase. Le cockpit n'a
> d'ailleurs **reçu aucune modification visuelle en phase 12** : il est cité comme déjà conforme
> à la référence 1 (trois zones, indicateurs latéraux, accents cyan) et non comme retravaillé.

## 5. Vérifications

- `npm run build` : **succès** (2117 modules, CSS 98,46 kB, JS 455,70 kB).
- Aucun débordement horizontal sur les 4 pages à 1440 × 950 (`scrollWidth === clientWidth`).
- Données identiques avant/après : 3 projets, 1 mission, 1 orchestrateur, 1 élément en file.
- Aucun endpoint modifié pour cette phase ; aucune migration ; aucune donnée supprimée.
- Thèmes : les nouveaux composants n'utilisent que les variables existantes (`--accent`, `--card`,
  `--surface`, `--hairline`, `--foreground`, `--muted-foreground`) : les 6 thèmes × 6 accents
  restent applicables.

## 6. Écart assumé — Référence 1 (Enterprise AI Platform)

Le cockpit satisfait déjà l'organisation en trois zones, les indicateurs synthétiques latéraux et
les accents cyan mesurés (validés en phase précédente : 280/330 px, repli indépendant, persistance).
En revanche, **le graphe central des relations** (projets ↔ missions ↔ orchestrateurs ↔ connexions)
**n'a pas été implémenté** dans cette passe : il demande un rendu SVG dédié et une vérification de
lisibilité sur les thèmes clair et contraste élevé.

Maquette décrite pour une prochaine itération :
- colonnes `Projets → Missions → Orchestrateurs`, liens courbes colorés par statut de mission ;
- nœud central « HORIZON CORE » ;
- panneau latéral de synthèse (déjà en place via le bandeau 4 indicateurs du cockpit).

Aucune modification de page n'est donc associée à cette référence : elle n'a pas été appliquée en
phase 12. La capture `apres-cockpit.png` documente l'état courant (hérité de la phase 2), pas une
application de la référence 1.

## 7. Problèmes restants

1. Référence 1 non appliquée (§6).
2. Onde du workbench animée en CSS uniquement : non mesurée en fréquence d'images.
3. Branches de workflow non représentées (le modèle de données ne les décrit pas).
4. Workflow en lecture seule : aucun réordonnancement ni réaffectation (aucun endpoint dédié).
   Aucun bouton inopérant n'a été ajouté.
5. Aucune vérification visuelle humaine des 6 thèmes sur les nouveaux composants : seules la
   compilation et les mesures DOM/CDP ont été exécutées.
6. Référence 2 : le cadre conversationnel n'apparaît que si la session est vide ; une fois la
   conversation commencée, il n'est plus visible (comportement voulu, non mesuré visuellement).

## 8. Reproductibilité des captures

Script réellement utilisé (hors dépôt, non versionné) :
`C:\Users\hp\AppData\Local\Cline\_horizon_shots.mjs`

- Chrome headless piloté par CDP sur `--remote-debugging-port=9224`, fenêtre 1440 × 950 ;
- `Page.captureScreenshot` par page, puis mesure `document.documentElement.scrollWidth` vs
  `clientWidth` et comptage `querySelectorAll` des composants de référence ;
- usage : `node _horizon_shots.mjs <préfixe>` → `docs/captures/<préfixe>-<page>.png`.

Prérequis : backend sur `127.0.0.1:8000` (vérifié 200 sur `/api/v1/health`, `/api/v1/sync/status`,
`/api/v1/projects`, `/api/v1/integrations`).