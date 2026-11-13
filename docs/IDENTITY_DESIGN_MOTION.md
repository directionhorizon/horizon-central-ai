# HORIZON CENTRAL AI — Identité, design system et motion design

Document de réalisation (2026-11-09). Aucune fonctionnalité existante retirée.

## 1. Identité officielle

Nom officiel : **HORIZON CENTRAL AI**. Renommé dans tous les éléments visibles.

| Emplacement | Avant | Après |
|---|---|---|
| Titre de la fenêtre / onglet (`index.html`) | HORIZON LOCAL AI | **HORIZON CENTRAL AI** |
| Métadonnée de description | …poste de commande local… | …poste de commande **central**… |
| En-tête de navigation (marque) | HORIZON / LOCAL AI | **HORIZON / CENTRAL AI** |
| En-tête du poste de pilotage | HORIZON / POSTE DE PILOTAGE | **HORIZON CENTRAL AI / POSTE DE PILOTAGE** |
| Libellé de version dans la barre | INTERFACE INTEGRATION · PREVIEW | **POSTE DE PILOTAGE CENTRAL** |
| Titre de l'API (`/openapi.json`, Swagger) | HORIZON Core API | **HORIZON CENTRAL AI — Core API** |
| Prompt système de planification | planificateur de HORIZON LOCAL AI | planificateur de **HORIZON CENTRAL AI** |
| Lanceurs `HORIZON.ps1` / `HORIZON.bat` / `HORIZON-Stop.ps1` / `start.ps1` | HORIZON LOCAL AI | **HORIZON CENTRAL AI** |
| Raccourci Windows du Bureau | HORIZON LOCAL AI.lnk | **HORIZON CENTRAL AI.lnk** (l'ancien a été remplacé) |
| README, docs produit | HORIZON LOCAL AI | **HORIZON CENTRAL AI** |

### Exceptions techniques conservées (compatibilité)

Ces identifiants ne sont pas visibles par l'utilisateur et ne doivent pas changer
sans migration de données :

| Identifiant | Raison |
|---|---|
| Dossier `…\HORIZON LOCAL AI\…\HORIZON_LOCAL_AI` | chemins réels sur disque (scripts, README, raccourci) |
| `package.json` → `horizon-local-ai-interfaces` | nom du paquet npm (verrouillé par `package-lock.json`) |
| `localStorage['horizon-local-ai:theme:v1']` | conserve les préférences de thème déjà enregistrées |
| `localStorage['horizon-local-ai:last-session:v1']` | conserve la dernière session de conversation |
| `horizon.db`, `HORIZON_*` (variables d'environnement) | base et configuration existantes |
| `docs/contracts/CORE_API_CONTRACT_v0.1.md`, `RELEASE_NOTES_1.0.0.md`, `.clinerules/…` | documents historiques (tracés, non modifiés) |

## 2. Design system

Ajouté dans `src/index.css` (à la suite des jetons de thème existants) :

- **Jetons de rythme et d'élévation** : espacements 4→32 px, rayons 8/12/16 px,
  trois niveaux d'ombre dérivés de `--shadow-color`.
- **Jetons de mouvement** : `--hz-motion-fast` 120 ms, `--hz-motion` 200 ms,
  `--hz-motion-slow` 320 ms, deux courbes d'accélération.
- **Composants communs** : `.hz-card`, `.hz-panel`, `.hz-kpi`, `.hz-badge`
  (variantes ok/warn/danger/accent), `.hz-btn` (primaire, fantôme, icône),
  `.hz-input/.hz-textarea/.hz-select`, `.hz-list-item`, `.hz-alert`
  (info/warn/danger), `.hz-track` (progression), `.hz-eyebrow`, `.hz-title`,
  `.hz-subtitle`, `.hz-metric`, `.hz-hint`, `.hz-code`, `.hz-dot`.
- **Finitions globales** : barres de défilement discrètes (y compris sur tous les
  conteneurs `overflow-y-auto` des pages existantes), sélection de texte teintée
  par l'accent, anneau de focus homogène.

Tous les composants consomment les variables du thème : ils suivent
automatiquement les 6 thèmes et les 6 palettes d'accent.

## 3. Motion design

| Animation | Usage | Durée |
|---|---|---|
| `hz-fade-up` (`.hz-enter`, `.hz-view`) | apparition des panneaux et changement de page | 320 ms / 200 ms |
| `hz-fade-in` (`.hz-overlay`) | voile des tiroirs | 200 ms |
| `hz-slide-in-right` (`.hz-drawer`) | ouverture d'un espace secondaire | 320 ms |
| `hz-slide-up-panel` (`.hz-panel-in`) | panneau contextuel | 200 ms |
| `hz-pop` (`.hz-pop`) | apparition d'un badge/notification | 120 ms |
| `hz-live` / `hz-status-ring` (`.hz-live`, `.hz-live-dot`) | **uniquement** pendant une opération réellement en cours | 1,4–1,9 s |
| `.hz-sweep` | progression d'un traitement réel | 1,4 s |
| `.hz-lift` | élévation au survol des éléments interactifs | 200 ms |

Échelonnement `hz-enter--1…4` (40 ms par palier) pour les trois panneaux.
**Aucune animation permanente** n'est affichée sans opération réelle :
`hz-live` et `hz-sweep` ne sont appliqués qu'aux indicateurs d'activité véritables.

`prefers-reduced-motion` neutralise animations et transitions (durée 0,001 ms,
`animation: none` sur les classes concernées) : vérifié par mesure.

## 4. Refonte de l'espace de pilotage

- **Bandeau d'état** (4 indicateurs) : projet actif (statut, missions,
  orchestrateurs), missions du projet (dont en cours / en échec), orchestrateurs
  actifs / total + fournisseurs et modèles vérifiés, **interventions requises**.
- **Bloc « Éléments nécessitant une décision ou une action »** : liste dérivée
  uniquement d'états mesurés (service local injoignable, sync distante non
  configurée, conflits ouverts, écritures en échec, aucun fournisseur IA, aucun
  modèle vérifié, missions en échec, jeton administrateur actif). Aucun élément
  inventé : la liste est vide quand tout est sain.
