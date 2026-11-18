/** API missions — routes réelles /api/v1/missions. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type {
  DispatchResult, Mission, MissionStatus, OrchestratorRun, Priority, StepStatus,
} from './entities';

export interface RunListResponse {
  items: OrchestratorRun[];
}

export interface RunActionResult {
  status: string;
  run?: OrchestratorRun;
  response?: Record<string, unknown>;
}

export interface MissionListResponse {
  items: Mission[];
}

export interface CreateMissionInput {
  project_id: string;
  title: string;
  description?: string;
  priority?: Priority;
  orchestrator_id?: string | null;
}

export const missionsApi = {
  list: (params: { projectId?: string; status?: string; orchestratorId?: string } = {}): Promise<MissionListResponse> => {
    const search = new URLSearchParams();
    if (params.projectId) search.set('project_id', params.projectId);
    if (params.status) search.set('status', params.status);
    if (params.orchestratorId) search.set('orchestrator_id', params.orchestratorId);
    const suffix = search.toString() ? `?${search.toString()}` : '';
    return http.requestWithRetry<MissionListResponse>(`${API_ROUTES.missions}${suffix}`);
  },
  get: (id: string): Promise<Mission> => http.request<Mission>(API_ROUTES.mission(id)),
  create: (input: CreateMissionInput): Promise<Mission> =>
    http.request<Mission>(API_ROUTES.missions, { method: 'POST', body: input }),
  update: (id: string, input: { title?: string; description?: string; status?: MissionStatus; priority?: Priority; orchestrator_id?: string | null }): Promise<Mission> =>
    http.request<Mission>(API_ROUTES.mission(id), { method: 'PATCH', body: input }),
  addStep: (id: string, title: string, assignedOrchestratorId?: string | null): Promise<Mission> =>
    http.request<Mission>(API_ROUTES.missionSteps(id), {
      method: 'POST',
      body: { title, assigned_orchestrator_id: assignedOrchestratorId ?? null },
    }),
  updateStep: (id: string, stepId: string, input: { title?: string; status?: StepStatus; error?: string }): Promise<Mission> =>
    http.request<Mission>(API_ROUTES.missionStep(id, stepId), { method: 'PATCH', body: input }),
  addCheckpoint: (id: string, label: string, stepId?: string | null, state: Record<string, unknown> = {}): Promise<Mission> =>
    http.request<Mission>(API_ROUTES.missionCheckpoints(id), {
      method: 'POST',
      body: { label, step_id: stepId ?? null, state },
    }),

  /* --- Exécution réelle CORE ↔ Hermes ----------------------------------- */
  dispatch: (id: string, input: { step_id?: string | null; orchestrator_id?: string | null } = {}): Promise<DispatchResult> =>
    http.request<DispatchResult>(API_ROUTES.missionDispatch(id), { method: 'POST', body: input }),
  listRuns: (id: string): Promise<RunListResponse> =>
    http.requestWithRetry<RunListResponse>(API_ROUTES.missionRuns(id)),
  getRun: (id: string, runId: string, refresh = true): Promise<OrchestratorRun> =>
    http.request<OrchestratorRun>(
      `${API_ROUTES.missionRun(id, runId)}?refresh=${refresh ? 'true' : 'false'}`,
      { timeoutMs: 20000 },
    ),
  stopRun: (id: string, runId: string): Promise<RunActionResult> =>
    http.request<RunActionResult>(API_ROUTES.missionRunStop(id, runId), { method: 'POST' }),
  approveRun: (id: string, runId: string, requestId: string, generation: number, choice: 'once' | 'deny'): Promise<RunActionResult> =>
    http.request<RunActionResult>(API_ROUTES.missionRunApproval(id, runId), {
      method: 'POST',
      body: { request_id: requestId, execution_generation: generation, choice },
    }),
  clarifyRun: (id: string, runId: string, requestId: string, generation: number, answer: string): Promise<RunActionResult> =>
    http.request<RunActionResult>(API_ROUTES.missionRunClarify(id, runId), {
      method: 'POST',
      body: { request_id: requestId, execution_generation: generation, answer },
    }),
} as const;
