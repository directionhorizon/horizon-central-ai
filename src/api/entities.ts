/**
 * Types des entités métier réellement exposées par le backend v0.2.
 * Aucun de ces objets ne contient de secret : `api_key_env` est un NOM de
 * variable d'environnement, jamais une valeur de clé.
 */

export type ProjectStatus = 'active' | 'paused' | 'archived';
export type OrchestratorStatus = 'active' | 'inactive' | 'disabled';
export type HealthStatus = 'unverified' | 'available' | 'unavailable' | 'degraded';
export type MissionStatus = 'draft' | 'planned' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type Priority = 'low' | 'normal' | 'high' | 'critical';
export type ProviderStatus = 'unconfigured' | 'unverified' | 'available' | 'unavailable';

export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  mission_count: number;
  orchestrator_count: number;
}

export interface ProjectDetail extends ProjectSummary {
  orchestrators: Array<{
    id: string;
    name: string;
    status: OrchestratorStatus;
    health_status: HealthStatus;
    role: string;
  }>;
  missions: Array<{
    id: string;
    title: string;
    status: MissionStatus;
    priority: Priority;
    orchestrator_id: string | null;
    created_at: string;
    updated_at: string;
  }>;
}

export interface Capability {
  id: string;
  orchestrator_id: string;
  capability_id: string;
  level: string;
  detail: string;
  created_at: string;
}

export interface Orchestrator {
  id: string;
  name: string;
  kind: string;
  description: string;
  endpoint: string;
  version: string;
  status: OrchestratorStatus;
  health_status: HealthStatus;
  last_checked_at: string | null;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  capabilities: Capability[];
  projects: Array<{
    project_id: string;
    project_name: string;
    project_status: ProjectStatus;
    role: string;
    created_at: string;
  }>;
  model_selection: Array<{
    provider_id: string;
    model: string;
    provider_name: string;
    provider_status: ProviderStatus;
  }>;
  skills: SkillSummary[];
}

/* --- Bibliothèque de skills (compétences) -------------------------------- */

export type SkillStatus = 'active' | 'disabled';

export interface SkillSummary {
  id: string;
  name: string;
  /** Grand domaine d'application (ex. « Analyse de données et recherche »). */
  category: string;
  /** Sous-domaine précis (ex. « Veille et synthèse »). */
  subcategory: string;
  description: string;
  level: string;
  tags: string;
  status: SkillStatus;
  /** Provenance : 'github', 'integrated' (catalogue du dépôt) ou 'manual'. */
  origin: string;
  source_url: string;
  author: string;
}

export interface Skill extends SkillSummary {
  license: string;
  created_at: string;
  updated_at: string;
}

export interface MissionStep {
  id: string;
  mission_id: string;
  position: number;
  title: string;
  status: StepStatus;
  assigned_orchestrator_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  error: string;
}

export interface MissionCheckpoint {
  id: string;
  mission_id: string;
  step_id: string | null;
  label: string;
  state: Record<string, unknown>;
  created_at: string;
}

export interface Mission {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: MissionStatus;
  priority: Priority;
  orchestrator_id: string | null;
  created_at: string;
  updated_at: string;
  steps?: MissionStep[];
  checkpoints?: MissionCheckpoint[];
  checkpoint_count?: number;
}

/* --- Exécution CORE ↔ Hermes --------------------------------------------- */

export type RunPhase =
  | 'dispatching' | 'running' | 'completed' | 'failed' | 'cancelled'
  | 'paused' | 'error' | 'stopping';

export interface OrchestratorRun {
  id: string;
  mission_id: string;
  step_id: string | null;
  orchestrator_id: string | null;
  run_id: string;
  session_id: string;
  idempotency_key: string;
  status: string;
  phase: RunPhase;
  replayed_count: number;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  output: string;
  error: string;
  usage: Record<string, unknown>;
  runtime: Record<string, unknown>;
  raw_status: {
    status?: string;
    model?: string;
    turn_exit_reason?: string;
    pending_controls?: Array<{
      request_id?: string;
      prompt_id?: string;
      execution_generation?: number;
      kind?: string;
      type?: string;
    }>;
    runtime?: Record<string, unknown>;
  };
}

export interface DispatchResult {
  run: OrchestratorRun;
  replayed: boolean;
  detail: string;
}

export interface PendingControl {
  request_id: string;
  execution_generation: number;
  kind?: string;
}

export interface LlmProvider {
  id: string;
  name: string;
  kind: string;
  base_url: string;
  api_key_env: string;
  default_model: string;
  status: ProviderStatus;
  last_checked_at: string | null;
  last_error: string;
  created_at: string;
  updated_at: string;
  api_key_configured: boolean;
}

export interface ModelSelection {
  mode: 'auto' | 'manual';
  provider_id: string | null;
  model: string | null;
}

export interface OperationEntry {
  id: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: string | null;
  result: string;
  detail: string;
  created_at: string;
}

