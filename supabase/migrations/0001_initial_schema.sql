-- =============================================================================
-- HORIZON CENTRAL AI — Schéma Supabase (PostgreSQL) — BROUILLON À VALIDER
-- =============================================================================
-- But : héberger les données de HORIZON (architecture online-first).
-- Référence : Politique de gouvernance des données (validée) + modèle
--             conceptuel HORIZON CORE. Ce fichier est une PROPOSITION : il doit
--             être validé avant exécution (la politique l'exige).
--
-- Principes appliqués :
--  - Séparation « registre administratif » (systèmes, agents, projets,
--    relations) et « données d'exécution / métier ».
--  - Aucun secret : seuls des NOMS de variables (api_key_env) sont stockés.
--  - Row Level Security (RLS) activée : aucune donnée exposée sans droit.
--  - Historique conservé (authorship, operation_log) — jamais d'écrasement.
-- =============================================================================

create extension if not exists pgcrypto;

-- -----------------------------------------------------------------------------
-- 1. REGISTRE ADMINISTRATIF
-- -----------------------------------------------------------------------------

create table if not exists projects (
  id text primary key,
  name text not null,
  description text not null default '',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrators (
  id text primary key,
  name text not null,
  kind text not null default 'local',
  description text not null default '',
  endpoint text not null default '',
  version text not null default '',
  status text not null default 'active',
  health_status text not null default 'unverified',
  last_checked_at timestamptz,
  config_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_capabilities (
  id text primary key,
  orchestrator_id text not null references orchestrators(id) on delete cascade,
  capability_id text not null,
  level text not null default 'standard',
  detail text not null default '',
  created_at timestamptz not null default now(),
  unique (orchestrator_id, capability_id)
);

create table if not exists orchestrator_projects (
  orchestrator_id text not null references orchestrators(id) on delete cascade,
  project_id text not null references projects(id) on delete cascade,
  role text not null default 'member',
  created_at timestamptz not null default now(),
  primary key (orchestrator_id, project_id)
);

-- -----------------------------------------------------------------------------
-- 2. EXÉCUTION (missions, étapes, exécutions)
-- -----------------------------------------------------------------------------

create table if not exists missions (
  id text primary key,
  project_id text not null references projects(id) on delete cascade,
  title text not null,
  description text not null default '',
  status text not null default 'draft',
  priority text not null default 'normal',
  orchestrator_id text references orchestrators(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists mission_steps (
  id text primary key,
  mission_id text not null references missions(id) on delete cascade,
  position integer not null,
  title text not null,
  status text not null default 'pending',
  assigned_orchestrator_id text references orchestrators(id) on delete set null,
  started_at timestamptz,
  completed_at timestamptz,
  error text not null default '',
  unique (mission_id, position)
);

create table if not exists mission_checkpoints (
  id text primary key,
  mission_id text not null references missions(id) on delete cascade,
  step_id text references mission_steps(id) on delete set null,
  label text not null,
  state_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists orchestrator_runs (
  id text primary key,
  mission_id text not null references missions(id) on delete cascade,
  step_id text references mission_steps(id) on delete set null,
  orchestrator_id text references orchestrators(id) on delete set null,
  run_id text not null default '',
  session_id text not null default '',
  idempotency_key text not null unique,
  status text not null default 'started',
  phase text not null default 'dispatching',
  replayed_count integer not null default 0,
  requested_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  output text not null default '',
  error text not null default '',
  usage_json jsonb not null default '{}'::jsonb,
  runtime_json jsonb not null default '{}'::jsonb,
  raw_status_json jsonb not null default '{}'::jsonb
);

-- -----------------------------------------------------------------------------
-- 3. CONNAISSANCES & DOCUMENTS
-- -----------------------------------------------------------------------------

create table if not exists documents (
  id text primary key,
  project_id text references projects(id) on delete set null,
  title text not null,
  content text not null default '',
  tags text not null default '',
  source text not null default '',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 4. MODÈLES, INTÉGRATIONS, PARAMÈTRES
-- -----------------------------------------------------------------------------

create table if not exists llm_providers (
  id text primary key,
  name text not null,
  kind text not null default 'openai_compatible',
  base_url text not null,
  api_key_env text not null default '',   -- NOM de variable uniquement
  default_model text not null default '',
  status text not null default 'unconfigured',
  last_checked_at timestamptz,
  last_error text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_model_selection (
  orchestrator_id text not null references orchestrators(id) on delete cascade,
  provider_id text not null references llm_providers(id) on delete cascade,
  model text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (orchestrator_id, provider_id)
);

create table if not exists integrations (
  id text primary key,
  name text not null,
  category text not null,
  method text not null,
  endpoint text not null default '',
  status text not null default 'not_configured',
  permissions text not null default '',
  capabilities text not null default '',
  api_key_env text not null default '',   -- NOM de variable uniquement
  last_checked_at timestamptz,
  last_error text not null default '',
  config_json jsonb not null default '{}'::jsonb,
  archived integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists settings (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 5. SESSIONS CONVERSATIONNELLES
-- -----------------------------------------------------------------------------

create table if not exists sessions (
  id text primary key,
  title text not null,
  project_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists messages (
  id text primary key,
  session_id text not null references sessions(id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 6. GOUVERNANCE (traçabilité — jamais exposée dans l'interface)
-- -----------------------------------------------------------------------------

create table if not exists authorship (
  id text primary key,
  entity_type text not null,
  entity_id text not null default '',
  agent_auteur text not null default '',
  systeme text not null default '',
  projet text not null default '',
  provenance text not null default '',
  version text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists operation_log (
  id text primary key,
  actor text not null,
  action text not null,
  target_type text not null,
  target_id text,
  result text not null default 'success',
  detail text not null default '',
  created_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 7. BIBLIOTHÈQUE DE SKILLS
-- -----------------------------------------------------------------------------

create table if not exists skills (
  id text primary key,
  name text not null,
  category text not null default 'general',
  subcategory text not null default '',
  description text not null default '',
  level text not null default 'standard',
  tags text not null default '',
  status text not null default 'active',
  origin text not null default 'integrated',
  source_url text not null default '',
  author text not null default '',
  license text not null default '',
  usage text not null default '',
  outputs text not null default '',
  example text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_skills (
  orchestrator_id text not null references orchestrators(id) on delete cascade,
  skill_id text not null references skills(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (orchestrator_id, skill_id)
);

-- -----------------------------------------------------------------------------
-- 8. SYNCHRONISATION (transitionnel — tant que le local coexiste)
-- -----------------------------------------------------------------------------

create table if not exists sync_outbox (
  id text primary key,
  entity text not null,
  entity_id text not null,
  operation text not null,
  payload_json jsonb not null default '{}'::jsonb,
  status text not null default 'pending',
  attempts integer not null default 0,
  last_error text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists sync_state (
  entity text not null,
  entity_id text not null,
  last_synced_at timestamptz,
  remote_updated_at timestamptz,
  local_updated_at timestamptz,
  primary key (entity, entity_id)
);

create table if not exists sync_conflicts (
  id text primary key,
  entity text not null,
  entity_id text not null,
  local_updated_at timestamptz,
  remote_updated_at timestamptz,
  reason text not null,
  resolved integer not null default 0,
  created_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 9. SÉCURITÉ — Row Level Security
-- -----------------------------------------------------------------------------
-- Le backend (sur LWS) accède avec la clé de service ; aucune donnée n'est
-- exposée publiquement. La clé de service n'est JAMAIS dans le frontend.
-- RLS activée partout : sans politique pour le rôle `anon`, aucun accès public.

do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'public'
  loop
    execute format('alter table public.%I enable row level security;', t);
  end loop;
end $$;

-- Index utiles
create index if not exists idx_missions_project on missions(project_id);
create index if not exists idx_documents_project on documents(project_id);
create index if not exists idx_authorship_entity on authorship(entity_type, entity_id);
create index if not exists idx_skills_category on skills(category);
create index if not exists idx_runs_mission on orchestrator_runs(mission_id);