- **Navigation** : marque retravaillée (tuile dégradée à l'accent, deux lignes
  HORIZON / CENTRAL AI), onglets en pilules avec transition, barre collante
  translucide (effet verre), indicateur actif teinté par l'accent, défilement
  horizontal sans barre visible.
- **Panneaux** : trois colonnes avec apparition échelonnée, en-têtes homogènes,
  états vides explicites, panneaux gauche/droit repliables.
- **Tiroirs** : voile assombri + glissement latéral, contenu = pages existantes
  réutilisées (Modèles, Mémoire, Outils & agents, Sécurité, Synchronisation,
  Supervision, Paramètres).
- Débordements maîtrisés : hauteurs maximales explicites, défilement local
  discret, aucune barre de défilement superflue sur la page.

## 5. Configuration et lancement

- Nouveau raccourci Windows : `HORIZON CENTRAL AI.lnk` (cible `HORIZON.bat`).
- Lanceur : `HORIZON.ps1` démarre le moteur local puis ouvre Edge/Chrome en mode
  application, avec la version en paramètre anti-cache.
- Aucune ressource distante : police Google retirée (seul un lien de
  documentation `tailwindcss.com` subsiste dans un commentaire CSS).

## 6. Tests réellement exécutés

Build de production : **2110 modules**, CSS 87,52 kB, JS 424,83 kB.

### Thèmes — mesures réelles (Chrome + DevTools Protocol)

Chaque scénario a réellement écrit la préférence dans `localStorage`, rechargé la
page, puis mesuré `getComputedStyle` après stabilisation.

| Scénario | Thème appliqué | Fond mesuré | Contraste | Animation | KPI |
|---|---|---|---|---|---|
| Sombre (défaut) | dark / cyan | rgb(10, 11, 16) | **18,79** | hz-fade-up 0,32 s | 4 |
| Clair | light / cyan | rgb(245, 247, 251) | **16,55** | hz-fade-up 0,32 s | 4 |
| Clair + Bleu | light / azure | rgb(245, 247, 251) | **16,55** | hz-fade-up 0,32 s | 4 |
| Confort + Vert | comfort / emerald | rgb(20, 22, 28) | **14,01** | hz-fade-up 0,32 s | 4 |
| Contraste élevé + Ambre | contrast / amber | rgb(0, 0, 0) | **21,00** | hz-fade-up 0,32 s | 4 |
| Automatique | light / rose | rgb(245, 247, 251) | **16,55** | hz-fade-up 0,32 s | 4 |
| Auto + horaires | light / violet | rgb(245, 247, 251) | **16,55** | hz-fade-up 0,32 s | 4 |
| Personnalisé | custom / violet | rgb(15, 20, 32) | **16,38** | hz-fade-up 0,32 s | 4 |

- 5 fonds distincts sur 8 scénarios (attendu : les trois variantes claires
  partagent le même fond).
- Tous les contrastes ≥ 14:1 (WCAG AAA largement dépassé).
- Préférence **persistante** : chaque scénario passe par un rechargement complet
  et le thème se réapplique → la persistance est démontrée.
- Mode automatique : suit la préférence système mesurée (`light` en headless) ;
  avec horaires 0 h→23 h, il reste clair — comportement conforme, jamais prioritaire
  sur un choix manuel.
- Classe figée d'une page existante (`bg-[#090c13]`) mesurée à
  `rgb(10, 11, 16)` = `--background` du thème : la passerelle fonctionne.
- `prefers-reduced-motion` forcé : **animation = none, durée 0 s** sur tous les
  scénarios ; thèmes et contrastes inchangés.

### Non-régression

- 10 routes API → 200 (`health`, `capabilities`, `projects`, `orchestrators`,
  `missions`, `documents`, `models`, `system/status`, `sync/status`, `sessions`).
- 11 routes SPA → 200 (`/`, `/cockpit`, `/workbench`, `/projects`, `/models`,
  `/orchestrators`, `/catalog`, `/memory`, `/control`, `/monitor`, `/sync`).
- Titre servi : `<title>HORIZON CENTRAL AI</title>` ; `openapi.json` →
  « HORIZON CENTRAL AI — Core API » ; Swagger UI idem.
- Données locales intactes : 3 projets, 1 orchestrateur, 1 mission, 1 document,
  6 sessions, file de synchronisation conservée.

## 7. Incident rencontré et traité

Le disque `C:` est tombé à **0 Mo libre** pendant les tests (profils Chrome de
test + cache npm de 1,1 Go). Nettoyage effectué : profils de test supprimés
(≈57 Mo) et `npm cache clean --force` (≈665 Mo) → **696 Mo libres**. Aucune
donnée du projet n'a été touchée.

## 8. Limites restantes

- Aucune capture d'écran automatique : la conformité visuelle est établie par
  mesures de styles calculés, DOM rendu et appels réseau réels.
- Une fenêtre déjà ouverte conserve son JavaScript : rouvrir le raccourci après
  un build.
- La synchronisation Supabase réelle et le fournisseur IA restent non configurés
  (prérequis humains) — voir `docs/SUPABASE_MIGRATION_STRATEGY.md`.