/** API mémoire documentaire centrale — routes réelles /api/v1/documents. */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { KnowledgeDocument } from './entities';

export interface DocumentListResponse {
  items: KnowledgeDocument[];
  count: number;
}

export interface CreateDocumentInput {
  title: string;
  content?: string;
  project_id?: string | null;
  tags?: string;
  source?: string;
}

export const documentsApi = {
  list: (params: { projectId?: string; query?: string; limit?: number } = {}): Promise<DocumentListResponse> => {
    const search = new URLSearchParams();
    if (params.projectId) search.set('project_id', params.projectId);
    if (params.query) search.set('q', params.query);
    if (params.limit) search.set('limit', String(params.limit));
    const suffix = search.toString() ? `?${search.toString()}` : '';
    return http.requestWithRetry<DocumentListResponse>(`${API_ROUTES.documents}${suffix}`);
  },
  get: (id: string): Promise<KnowledgeDocument> => http.request<KnowledgeDocument>(API_ROUTES.document(id)),
  create: (input: CreateDocumentInput): Promise<KnowledgeDocument> =>
    http.request<KnowledgeDocument>(API_ROUTES.documents, { method: 'POST', body: input }),
  update: (id: string, input: Partial<CreateDocumentInput>): Promise<KnowledgeDocument> =>
    http.request<KnowledgeDocument>(API_ROUTES.document(id), { method: 'PATCH', body: input }),
  archive: (id: string): Promise<KnowledgeDocument> =>
    http.request<KnowledgeDocument>(API_ROUTES.document(id), { method: 'DELETE' }),
} as const;
