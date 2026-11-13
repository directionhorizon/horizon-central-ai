# HORIZON CENTRAL AI — Architecture Offline-First / Local-First

Document technique de l'adaptation « application de bureau Windows » demandée.
Rédigé le 2026-11-09. Aucune fonctionnalité existante n'a été supprimée.

## 1. Existant analysé avant modification

| Élément | État constaté |
|---|---|
| Backend | FastAPI 0.115 + Uvicorn, SQLite locale `backend/data/horizon.db`, monolithe modulaire `backend/horizon/` |
| Frontend | React 19 + Vite 6, build `dist/`, servi jusqu'ici uniquement par le serveur de développement Vite (port 5173) |
| Données | 100 % locales (projets, orchestrateurs, missions, documents, opérations, sessions) |
| Réseau | Adaptateur LLM OpenAI-compatible unique + métriques système + journal d'opérations |
| Lancement | `start.ps1` : backend + Vite en mode développement, dépendant d'un terminal |
| Absent | service de l'interface par le backend, détection réseau, file de synchronisation, gestion de conflits, lanceur de bureau |

Conséquence : l'application fonctionnait hors ligne **de fait**, mais rien ne le garantissait :
aucun détecteur de connectivité, aucune file d'attente, aucune règle de conflit, et
l'interface n'était pas servie par le processus local en mode production.

## 2. Écarts identifiés et adaptations retenues

