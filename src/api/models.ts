/** API du gestionnaire de modèles IA — routes réelles /api/v1/models. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { LlmProvider, ModelSelection, ProviderStatus } from './entities';

export interface ModelsResponse {
  items: LlmProvider[];
  selection: ModelSelection;
}

export interface ProviderTestResponse {
  id: string;
  status: ProviderStatus;
  detail: string;
  models: string[];
}

export interface CreateProviderInput {
  name: string;
  base_url: string;
  kind?: string;
  api_key_env?: string;
  default_model?: string;
}

export const modelsApi = {
  list: (): Promise<ModelsResponse> => http.requestWithRetry<ModelsResponse>(API_ROUTES.models),
  create: (input: CreateProviderInput): Promise<LlmProvider> =>
    http.request<LlmProvider>(API_ROUTES.models, { method: 'POST', body: input }),
  update: (id: string, input: Partial<CreateProviderInput>): Promise<LlmProvider> =>
    http.request<LlmProvider>(API_ROUTES.model(id), { method: 'PATCH', body: input }),
  remove: (id: string): Promise<{ id: string; status: string }> =>
    http.request<{ id: string; status: string }>(API_ROUTES.model(id), { method: 'DELETE' }),
  test: (id: string): Promise<ProviderTestResponse> =>
    http.request<ProviderTestResponse>(API_ROUTES.modelTest(id), { method: 'POST', timeoutMs: 20000 }),
  getSelection: (): Promise<ModelSelection> =>
    http.requestWithRetry<ModelSelection>(API_ROUTES.modelSelection),
  setSelection: (selection: ModelSelection): Promise<ModelSelection> =>
    http.request<ModelSelection>(API_ROUTES.modelSelection, { method: 'PUT', body: selection }),
  chatTest: (providerId: string, message: string): Promise<{ content: string; model: string; provider_id: string }> =>
    http.request<{ content: string; model: string; provider_id: string }>(`${API_ROUTES.models}/chat-test`, {
      method: 'POST',
      body: { provider_id: providerId, message },
      timeoutMs: 90000,
    }),
} as const;
