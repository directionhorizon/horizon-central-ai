/**
 * Configuration runtime du frontend.
 *
 * Une seule source de vérité pour l'URL du backend et les chemins d'API.
 * Aucune clé, aucun secret, aucun token n'est lu ici : uniquement des URL publiques.
 */

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

const trimTrailingSlashes = (value: string): string => value.replace(/\/+$/, '');

const readBaseUrl = (): string => {
  const raw = import.meta.env.VITE_HORIZON_API_URL as string | undefined;
  if (typeof raw === 'string' && raw.trim().length > 0) {
    return trimTrailingSlashes(raw.trim());
  }
  return DEFAULT_API_BASE_URL;
};

const readTimeout = (): number => {
  const raw = Number(import.meta.env.VITE_HORIZON_API_TIMEOUT_MS);
  if (Number.isFinite(raw) && raw > 0) return raw;
  return 8000;
};

export const API_ROUTES = {
  health: '/api/v1/health',
  capabilities: '/api/v1/capabilities',
  sessions: '/api/v1/sessions',
  session: (id: string) => `/api/v1/sessions/${encodeURIComponent(id)}`,
  messages: (id: string) => `/api/v1/sessions/${encodeURIComponent(id)}/messages`,
  reset: (id: string) => `/api/v1/sessions/${encodeURIComponent(id)}/reset`,

  projects: '/api/v1/projects',
  project: (id: string) => `/api/v1/projects/${encodeURIComponent(id)}`,

  orchestrators: '/api/v1/orchestrators',
  orchestrator: (id: string) => `/api/v1/orchestrators/${encodeURIComponent(id)}`,
  orchestratorCheck: (id: string) => `/api/v1/orchestrators/${encodeURIComponent(id)}/check`,
  orchestratorCapabilities: (id: string) => `/api/v1/orchestrators/${encodeURIComponent(id)}/capabilities`,
  orchestratorCapability: (id: string, capabilityId: string) =>
    `/api/v1/orchestrators/${encodeURIComponent(id)}/capabilities/${encodeURIComponent(capabilityId)}`,
  orchestratorProjects: (id: string) => `/api/v1/orchestrators/${encodeURIComponent(id)}/projects`,
  orchestratorProject: (id: string, projectId: string) =>
    `/api/v1/orchestrators/${encodeURIComponent(id)}/projects/${encodeURIComponent(projectId)}`,
  orchestratorModel: (id: string) => `/api/v1/orchestrators/${encodeURIComponent(id)}/model`,

  missions: '/api/v1/missions',
  mission: (id: string) => `/api/v1/missions/${encodeURIComponent(id)}`,
  missionSteps: (id: string) => `/api/v1/missions/${encodeURIComponent(id)}/steps`,
  missionStep: (id: string, stepId: string) =>
    `/api/v1/missions/${encodeURIComponent(id)}/steps/${encodeURIComponent(stepId)}`,
  missionCheckpoints: (id: string) => `/api/v1/missions/${encodeURIComponent(id)}/checkpoints`,

  models: '/api/v1/models',
  model: (id: string) => `/api/v1/models/${encodeURIComponent(id)}`,
  modelTest: (id: string) => `/api/v1/models/${encodeURIComponent(id)}/test`,
  modelSelection: '/api/v1/settings/model-selection',

  documents: '/api/v1/documents',
  document: (id: string) => `/api/v1/documents/${encodeURIComponent(id)}`,

  coreRoute: '/api/v1/core/route',
  corePlan: '/api/v1/core/plan',

  operations: '/api/v1/operations',
  systemMetrics: '/api/v1/system/metrics',
  systemStatus: '/api/v1/system/status',
  systemConnectivity: '/api/v1/system/connectivity',

  syncStatus: '/api/v1/sync/status',
  syncQueue: '/api/v1/sync/queue',
  syncPush: '/api/v1/sync/push',
  syncPull: '/api/v1/sync/pull',
  syncConflicts: '/api/v1/sync/conflicts',
  syncConflictResolve: (id: string) => `/api/v1/sync/conflicts/${encodeURIComponent(id)}/resolve`,

  integrations: '/api/v1/integrations',
  integrationsCatalog: '/api/v1/integrations/catalog',
  integration: (id: string) => `/api/v1/integrations/${encodeURIComponent(id)}`,
  integrationTest: (id: string) => `/api/v1/integrations/${encodeURIComponent(id)}/test`,

  adminDiagnostics: '/api/v1/admin/diagnostics',
} as const;

export const apiConfig = {
  baseUrl: readBaseUrl(),
  timeoutMs: readTimeout(),
  routes: API_ROUTES,
} as const;

export type ApiConfig = typeof apiConfig;
