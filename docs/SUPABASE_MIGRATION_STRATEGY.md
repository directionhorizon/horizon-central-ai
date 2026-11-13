# HORIZON CENTRAL AI — Stratégie de migration contrôlée vers Supabase

État : **plan validé, aucune étape destructive exécutée**. La base locale SQLite
reste la source de vérité tant que la migration n'est pas explicitement
autorisée. Rien dans ce document n'a été appliqué à distance.

## 1. Principes

1. **Local-first d'abord.** SQLite reste la source de vérité locale ; Supabase
   devient un miroir distant interrogeable depuis plusieurs machines.
2. **Aucune suppression.** La migration ajoute et copie ; elle ne purge rien.
3. **Aucun secret dans le frontend.** Les valeurs restent dans `backend/.env` ;
   le code ne manipule que des *noms* de variables (`api_key_env`).
4. **Aucune écriture automatique non réversible.** Résolution de conflit
   toujours humaine ; le moteur ne pousse que la file locale `sync_outbox`.
5. **Réversibilité totale.** Retirer les deux variables d'environnement remet
   l'application en mode 100 % local, sans perte de données.

## 2. État actuel (mesuré)

| Élément | Valeur constatée |
|---|---|
| Base locale | `backend/data/horizon.db` (SQLite) |
| Migrations appliquées | 4 (`projects_orchestrators_missions`, `sessions_project_link`, `documents_memory`, `offline_first_sync`) |
| Tables | 18 (dont `sync_outbox`, `sync_state`, `sync_conflicts`) |
| Instantané exportable | 41 lignes (3 projets, 1 orchestrateur, 1 mission, 1 document, 6 sessions, 19 opérations, 1 écriture en file, 1 conflit technique, 4 migrations) |
| Fournisseur distant | **non configuré** (`provider: none`) |
| Synchronisation automatique | disponible et **inactive** (`HORIZON_SYNC_AUTO` non défini) |

## 3. Colonnes réellement présentes (vérifiées en base)

- `projects` : `id, name, description, status, created_at, updated_at`
- `orchestrators` : `id, name, kind, description, endpoint, version, status, health_status, last_checked_at, config_json, created_at, updated_at`
- `missions` : `id, project_id, title, description, status, priority, orchestrator_id, created_at, updated_at`
- `documents` : `id, project_id, title, content, tags, source, status, created_at, updated_at`

## 4. Schéma distant proposé (à exécuter par l'utilisateur, non appliqué ici)

```sql
-- Tables miroir des entités synchronisées (postgresql / Supabase).
create table if not exists projects (
  id text primary key,
  name text not null,
  description text default '',
  status text default 'active',
  created_at timestamptz,
  updated_at timestamptz
);

create table if not exists orchestrators (
  id text primary key,
  name text not null,
  kind text default '',
  description text default '',
  endpoint text default '',
  version text default '',
  status text default 'inactive',
  health_status text default 'unverified',
  last_checked_at timestamptz,
  config_json jsonb default '{}'::jsonb,
  created_at timestamptz,
  updated_at timestamptz
);

create table if not exists missions (
  id text primary key,
  project_id text references projects(id),
  title text not null,
  description text default '',
  status text default 'draft',
  priority text default 'normal',
  orchestrator_id text,
  created_at timestamptz,
  updated_at timestamptz
);

create table if not exists documents (
  id text primary key,
  project_id text,
  title text not null,
  content text default '',
  tags text default '',
  source text default '',
  status text default 'active',
  created_at timestamptz,
  updated_at timestamptz
);

-- Sécurité : activer RLS et n'autoriser que la clé de service locale.
alter table projects enable row level security;
alter table orchestrators enable row level security;
alter table missions enable row level security;
alter table documents enable row level security;
```

`updated_at` est indispensable : c'est la base de la détection de conflit
(comparaison `remote.updated_at` / `sync_state.local_updated_at`).

