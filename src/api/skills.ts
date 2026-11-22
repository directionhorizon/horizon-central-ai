/** API bibliothèque de skills (compétences) — routes réelles /api/v1/skills. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { Skill } from './entities';

export interface SkillListResponse {
  items: Skill[];
  count: number;
}

export interface CreateSkillInput {
  name: string;
  category?: string;
  description?: string;
  level?: string;
  tags?: string;
  status?: 'active' | 'disabled';
}

export const skillsApi = {
  list: (params: { q?: string; category?: string; status?: string } = {}): Promise<SkillListResponse> => {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.category) search.set('category', params.category);
    if (params.status) search.set('status', params.status);
    const suffix = search.toString() ? `?${search.toString()}` : '';
    return http.requestWithRetry<SkillListResponse>(`${API_ROUTES.skills}${suffix}`);
  },
  categories: (): Promise<{ items: string[] }> =>
    http.requestWithRetry<{ items: string[] }>(API_ROUTES.skillsCategories),
  create: (input: CreateSkillInput): Promise<Skill> =>
    http.request<Skill>(API_ROUTES.skills, { method: 'POST', body: input }),
  update: (id: string, input: Partial<CreateSkillInput>): Promise<Skill> =>
    http.request<Skill>(API_ROUTES.skill(id), { method: 'PATCH', body: input }),
  disable: (id: string): Promise<Skill> =>
    http.request<Skill>(API_ROUTES.skill(id), { method: 'DELETE' }),
  import: (payload: {
    url?: string;
    bundle?: unknown[];
    origin?: string;
    source?: string;
    package?: string;
  }): Promise<{ status: string; created: number; skipped: number }> =>
    http.request<{ status: string; created: number; skipped: number }>(API_ROUTES.skillsImport, {
      method: 'POST',
      body: payload,
      timeoutMs: 30000,
    }),
} as const;

/** Compétences rattachées à un agent précis (spécialisation). */
export const agentSkillsApi = {
  list: (agentId: string): Promise<{ items: Skill[] }> =>
    http.requestWithRetry<{ items: Skill[] }>(API_ROUTES.agentSkills(agentId)),
  attach: (agentId: string, skillId: string): Promise<unknown> =>
    http.request<unknown>(API_ROUTES.agentSkills(agentId), {
      method: 'POST',
      body: { skill_id: skillId },
    }),
  detach: (agentId: string, skillId: string): Promise<unknown> =>
    http.request<unknown>(API_ROUTES.agentSkill(agentId, skillId), { method: 'DELETE' }),
} as const;
