# HORIZON CENTRAL AI — Poste de pilotage central, thèmes et audit hybride

Document de réalisation (2026-11-09). Aucune fonctionnalité existante n'a été
supprimée : les six espaces d'origine restent accessibles.

## 1. Audit de l'existant (avant modification)

| Élément constaté | Conséquence |
|---|---|
| 8 pages routées (`/workbench`, `/projects`, `/models`, `/orchestrators`, `/catalog`, `/memory`, `/control`, `/monitor`) + `/sync` | navigation fragmentée : piloter demandait de changer de page en permanence |
| Couleurs figées dans chaque page (inventaire : 200 occurrences `border-white`, 158 `bg-white`, 140 `text-slate-500`, 104 `text-white`, 57 `text-cyan-300`…) | thème unique sombre non modifiable |
| `src/main.tsx` forçait le mode clair OFF (`document.documentElement.classList.remove('dark')`) et bloquait toute évolution de thème | aucun pilotage du thème |
| `src/settings/theme.ts` (généré MagicPath) contient des jetons `%INJECTED_THEME%` inutilisés | fichier conservé tel quel, jamais modifié |
| `index.css` importait une police Google distante | dépendance réseau évitable en mode hors ligne |

## 2. Poste de pilotage central (`/cockpit`)

Nouvelle route **par défaut** (`/` redirige vers `/cockpit`). Composant
`src/pages/cockpit/Cockpit.tsx`.

- **Zone centrale** : conversation permanente avec HORIZON CORE (contexte de
  session réel : `ChatSessionContext`), saisie, envoi, état d'exécution renvoyé
  par le backend, avertissements, bouton **« Planifier avec HORIZON CORE »**
  (`POST /api/v1/core/plan`). Sans modèle vérifié, la réponse reste `no_model`.
- **Panneau latéral gauche** : projets (réels), missions du projet sélectionné,
  historique des sessions (+ nouvelle session), accès rapide vers les espaces.
- **Panneau contextuel droit** : orchestrateurs mobilisés, ressources
  (orchestrateurs actifs, fournisseurs, modèles vérifiés, compteurs de la base),
  progression des missions du projet, **état des connexions** (backend,
  sondage Internet mesuré, sync distante, file locale, authentification).
- **Espaces secondaires en tiroirs** : Modèles, Mémoire, Outils & agents,
  Sécurité, Synchronisation, Supervision, Paramètres. Les tiroirs **réutilisent
  les pages existantes** (`ModelManagerLive`, `KnowledgeMemoryLive`,
  `AgentsToolsCatalog`, `SyncCenter`, `SystemMonitorLive`) : aucune duplication,
  aucune fonctionnalité perdue.
- Panneaux gauche et droit repliables ; en-tête avec état Internet, thème
  courant et bouton d'actualisation.

Le contexte de conversation accepte désormais `/cockpit` et `/cockpit/:sessionId`.

## 3. Gestionnaire de thèmes (`src/theme/`)

| Fichier | Rôle |
|---|---|
| `theme.ts` | modèle, valeurs par défaut, lecture/écriture défensives, résolution automatique (système + horaires), variables du thème personnalisé |
| `ThemeProvider.tsx` | contexte React, application au DOM, écoute des préférences système, persistance |
| `ThemeControls.tsx` | interface de personnalisation |
| `index.ts` | exports publics |

