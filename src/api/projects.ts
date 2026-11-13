/** API projets — routes réelles /api/v1/projects. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { ProjectDetail, ProjectSummary } from './entities';

export interface ProjectListResponse {
  items: ProjectSummary[];
  default_project_id: string;
}

export interface CreateProjectInput {
  name: string;
  description?: string;
  status?: 'active' | 'paused' | 'archived';
}

export const projectsApi = {
  list: (): Promise<ProjectListResponse> => http.requestWithRetry<ProjectListResponse>(API_ROUTES.projects),
  get: (id: string): Promise<ProjectDetail> => http.request<ProjectDetail>(API_ROUTES.project(id)),
  create: (input: CreateProjectInput): Promise<ProjectSummary> =>
    http.request<ProjectSummary>(API_ROUTES.projects, { method: 'POST', body: input }),
  update: (id: string, input: Partial<CreateProjectInput>): Promise<ProjectSummary> =>
    http.request<ProjectSummary>(API_ROUTES.project(id), { method: 'PATCH', body: input }),
  archive: (id: string): Promise<ProjectSummary> =>
    http.request<ProjectSummary>(API_ROUTES.project(id), { method: 'DELETE' }),
} as const;
