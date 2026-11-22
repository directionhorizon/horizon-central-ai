/** API orchestrateurs — routes réelles /api/v1/orchestrators. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { HealthStatus, Orchestrator, SkillSummary } from './entities';

export interface OrchestratorListResponse {
  items: Orchestrator[];
}

export interface CreateOrchestratorInput {
  name: string;
  kind?: string;
  description?: string;
  endpoint?: string;
  version?: string;
  status?: 'active' | 'inactive' | 'disabled';
  config?: Record<string, unknown>;
  capabilities?: Array<{ capability_id: string; level?: string; detail?: string }>;
}

export interface CheckResponse {
  id: string;
  health_status: HealthStatus;
  detail: string;
  target?: string;
}

export const orchestratorsApi = {
  list: (params: { status?: string; projectId?: string } = {}): Promise<OrchestratorListResponse> => {
    const search = new URLSearchParams();
    if (params.status) search.set('status', params.status);
    if (params.projectId) search.set('project_id', params.projectId);
    const suffix = search.toString() ? `?${search.toString()}` : '';
    return http.requestWithRetry<OrchestratorListResponse>(`${API_ROUTES.orchestrators}${suffix}`);
  },
  get: (id: string): Promise<Orchestrator> => http.request<Orchestrator>(API_ROUTES.orchestrator(id)),
  create: (input: CreateOrchestratorInput): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestrators, { method: 'POST', body: input }),
  update: (id: string, input: Partial<CreateOrchestratorInput>): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestrator(id), { method: 'PATCH', body: input }),
  disable: (id: string): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestrator(id), { method: 'DELETE' }),
  check: (id: string): Promise<CheckResponse> =>
    http.request<CheckResponse>(API_ROUTES.orchestratorCheck(id), { method: 'POST' }),
  addCapability: (id: string, capability: { capability_id: string; level?: string; detail?: string }): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorCapabilities(id), { method: 'POST', body: capability }),
  removeCapability: (id: string, capabilityId: string): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorCapability(id, capabilityId), { method: 'DELETE' }),
  linkProject: (id: string, projectId: string, role = 'member'): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorProjects(id), {
      method: 'POST',
      body: { project_id: projectId, role },
    }),
  unlinkProject: (id: string, projectId: string): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorProject(id, projectId), { method: 'DELETE' }),
  setModel: (id: string, providerId: string, model: string): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorModel(id), {
      method: 'PUT',
      body: { provider_id: providerId, model },
    }),
  listSkills: (id: string): Promise<{ items: SkillSummary[] }> =>
    http.requestWithRetry<{ items: SkillSummary[] }>(API_ROUTES.orchestratorSkills(id)),
  attachSkill: (id: string, skillId: string): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorSkills(id), {
      method: 'POST',
      body: { skill_id: skillId },
    }),
  detachSkill: (id: string, skillId: string): Promise<Orchestrator> =>
    http.request<Orchestrator>(API_ROUTES.orchestratorSkill(id, skillId), { method: 'DELETE' }),
} as const;
