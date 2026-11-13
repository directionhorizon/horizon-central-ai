# HORIZON CENTRAL AI — Audit et amélioration de l'interface

Date : 2026-11-09 · Version API : **0.4.0** · Schéma : migration **5**
Périmètre : amélioration de l'application existante (aucune réécriture, aucune suppression).

---

## 1. État initial constaté

- 11 pages servies par le SPA (`/cockpit`, `/workbench`, `/projects`, `/models`,
  `/orchestrators`, `/catalog`, `/memory`, `/control`, `/monitor`, `/sync`) — toutes en 200.
- Le cockpit possédait **deux panneaux latéraux repliables**, mais **sans redimensionnement,
  sans rail de réouverture et sans persistance** : l'état revenait à « ouvert » à chaque
  rechargement.
- Grille figée `lg:grid-cols-[260px_1fr_320px]` : sur 1024–1279 px le contenu central était
  comprimé et la barre de navigation (11 onglets) tombait à ~81 px de largeur utile.
- Système de thèmes complet (6 thèmes × 6 accents) avec persistance déjà opérationnel.
- Animations CSS existantes (`hz-fade-up`, `hz-fade-in`, `hz-slide-in-right`,
  `hz-slide-up-panel`, `hz-pop`, `hz-live`) : présentes, mais **aucune transition de panneau**
  ni animation de tiroir.
- Aucune représentation de l'activité de HORIZON CORE ni de pipeline de mission.
- Aucun registre centralisé de connexions (aucune table correspondante en base).
- **Informations techniques exposées** dans l'interface et dans les réponses API publiques :
  cible de la sonde réseau (`1.1.1.1:443`), noms de variables d'environnement, chemin de la
  base locale, répertoire `dist`, chemin du disque, mention `backend/.env`.

## 2. Problèmes identifiés

| # | Problème | Gravité |
|---|---|---|
| 1 | Panneaux non redimensionnables / non persistés / pas de rail quand repliés | élevée |
| 2 | Aucun tiroir tablette/mobile : les panneaux s'empilaient au-dessus du contenu | élevée |
| 3 | Contenu central comprimé à 1024–1279 px | élevée |
| 4 | Onglets de navigation réduits à 81 px à 1024 px | moyenne |
| 5 | Aucune transition d'ouverture/fermeture de panneau | moyenne |
| 6 | Activité de HORIZON CORE et pipeline de mission non représentées | moyenne |
| 7 | Aucun espace « Connexions et intégrations » | élevée |
| 8 | Fuite d'informations techniques (sonde, chemins, variables) | élevée |
| 9 | `/api/v1/system/desktop` renvoyait `database_path` et `dist_dir` | élevée |

## 3. Modifications effectuées

### 3.1 Espace de travail à trois zones (Phase 2)

- Nouveau hook `src/workspace/useWorkspaceLayout.ts` : largeurs bornées (216–520 px), repli
  indépendant gauche/droit, rail de réouverture (52 px), **persistance `localStorage`
  (`horizon-central-ai:workspace:v1`)**, commande de restauration, classification de la fenêtre
  (desktop ≥ 1024, tablette ≥ 768, mobile < 768).
- Cockpit refactoré sur ce socle : `ws-shell`, `ws-pane`, `ws-handle`, `ws-rail`, `ws-backdrop`.
- Poignées de redimensionnement à la souris (`pointerdown` + `pointermove`), curseur
  `col-resize`, sélection verrouillée pendant le glissement.
- Tablette/mobile : panneaux convertis en **tiroirs** (position fixe, largeur
  `min(90vw, 340px)`, fond assombri cliquable pour fermer).
- Bouton « Disposition » dans l'en-tête : restaure les deux panneaux et les largeurs par défaut.
- Le panneau replié **reste accessible** : rail vertical avec bouton de réouverture explicite
  (« Afficher la navigation » / « Afficher le contexte »).

### 3.2 Responsive (Phase 3)

