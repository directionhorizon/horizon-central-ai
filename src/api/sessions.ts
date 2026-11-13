/**
 * Module API des sessions — couvre uniquement les routes déjà présentes
 * dans backend/app.py. Aucune route n'est ajoutée ici.
 *
 * Contraintes constatées côté backend :
 * - POST /sessions exige un corps JSON (422 sans corps) : on envoie toujours `{}`.
 * - Aucune route DELETE /sessions : la suppression de session n'est pas possible.
 * - POST /sessions/{id}/messages n'accepte qu'un champ `content` (pas de pièce jointe).
 */

import { API_ROUTES } from '../config/env';
import { http } from './http';
import type {
  MessageAcceptedResponse,
  SessionDetail,
  SessionListResponse,
  SessionResetResponse,
  SessionSummary,
} from './types';

export interface CreateSessionInput {
  title?: string;
}

export const sessionsApi = {
  /** POST /api/v1/sessions — corps toujours présent, même vide. */
  create: (input: CreateSessionInput = {}): Promise<SessionSummary> =>
    http.request<SessionSummary>(API_ROUTES.sessions, {
      method: 'POST',
      body: input.title ? { title: input.title } : {},
    }),

  /** GET /api/v1/sessions — renvoie { items } sans métadonnées de pagination. */
  list: (): Promise<SessionListResponse> =>
    http.requestWithRetry<SessionListResponse>(API_ROUTES.sessions),

  /** GET /api/v1/sessions/{id} — inclut les messages. */
  get: (id: string): Promise<SessionDetail> =>
    http.request<SessionDetail>(API_ROUTES.session(id)),

  /** POST /api/v1/sessions/{id}/messages — réponse 202 avec execution.status. */
  sendMessage: (id: string, content: string): Promise<MessageAcceptedResponse> =>
    http.request<MessageAcceptedResponse>(API_ROUTES.messages(id), {
      method: 'POST',
      body: { content },
    }),

  /** POST /api/v1/sessions/{id}/reset — supprime les messages de la session. */
  reset: (id: string): Promise<SessionResetResponse> =>
    http.request<SessionResetResponse>(API_ROUTES.reset(id), { method: 'POST' }),
} as const;