## 5. Étapes de migration (ordre imposé, aucune exécutée à ce jour)

| # | Étape | Qui | Réversible ? | Statut |
|---|---|---|---|---|
| 1 | Créer le projet Supabase et noter l'URL + la clé de service | utilisateur | oui | **à faire (autorisation requise)** |
| 2 | Exécuter le DDL du §4 dans l'éditeur SQL Supabase | utilisateur | oui (drop des tables miroir) | à faire |
| 3 | Renseigner `HORIZON_SUPABASE_URL` et `HORIZON_SUPABASE_KEY` dans `backend/.env` | utilisateur (fichier local, jamais versionné) | oui (vider les valeurs) | à faire |
| 4 | Vérifier la détection : `GET /api/v1/sync/status` doit passer à `provider.configured: true` | HORIZON | oui | prêt (mécanisme testé) |
| 5 | Produire un instantané local : `python tools/export_snapshot.py` | HORIZON | oui (fichier en lecture seule) | **exécuté** (41 lignes) |
| 6 | Pousser la file locale : `POST /api/v1/sync/push` | utilisateur | oui (les données locales restent) | prêt |
| 7 | Vérifier côté Supabase que les lignes correspondent à l'instantané | utilisateur | oui | à faire |
| 8 | Première récupération : `POST /api/v1/sync/pull` (500 lignes max par appel) | utilisateur | oui | prêt |
| 9 | Activer la synchronisation automatique : `HORIZON_SYNC_AUTO=1` | utilisateur | oui | prêt |
| 10 | Vérifier `sync_conflicts` après chaque cycle | utilisateur | oui | prêt |

Aucune étape ne supprime ni ne remplace les données SQLite existantes.

## 6. Règles de conflit (déjà implémentées et testées)

- La comparaison se fait sur `updated_at` **et** sur la présence d'une écriture
  en attente dans `sync_outbox` pour la même entité.
- Un désaccord est inscrit dans `sync_conflicts` avec les deux horodatages et un
  motif ; **rien n'est écrasé**, ni localement ni à distance.
- La résolution est explicite (`POST /api/v1/sync/conflicts/{id}/resolve`) et
  journalisée dans `operation_log`.
- Un HTTP 409 / `23505` renvoyé par le distant devient également un conflit.
- Test réel effectué : conflit créé → visible (`count 1`) → résolu (`resolved 1`)
  → `count 0`, données locales intactes.

## 7. Sécurité

- La clé de service Supabase reste **sur la machine locale**, dans `backend/.env`
  (jamais dans le dépôt, jamais dans le frontend, jamais dans les journaux).
- Le frontend n'appelle jamais Supabase directement : tout passe par le backend
  local (une seule surface d'accès, un seul point d'audit).
- RLS activée sur les tables miroir ; la clé de service n'est utilisée que par le
  processus local, sur `127.0.0.1`.
- `HORIZON_*` : seuls des *noms* de variables apparaissent en base
  (`api_key_env`) ; aucune valeur n'est stockée.

## 8. Retour arrière (rollback)

1. Vider `HORIZON_SUPABASE_URL` et `HORIZON_SUPABASE_KEY` dans `backend/.env`.
2. Redémarrer le moteur local (`HORIZON-Stop.ps1` puis `HORIZON.bat`).
3. L'application repasse en mode 100 % local : `provider: none`, file locale
   conservée, aucune donnée perdue.
4. Les instantanés JSON produits à l'étape 5 restent disponibles comme sauvegarde.

## 9. Prérequis humains restants

- Un projet Supabase (gratuit) et sa clé de service.
- L'autorisation explicite d'exécuter les étapes 4 à 9.
- Pour la partie IA : une clé de fournisseur LLM, afin que `/api/v1/core/plan`
  cesse de répondre `no_model`.

Tant que ces prérequis ne sont pas fournis, HORIZON CENTRAL AI fonctionne
intégralement en local — ce qui est l'état actuel vérifié.