- 1024–1279 px : largeurs de panneaux **bornées** (`min(232px, préférence)`) sans écraser la
  préférence utilisateur ; libellé de version masqué ; sélecteurs de thème compactés.
- `#root` / `.horizon-page` : `overflow-x: clip` (aucun débordement horizontal).
### 3.3 Motion design (Phase 4)

- `hz-slide-in-left` ajouté ; transitions réelles de panneaux et de tiroirs
  (`hz-slide-in-right`, `hz-fade-in` pour le fond).
- Nouveau composant `src/components/CoreActivity.tsx` :
  - `deriveCoreState()` : `idle · analyzing · planning · executing · verifying · delivered ·
    attention · error`, **déduits uniquement de faits observés** (`sending`, `planning`,
    `error`, `execution.status`, `mission.status`, statuts d'étapes) ;
  - `MissionPipeline` : 7 étapes (Demande → Analyse → Planification → Affectation →
    Exécution → Vérification → Livraison), états `done/current/pending/failed/paused` ;
  - aucun indicateur animé quand le système est inactif (`CoreActivityDot` renvoie `null`).
- Section « HORIZON CORE · état mesuré » en tête du panneau droit (état + pipeline réels).

### 3.4 Connexions et intégrations (Phase 5)

- Migration 5 : table `integrations` (name, category, method, endpoint, status, permissions,
  capabilities, api_key_env, last_checked_at, last_error, config_json, archived, horodatages)
  + deux index.
- `backend/horizon/repositories/integrations.py` : CRUD, archivage logique, `stats()`.
- `backend/horizon/routers/integrations.py` : `GET /catalog`, `GET`, `GET /{id}`, `POST`,
  `PATCH`, `DELETE` (archivage), `POST /{id}/test` (rôle admin).
  - **Aucune valeur secrète** : seul le *nom* de variable (`api_key_env`) est stocké ; la
    réponse contient `secret_present: bool` et `endpoint_host` (hôte seul, jamais le chemin).
  - **Test réel** : HTTP(S) via `httpx` (timeout 4 s) ou TCP (`socket`, timeout 3 s). Une fiche
    n'est `connected` qu'après un test réussi ; sinon `unavailable`, `not_configured`
    (variable absente) ou `partial` (aucun endpoint testable).
- Frontend : `src/pages/integrations/Integrations.tsx` (catégories, filtres, formulaire, test,
  archivage), `src/api/integrations.ts`, route `/integrations` + onglet « Connexions ».
- 9 catégories et 8 méthodes de connexion exposées par `GET /api/v1/integrations/catalog`.

### 3.5 Confidentialité (Phase 6)

- `GET /api/v1/system/desktop` : ne renvoie plus que `mode`, `version`, `ui_bundled`.
- `GET /api/v1/system/metrics` : le champ `disk.path` est retiré.
- `GET /api/v1/sync/status` : recentré sur le fonctionnel (`provider_configured`, `online`,
  `queue`, `worker_active`, `last_sync_at`, `note`) ; la cible de sonde, les variables
  attendues et le détail du worker ont disparu.
- Nouveau `GET /api/v1/admin/diagnostics` (rôle admin, consultation journalisée) : chemins,
  sonde, fournisseur, worker, métriques complètes, présence des variables de clés (booléens).
- Interface : plus aucune mention de sonde réseau, de variable d'environnement, de chemin de
  base ou de `.env` dans le cockpit et la page Synchronisation.

## 4. Fichiers créés

- `src/workspace/useWorkspaceLayout.ts`
- `src/components/CoreActivity.tsx`
- `src/pages/integrations/Integrations.tsx`
- `src/api/integrations.ts`, `src/api/diagnostics.ts`
- `backend/horizon/repositories/integrations.py`
- `backend/horizon/routers/integrations.py`, `backend/horizon/routers/diagnostics.py`
- `docs/UI_WORKSPACE_AUDIT_2026-11-09.md` (ce document)
- Outil de mesure : `C:\Users\hp\AppData\Local\Cline\_horizon_responsive_test.mjs`

## 5. Fichiers modifiés

`backend/horizon/schema.py` (migration 5) · `backend/app.py` (v0.4.0, routeurs, desktop) ·
`backend/horizon/routers/{sync,system,__init__}.py` · `backend/horizon/repositories/__init__.py` ·
`src/App.tsx` (route + onglet) · `src/pages/cockpit/Cockpit.tsx` ·
`src/pages/sync-center/SyncCenter.tsx` · `src/api/entities.ts` (contrats) ·
`src/config/env.ts` (routes) · `src/index.css` (espace de travail, responsive).

## 6. Composants réutilisés

`hz-card`, `hz-panel`, `hz-btn`, `hz-badge`, `hz-kpi`, `hz-alert`, `hz-input`, `hz-select`,
`hz-eyebrow`, `hz-hint`, `hz-live-dot`, `ThemeControls`, client `http` (retry/timeouts),
keyframes existantes, `lucide-react` (déjà présent).

## 7. Fonctionnalités réellement opérationnelles (prouvées)

- **Panneaux indépendants** (mesuré à 1440 px) : gauche 280 px / droite 330 px ; repli gauche →
  rail 52 px et **droite inchangée à 330 px** ; repli des deux → 0/0 + rail ; après
  rechargement de la page → **toujours repliés**
  (`{"leftCollapsed":true,"rightCollapsed":true}`) ; « Disposition » → retour à 280/330.
- **Redimensionnement** : poignées `block` (actives) à 1920/1440/1024, `none` ≤ 1023 px.
- **Responsive** : aucun débordement horizontal mesuré aux 5 largeurs (voir §10).
- **Registre de connexions** : création → 201 (endpoint masqué, `endpoint_present=False`) ;
  test réel → `{"status":"connected","detail":"HTTP 200","verified":true}` sur
  `http://127.0.0.1:8000/api/v1/health` ; test avec clé absente →
  `{"status":"not_configured","secret_present":false,"verified":false}` ; archivage → 200.
- **Cloisonnement des informations** : `/sync/status`, `/system/desktop`, `/system/metrics` ne
  contiennent plus aucune cible de sonde, chemin ni nom de variable (vérifié par scan).
- **Diagnostic protégé** : `/api/v1/admin/diagnostics` renvoie version 0.4.0, base présente,
  `dist` présent, sonde `1.1.1.1:443`, fournisseur `none`.
- **Non-régression données** : projets 3, missions 1, orchestrateurs 1, file de sync 1 ;
  11 routes SPA en 200 avec le titre « HORIZON CENTRAL AI » ; 46 routes dans OpenAPI.
- Build de production : 2114 modules, CSS 90,45 kB, JS 442,26 kB.

## 8. Fonctionnalités partiellement opérationnelles

- **États de HORIZON CORE** : 8 états dérivés de faits réels. « Coordination » et « sélection
  d'orchestrateur » ne sont pas exposés isolément par le backend : ils apparaissent via
  `planning` puis `executing` (affectation visible dans la pipeline). Aucune activité simulée.
- **Pipeline de mission** : dérivée des statuts réels (mission + étapes). Un statut non prévu
  retomberait sur `pending` (aucun état inventé).
- **Intégrations** : OAuth 2.0 proposé comme *méthode* mais **aucun flux OAuth implémenté**
  (état honnête : `pending`/`partial`, test HTTP/TCP seulement).
- **Diagnostic technique** : exposé par l'API uniquement ; pas d'écran dédié tant que le jeton
  administrateur n'est pas saisissable depuis l'interface.

## 9. Connexions non configurées

| Élément | État réel |
|---|---|
| Fournisseur LLM | aucun configuré → `/core/plan` répond `no_model` |
| Supabase (sync distante) | non configuré → `provider_configured: false`, mode 100 % local |
| OAuth (toute application) | non implémenté |
| Clés API de services tiers | aucune (seuls des noms de variables sont enregistrés) |

## 10. Résultats des tests responsive (mesurés via CDP)

| Largeur | scrollW / clientW | Débordement | Colonnes | Panneau gauche | Panneau droit | Poignée | Nav (scroll/client) |
|---:|---|---|---|---|---|---|---|
| 1920 | 1905 / 1905 | non | 5 | static 280 | static 330 | visible | 1443 / 977 |
| 1440 | 1425 / 1425 | non | 5 | static 280 | static 330 | visible | 1443 / 497 |
| 1024 | 1009 / 1009 | non | 5 | static 232 | static 258 | visible | 1443 / 254 |
| 768 | 753 / 753 | non | 1 | fixed 340 (tiroir) | fixed 340 (tiroir) | masquée | 1443 / 717 |
| 390 | 390 / 390 | non | 1 | fixed 340 (tiroir) | fixed 340 (tiroir) | masquée | 1443 / 354 |

*Captures d'écran* : aucune capture PNG exploitable dans cet environnement ; les valeurs
proviennent de la page réelle (CDP + `getComputedStyle`).

## 11. Résultats des tests de motion design

- Animations de panneau/tiroir : présentes et déclenchées par un changement d'état réel.
  **Non mesurées en durée/fréquence d'images** — à valider visuellement.
- `prefers-reduced-motion` : neutralisation globale vérifiée lors de la session précédente
  (mesurée) ; les nouvelles animations utilisent les mêmes jetons de mouvement.
- Aucune animation permanente : les indicateurs ne tournent que pendant une opération réelle.

## 12. Résultats de l'audit de confidentialité

Scan des réponses publiques sur `required_env`, `HORIZON_`, `C:\`, `1.1.1.1`, `dist_dir`,
`database_path`, `SQLite`, `backend/.env`, `api_key` :

| Route | Résultat |
|---|---|
| `/api/v1/health`, `/api/v1/sync/status`, `/api/v1/system/desktop`, `/api/v1/system/metrics` | **aucune fuite** |
| `/api/v1/system/status` | contient `HORIZON_ADMIN_TOKEN` (nom de la variable du jeton admin) |
| `/api/v1/integrations` | contient `api_key_env` (nom de champ) et le nom de variable saisi |
| `/api/v1/capabilities` | mentionne « SQLite » dans la description de la persistance locale |

Résiduels assumés : noms de variables (jamais de valeurs), mention du moteur de stockage.
Aucun secret n'est stocké en base, renvoyé par l'API, écrit dans les logs ni dans `localStorage`.

## 13. Problèmes restants

1. Aucun fournisseur LLM → la planification réelle reste impossible.
2. Supabase non configuré → la synchronisation distante réelle n'est pas démontrable.
3. Aucun flux OAuth implémenté (méthode annoncée, non fonctionnelle).
4. Pas d'écran de diagnostic technique (API seulement) — nécessite le jeton admin.
5. Motion non validée visuellement (aucune capture automatisée disponible).
6. Espace disque : ~0,6 Go libres ; aucun dépôt Git.
7. Données de test conservées : projet « Test Registry E2E » (archivé), orchestrateur
   « Test Orchestrator E2E » (désactivé), mission « Mission validation raccordement » (draft),
   fiche d'intégration « Backend local (auto-test) » (connectée, conservée comme exemple).
   La fiche « Service avec cle absente » a été archivée (suppression logique).

## 14. Actions nécessitant une autorisation humaine

1. **Choisir un fournisseur LLM** et fournir la clé (variable d'environnement côté backend).
2. **Fournir les clés Supabase** pour tester réellement la synchronisation distante.
3. **Valider visuellement** l'interface page par page (aucun test automatisé de rendu visuel).
4. **Autoriser l'activation du jeton administrateur** — seulement après avoir prévu la saisie du
   jeton côté interface, sinon `/api/v1/admin/*` devient inaccessible.
5. Décider du **nettoyage des données de test** listées au §13.7.