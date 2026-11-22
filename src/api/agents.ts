/** API du registre des agents — routes réelles /api/v1/agents. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { Agent, Skill } from './entities';

export const agentsApi = {
  list: (params: { orchestrator_id?: string; role?: string; status?: string } = {}): Promise<{ items: Agent[] }> => {
    const search = new URLSearchParams();
    if (params.orchestrator_id) search.set('orchestrator_id', params.orchestrator_id);
    if (params.role) search.set('role', params.role);
    if (params.status) search.set('status', params.status);
    const suffix = search.toString() ? `?${search.toString()}` : '';
    return http.requestWithRetry<{ items: Agent[] }>(`${API_ROUTES.agents}${suffix}`);
  },
  listSkills: (agentId: string): Promise<{ items: Skill[] }> =>
    http.requestWithRetry<{ items: Skill[] }>(API_ROUTES.agentSkills(agentId)),
  attachSkill: (agentId: string, skillId: string): Promise<unknown> =>
    http.request<unknown>(API_ROUTES.agentSkills(agentId), {
      method: 'POST',
      body: { skill_id: skillId },
    }),
  detachSkill: (agentId: string, skillId: string): Promise<unknown> =>
    http.request<unknown>(API_ROUTES.agentSkill(agentId, skillId), { method: 'DELETE' }),
} as const;
