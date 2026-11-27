/** API supervision et moteur HORIZON CORE. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { OperationEntry, PlanResponse, SystemMetrics, SystemStatus } from './entities';

export interface OperationsResponse {
  items: OperationEntry[];
}

export interface CoreRouteResponse {
  status: 'selected' | 'no_orchestrator';
  capability: string | null;
  detail?: string;
  orchestrator?: { id: string; name: string; health_status: string; capabilities: string[] };
}

export interface UpdateStatus {
  state: 'idle' | 'running' | 'done' | 'error';
  mode: 'local' | 'server' | 'off' | null;
  available: boolean;
  detail: string;
  log: string[];
  started_at: string | null;
  finished_at: string | null;
}

export const systemApi = {
  metrics: (): Promise<SystemMetrics> => http.requestWithRetry<SystemMetrics>(API_ROUTES.systemMetrics),
  status: (): Promise<SystemStatus> => http.requestWithRetry<SystemStatus>(API_ROUTES.systemStatus),
  operations: (limit = 100): Promise<OperationsResponse> =>
    http.requestWithRetry<OperationsResponse>(`${API_ROUTES.operations}?limit=${limit}`),
  updateStatus: (): Promise<UpdateStatus> => http.requestWithRetry<UpdateStatus>(API_ROUTES.systemUpdate),
  startUpdate: (): Promise<UpdateStatus> =>
    http.request<UpdateStatus>(API_ROUTES.systemUpdate, { method: 'POST', timeoutMs: 60000 }),
} as const;

export const coreApi = {
  route: (capability?: string): Promise<CoreRouteResponse> =>
    http.requestWithRetry<CoreRouteResponse>(
      capability ? `${API_ROUTES.coreRoute}?capability=${encodeURIComponent(capability)}` : API_ROUTES.coreRoute,
    ),
  plan: (projectId: string, request: string, orchestratorId?: string): Promise<PlanResponse> =>
    http.request<PlanResponse>(API_ROUTES.corePlan, {
      method: 'POST',
      body: { project_id: projectId, request, orchestrator_id: orchestratorId ?? null },
      timeoutMs: 120000,
    }),
} as const;
