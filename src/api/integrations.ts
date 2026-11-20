/** API des connexions et intégrations (registre central). */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type {
  Integration,
  IntegrationCatalogResponse,
  IntegrationListResponse,
  IntegrationTestResult,
} from './entities';

export interface CreateIntegrationInput {
  name: string;
  category: string;
  method: string;
  endpoint?: string;
  permissions?: string;
  capabilities?: string;
  /** Nom de la variable d'environnement : jamais la clé elle-même. */
  api_key_env?: string;
  config?: Record<string, unknown>;
}

export interface OauthProvider {
  label: string;
  configured: boolean;
  redirect_uri: string;
  scope: string;
}

export interface OauthStartResult {
  provider: string;
  authorize_url: string;
  state: string;
}

export const integrationsApi = {
  oauthProviders: (): Promise<{ items: Record<string, OauthProvider> }> =>
    http.requestWithRetry<{ items: Record<string, OauthProvider> }>(
      API_ROUTES.integrationsOauthProviders,
    ),
  oauthStart: (provider: string, name = ''): Promise<OauthStartResult> =>
    http.request<OauthStartResult>(API_ROUTES.integrationOauthStart(provider, name)),
  catalog: (): Promise<IntegrationCatalogResponse> =>
    http.requestWithRetry<IntegrationCatalogResponse>(API_ROUTES.integrationsCatalog),
  list: (params: { category?: string; includeArchived?: boolean } = {}): Promise<IntegrationListResponse> => {
    const search = new URLSearchParams();
    if (params.category) search.set('category', params.category);
    if (params.includeArchived) search.set('include_archived', 'true');
    const suffix = search.toString() ? `?${search.toString()}` : '';
    return http.requestWithRetry<IntegrationListResponse>(`${API_ROUTES.integrations}${suffix}`);
  },
  create: (input: CreateIntegrationInput): Promise<Integration> =>
    http.request<Integration>(API_ROUTES.integrations, { method: 'POST', body: input }),
  update: (id: string, input: Partial<CreateIntegrationInput> & { status?: string }): Promise<Integration> =>
    http.request<Integration>(API_ROUTES.integration(id), { method: 'PATCH', body: input }),
  archive: (id: string): Promise<Integration> =>
    http.request<Integration>(API_ROUTES.integration(id), { method: 'DELETE' }),
  test: (id: string): Promise<IntegrationTestResult> =>
    http.request<IntegrationTestResult>(API_ROUTES.integrationTest(id), {
      method: 'POST',
      timeoutMs: 20000,
    }),
} as const;