export interface SystemMetrics {
  measured_at: string;
  source: string;
  cpu_percent: number | null;
  memory: { supported: boolean; total_mb?: number; available_mb?: number; used_percent?: number; reason?: string };
  disk: { supported: boolean; path?: string; total_gb?: number; free_gb?: number; used_percent?: number; reason?: string };
}

export interface SystemStatus {
  generated_at: string;
  auth: { auth_enabled: boolean; token_env: string; mode: string };
  counts: { projects: number; orchestrators: number; missions: number; sessions: number; operations: number };
  llm: { providers: number; available_providers: number; selection: ModelSelection; status: string };
}

export type DocumentStatus = 'active' | 'archived';

export interface KnowledgeDocument {
  id: string;
  project_id: string | null;
  title: string;
  content: string;
  tags: string;
  source: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
}

export interface PlanResponse {
  status: 'planned' | 'no_model';
  detail?: string;
  mission?: Mission;
  plan?: { title: string; summary: string; steps: Array<{ title: string; capability: string }> };
  execution?: { status: string; provider_id: string | null; model_id: string | null; fallback_used: boolean };
}

/* --- Synchronisation Offline-First ---------------------------------------- */

export interface ConnectivityStatus {
  online: boolean;
  target: string;
  checked_at: string;
  error: string;
}

export interface SyncQueueItem {
  id: string;
  entity: string;
  entity_id: string;
  operation: 'create' | 'update' | 'delete';
  payload_json: string;
  status: 'pending' | 'synced' | 'failed' | 'conflict';
  attempts: number;
  last_error: string;
  created_at: string;
  updated_at: string;
}

export interface SyncConflict {
  id: string;
  entity: string;
  entity_id: string;
  local_updated_at: string | null;
  remote_updated_at: string | null;
  reason: string;
  resolved: number;
  created_at: string;
}

export interface SyncStatus {
  /** Vrai uniquement si un fournisseur distant est réellement configuré. */
  provider_configured: boolean;
  online: boolean;
  queue: { pending: number; synced: number; failed: number; conflicts: number };
  worker_active: boolean;
  last_sync_at: string | null;
  mode: string;
  /** Stockage de référence (supabase quand configuré, sinon sqlite). */
  primary_store?: string;
  /** Copie locale de secours (sqlite quand un stockage distant est actif). */
  secondary_store?: string | null;
  note: string;
}

/* --- Connexions et intégrations ------------------------------------------ */

export type IntegrationCategory =
  | 'orchestrator'
  | 'app'
  | 'llm_provider'
  | 'model'
  | 'mcp'
  | 'api'
  | 'machine'
  | 'storage'
  | 'communication';

export type IntegrationMethod =
  | 'oauth2'
  | 'api_key'
  | 'bearer'
  | 'endpoint'
  | 'mcp'
  | 'rest'
  | 'cli'
  | 'webhook';

export type IntegrationStatus =
  | 'connected'
  | 'not_configured'
  | 'pending'
  | 'expired'
  | 'unavailable'
  | 'error'
  | 'partial';

export interface Integration {
  id: string;
  name: string;
  category: IntegrationCategory;
  method: IntegrationMethod;
  status: IntegrationStatus;
  permissions: string;
  capabilities: string;
  /** Nom de variable uniquement : aucune valeur de clé n'est exposée. */
  api_key_env: string;
  last_checked_at: string | null;
  last_error: string;
  config: Record<string, unknown>;
  archived: boolean;
  endpoint_host: string;
  secret_present: boolean;
  created_at: string;
  updated_at: string;
}

export interface IntegrationTestResult {
  id: string;
  status: IntegrationStatus;
  detail: string;
  secret_present: boolean;
  endpoint_host: string;
  last_checked_at: string | null;
  verified: boolean;
}

export interface IntegrationStats {
  total: number;
  by_status: Record<string, number>;
  connected: number;
  needs_action: number;
}

export interface IntegrationListResponse {
  items: Integration[];
  count: number;
  stats: IntegrationStats;
}

export interface IntegrationCatalogResponse {
  categories: Array<{ id: IntegrationCategory; label: string }>;
  methods: Array<{ id: IntegrationMethod; label: string }>;
  statuses: Array<{ id: IntegrationStatus; label: string }>;
}

export interface SyncPushResult {
  status: 'completed' | 'not_configured';
  detail?: string;
  pushed: number;
  failed: number;
  conflicts: number;
  pending?: number;
}

export interface SyncPullResult {
  status: 'completed' | 'not_configured';
  detail?: string;
  pulled: number;
  conflicts: number;
}

export interface SyncQueueResponse {
  items: SyncQueueItem[];
  count: number;
}

export interface SyncConflictsResponse {
  items: SyncConflict[];
  count: number;
}

export interface PlanResponse {
  status: 'planned' | 'no_model';
  detail?: string;
  mission?: Mission;
  plan?: { title: string; summary: string; steps: Array<{ title: string; capability: string }> };
  execution?: { status: string; provider_id: string | null; model_id: string | null; fallback_used: boolean };
}