Thèmes livrés : **Clair**, **Sombre** (défaut, identité d'origine), **Confort
visuel** (contraste maîtrisé), **Contraste élevé** (accessibilité),
**Automatique** (préférences système, puis horaires si activés), **Personnalisé**
(fond, panneaux, texte, accent + base de contraste).

Palettes d'accentuation : Cyan (origine), Bleu, Violet, Émeraude, Ambre, Rose —
assombries automatiquement en thème clair. Les accents sont propagés à toute
l'interface, y compris aux pages anciennes (voir §4).

Comportement vérifié par conception et par code :

- changement **instantané** (variables CSS, aucun rechargement) ;
- **persistance** dans `localStorage['horizon-local-ai:theme:v1']` ;
- **automatique** sans jamais écraser un choix manuel : dès que l'utilisateur
  choisit un thème explicite, le mode automatique ne s'applique plus ;
- horaires personnalisables (jour dès / nuit dès), recalculés chaque minute ;
- `prefers-color-scheme` et `prefers-reduced-motion` respectés ;
- changement de thème progressif (0,18 s) sauf si l'utilisateur demande la
  réduction des animations ;
- contraste élevé : focus visible renforcé ;
- mise en page responsive (grille `lg:grid-cols-…`, panneaux repliables,
  `@media(max-width:900px)` pour la navigation).

## 4. Passerelle de thème (« compat layer »)

Les pages existantes utilisent des classes de couleur figées. Plutôt que de
réécrire neuf pages (risque de régression fonctionnelle), `src/index.css` ajoute
une couche de règles **hors `@layer`** — donc prioritaires sur les utilitaires
Tailwind — qui rattachent ces classes aux jetons du thème actif :

- fonds de page et de panneaux (`bg-[#0A0B10]`, `bg-[#12151e]`, `bg-[#141721]`…) ;
- textes (`text-white`, `text-slate-100` → `--foreground` ; `text-slate-400/500/600` → `--muted-foreground`) ;
- bordures et surfaces translucides (`border-white/*` → `--hairline`, `bg-white/*` → `--hover`) ;
- **accents cyan → jetons d'accent** : changer de palette recolore réellement toute l'application ;
- états sémantiques (succès, avertissement, danger) adaptés à la lisibilité en thème clair.

Vérification dans le build : **156 sélecteurs `[class~=…]`** présents dans
`dist/assets/*.css`. Aucune page n'a été réécrite : structure et comportement
inchangés, seules les couleurs suivent le thème.

## 5. Vérification réelle de l'architecture hybride

| Exigence | Test réellement exécuté | Résultat mesuré | Statut |
|---|---|---|---|
| Démarrage et fonctionnement local sans Internet | instance locale lancée avec sonde `127.0.0.1:1` (port fermé) | `/health` 200, `/projects` 200, `/sessions` 200, `/capabilities` 200, `/cockpit` 200 ; `/sync/status` → `online:false` + erreur mesurée | **Opérationnel** |
| Persistance des données locales | arrêt complet du moteur, puis redémarrage | 3 projets et 1 écriture en file retrouvés à l'identique | **Opérationnel** |
| Connexion réelle à Supabase | variables absentes : appel `push`/`pull` | `provider: none`, `status: not_configured`, aucune donnée modifiée | **Non configuré** |
| Services distants autorisés (fournisseurs IA) | lecture du registre et de la sélection | 0 fournisseur, 0 vérifié ; `/core/plan` répond `no_model` | **Non configuré** |
| Synchronisation bidirectionnelle | impossible sans fournisseur | routes et moteur présents, réponse honnête `not_configured` | **Bloqué (prérequis)** |
| Gestion des conflits local/distant | conflit créé par le dépôt → lu via API → résolu via API | `count` 1 → `resolved 1` → `count` 0 ; aucune donnée écrasée | **Opérationnel** |
| Reprise après interruption réseau | worker lancé avec `HORIZON_SYNC_AUTO=1` (45 s), sans fournisseur | démarre, ne plante pas, ne touche à rien ; hors ligne correctement détecté | **Partiel** |
| Continuité du travail sur plusieurs machines | dépend de la connexion Supabase | non exécutable | **Non configuré** |
| Aucune connexion présentée comme active sans preuve | lecture de l'interface et de `/sync/status` | affiche « non configurée » / « hors ligne » et les valeurs brutes des sondes | **Opérationnel** |
| Aucune donnée fictive ni réponse IA simulée | appel de planification sans modèle | `no_model` assumé, aucun plan fabriqué | **Opérationnel** |
| Thèmes (clair, sombre, auto, confort, contraste, personnalisé + 6 accents) | build + inspection du CSS livré | blocs `[data-theme=…]` et `[data-accent=…]` présents, `color-mix` ×214, persistance localStorage | **Opérationnel** |
| Poste de pilotage central | rendu réel de `/cockpit` + journal du backend | DOM de 30 233 caractères ; appels réels `/projects`, `/orchestrators`, `/models`, `/system/status`, `/sync/status`, `/missions` tous en 200 | **Opérationnel** |


## 6. Compte rendu : terminé / partiel / bloqué

**Terminé (vérifié)**

1. Poste de pilotage central unique avec les trois zones et sept espaces
   secondaires en tiroirs, servant réellement les données locales.
2. Gestionnaire de thèmes : 6 modes, 6 palettes d'accent, persistance locale,
   mode automatique (système + horaires), personnalisé, accessibilité,
   responsive, transitions douces.
3. Cohérence visuelle de toutes les pages existantes via la passerelle de thème
   (aucune page réécrite, aucune fonctionnalité retirée).
4. Fonctionnement hors ligne réel (mesuré), persistance locale après
   redémarrage, gestion de conflits de bout en bout, aucune donnée fictive.
5. Zéro ressource réseau obligatoire : la police distante a été retirée du CSS
   (seul un lien de documentation `tailwindcss.com` subsiste dans un commentaire).

**Partiel**

1. Reprise après interruption réseau : le worker et la détection de connectivité
   fonctionnent, mais la reprise réelle d'un envoi ne peut pas être démontrée
   sans fournisseur distant configuré.

**Bloqué (prérequis humain)**

1. Connexion réelle à Supabase : nécessite un projet et une clé d'API à placer
   dans `backend/.env` (`HORIZON_SUPABASE_URL`, `HORIZON_SUPABASE_KEY`).
2. Synchronisation bidirectionnelle et continuité multi-machines : dépendent
   directement du point précédent.
3. Fournisseur IA : aucune clé disponible → la planification répond `no_model`.

## 7. Fichiers créés / modifiés

**Créés** : `src/theme/theme.ts`, `src/theme/ThemeProvider.tsx`,
`src/theme/ThemeControls.tsx`, `src/theme/index.ts`,
`src/pages/cockpit/Cockpit.tsx`, `docs/UI_COCKPIT_AND_THEMES.md`.

**Modifiés** : `src/index.css` (thèmes, jetons, passerelle, navigation),
`src/main.tsx` (thème délégué au provider, plus aucun forçage), `src/App.tsx`
(route `/cockpit` par défaut, sélecteurs de thème et d'accent dans l'en-tête),
`src/shared/ChatSessionContext.tsx` (`/cockpit` reconnu comme espace de
conversation). Aucun fichier supprimé, déplacé ou renommé ; `src/settings/theme.ts`
(généré) est conservé intact.

## 8. Limites connues

- Une fenêtre déjà ouverte conserve le JavaScript qu'elle a chargé : pour voir
  un nouveau build, il faut la rouvrir (le shell HTML est servi en `no-store`).
- Aucune capture d'écran automatisée : la conformité visuelle est vérifiée par
  le CSS livré, le DOM rendu et les appels réseau réels, pas pixel par pixel.
- Le tiroir Sécurité n'expose volontairement aucune saisie de jeton : la valeur
  reste dans `backend/.env` (aucun secret ne transite par l'interface).