| Exigence | Adaptation mise en œuvre | Fichier |
|---|---|---|
| Démarrer sans Internet | backend sert le build `dist/` (montage `/assets` + fallback SPA) ; aucune ressource externe dans `index.html` | `backend/app.py` |
| Ouvrir comme une application Windows | lanceur `HORIZON.ps1` + `HORIZON.bat` : démarre le moteur local puis ouvre Edge/Chrome en mode application (sans barre d'adresse), profil dédié | `HORIZON.ps1`, `HORIZON.bat` |
| Données locales toujours accessibles | SQLite + API locale inchangées ; l'UI lit `/api/v1/...` sur 127.0.0.1 | existant préservé |
| Connexion = services distants | fournisseur de synchronisation optionnel (Supabase REST/PostgREST) + fournisseurs LLM distants | `horizon/sync_provider.py` |
| Synchronisation au retour du réseau | worker de fond `HORIZON_SYNC_AUTO=1` (inactif par défaut), sinon boutons manuels dans l'UI | `horizon/sync_worker.py` |
| Détection de conflits sans écrasement | table `sync_conflicts` + statut `conflict` dans la file ; résolution humaine explicite | `horizon/repositories/sync.py` |
| Panne réseau = application utilisable | toutes les erreurs réseau sont capturées ; aucune route locale n'en dépend | `horizon/connectivity.py` |

## 3. Architecture cible (implémentée)

```
┌────────────────────────── Poste Windows (local) ──────────────────────────┐
│  Fenêtre Edge/Chrome en mode application  ──►  http://127.0.0.1:8000       │
│                                                    │                       │
│  Uvicorn / FastAPI  ──►  dist/ (interface compilée)                        │
│         │                                                                  │
│         ├─► SQLite  backend/data/horizon.db  (source de vérité locale)     │
│         ├─► sync_outbox  (file locale des écritures)                       │
│         ├─► sync_conflicts (conflits non résolus)                          │
│         └─► sync_worker  (optionnel, HORIZON_SYNC_AUTO=1)                  │
└────────────────────────────────────────────────────────────────────────────┘
                              │  si Internet + fournisseur configuré
                              ▼
              Supabase (PostgREST) / fournisseur LLM distant
```

Règles structurantes :

1. **La base locale est la source de vérité.** Aucune écriture n'attend le réseau.
2. **Toute écriture métier est journalisée dans `sync_outbox`** (create / update / delete),
   en plus du journal d'opérations existant. Le `delete` reste une suppression logique
   (archivage/désactivation) : rien n'est purgé physiquement.
3. **Aucun secret en base ni dans l'UI.** Seuls les *noms* de variables d'environnement
   sont référencés ; les valeurs restent dans `backend/.env`.
4. **Un conflit n'est jamais écrasé.** Il est enregistré, visible dans l'interface, et
   marqué résolu uniquement par une action humaine explicite.
5. **Le worker est inactif par défaut.** Sans fournisseur configuré, il ne fait rien.

## 4. Contrats d'API ajoutés (tous testés en HTTP réel)

| Méthode | Route | Rôle | Réponse si non configuré |
|---|---|---|---|
| GET | `/api/v1/system/connectivity` | sonde TCP mesurée vers `HORIZON_CONNECTIVITY_PROBE` | toujours 200, `online: false` + `error` |
| GET | `/api/v1/system/desktop` | informations de démarrage du lanceur (mode, base, build) | 200 |
| GET | `/api/v1/sync/status` | connectivité + fournisseur + compteurs + worker | 200, `provider.configured: false` |
| GET | `/api/v1/sync/queue?status=pending` | contenu de la file locale | 200 |
| POST | `/api/v1/sync/push` | pousse la file vers le distant | 200, `status: not_configured` |
| POST | `/api/v1/sync/pull` | récupère le distant, consigne les conflits | 200, `status: not_configured` |
| GET | `/api/v1/sync/conflicts` | conflits non résolus | 200 |
| POST | `/api/v1/sync/conflicts/{id}/resolve` | marque un conflit résolu (aucun écrasement) | 200 |

Les routes d'écriture restent protégées par `require_admin` (jeton optionnel).

## 5. Configuration (backend/.env)

```ini
# Optionnel : sans ces valeurs, HORIZON reste 100 % local.
HORIZON_SUPABASE_URL=
HORIZON_SUPABASE_KEY=

# Sonde réseau (TCP court, aucun service payant).
HORIZON_CONNECTIVITY_PROBE=1.1.1.1:443

# Synchronisation automatique au retour du réseau (inactive par défaut).
HORIZON_SYNC_AUTO=0
HORIZON_SYNC_INTERVAL_S=120
```

Tableau distant attendu côté Supabase (colonnes minimales) :
`id`, `updated_at` et les colonnes métier de chaque entité (`projects`,
`orchestrators`, `missions`, `documents`). Le push utilise
`Prefer: resolution=merge-duplicates` ; un HTTP 409 / 23505 devient un conflit.

## 6. Interface

Nouvelle page `/sync` (« Synchronisation ») dans la barre de navigation :
- état Internet mesuré, cible de la sonde et horodatage ;
- état du fournisseur distant et variables requises (noms uniquement) ;
- quatre compteurs (en attente, synchronisées, échecs, conflits) ;
- boutons « Pousser la file » / « Récupérer le distant » ;
- liste des conflits avec résolution explicite ;
- liste de la file locale en attente ;
- mention de l'état du worker automatique.

Rafraîchissement automatique toutes les 30 s. En cas d'arrêt du backend, la page
affiche l'erreur et rappelle que la base SQLite reste intacte sur le disque.

## 7. Lancement bureau

```
Double-clic sur HORIZON.bat
   └─ HORIZON.ps1 : vérifie Python + build, démarre Uvicorn si besoin,
      attend /api/v1/health, ouvre Edge/Chrome en mode application.
HORIZON-Stop.ps1 : arrêt propre du moteur (aucune donnée supprimée).
```

Le mode application utilise un profil navigateur dédié
(`%LOCALAPPDATA%\HORIZON\browser-profile`) : fenêtre sans barre d'adresse, comme
une application de bureau. Aucun paquet supplémentaire n'a été installé.

## 8. Tests réellement exécutés (2026-11-09)

| Test | Résultat mesuré |
|---|---|
| `npm run build` (tsc + vite) | succès, 2105 modules, `dist/index.html` 0.55 kB |
| `GET /api/v1/health` | 200, `version: 0.3.0` |
| `GET /api/v1/sync/status` | 200, `online: true`, `provider: none`, `pending: 1`, `worker.auto_enabled: false` |
| `POST /api/v1/projects` | 201, écriture ajoutée à `sync_outbox` (vérifié : `pending: 1`) |
| `POST /api/v1/sync/push` | 200, `status: not_configured`, file conservée |
| `POST /api/v1/sync/pull` | 200, `status: not_configured`, aucune donnée modifiée |
| `GET /api/v1/sync/conflicts` | 200, `count: 0` |
| Détection hors ligne (module `connectivity`, sonde `127.0.0.1:1`) | `online: false`, `ConnectionRefusedError` capturée |
| 11 routes API existantes | 200 |
| 10 routes SPA servies par le backend | 200 |
| Lanceur `HORIZON.ps1` | fenêtre application ouverte, titre « HORIZON CENTRAL AI » (anciennement « HORIZON LOCAL AI », renommé le 2026-11-09) |
| Migration 4 `offline_first_sync` | appliquée ; tables `sync_outbox`, `sync_conflicts`, `sync_state` présentes |
| Données existantes | conservées (3 projets, 1 orchestrateur, 1 mission, 1 document) |

**Non testé** : navigateur automatisé (aucun outil disponible) — le rendu de la
page `/sync` n'est pas vérifié visuellement ; push/pull réels vers Supabase
( aucun fournisseur configuré ) ; mode hors ligne complet de bout en bout avec
coupure réseau physique.

## 9. Limites et suites

- La synchronisation est **mono-fournisseur** (Supabase REST). D'autres
  adaptateurs peuvent être ajoutés sans toucher au moteur (`SyncProvider`).
- Pas de résolution automatique de conflit (choix assumé : jamais d'écrasement).
- Le `pull` consigne les divergences mais n'écrit pas les données distantes en
  local : une stratégie de fusion explicite reste à définir.
- Le lanceur dépend d'Edge ou Chrome installés ; sinon il retombe sur le
  navigateur par défaut (fenêtre avec barre d'adresse).
- Tests d'interface manuels page par page toujours à réaliser.

