/**
 * API de synchronisation Offline-First.
 *
 * Toutes ces routes sont facultatives : si elles échouent (réseau coupé, backend
 * arrêté), l'interface doit rester utilisable et afficher un état honnête.
 * Aucune clé de fournisseur n'est transmise ni lue ici.
 */
import { API_ROUTES } from '../config/env';
import { http } from './http';
import type {
  SyncConflictsResponse,
  SyncPullResult,
  SyncPushResult,
  SyncQueueResponse,
  SyncStatus,
} from './entities';

export const syncApi = {
  status: (): Promise<SyncStatus> => http.requestWithRetry<SyncStatus>(API_ROUTES.syncStatus),
  queue: (status: 'pending' | 'failed' | 'synced' | 'conflict' = 'pending', limit = 100): Promise<SyncQueueResponse> =>
    http.requestWithRetry<SyncQueueResponse>(
      `${API_ROUTES.syncQueue}?status=${encodeURIComponent(status)}&limit=${limit}`,
    ),
  conflicts: (resolved = false): Promise<SyncConflictsResponse> =>
    http.requestWithRetry<SyncConflictsResponse>(
      `${API_ROUTES.syncConflicts}?resolved=${resolved ? 'true' : 'false'}`,
    ),
  push: (): Promise<SyncPushResult> =>
    http.request<SyncPushResult>(API_ROUTES.syncPush, { method: 'POST', timeoutMs: 120000 }),
  retry: (): Promise<{ status: string; requeued: number }> =>
    http.request<{ status: string; requeued: number }>(API_ROUTES.syncRetry, { method: 'POST' }),
  pull: (): Promise<SyncPullResult> =>
    http.request<SyncPullResult>(API_ROUTES.syncPull, { method: 'POST', timeoutMs: 120000 }),
  resolveConflict: (id: string): Promise<unknown> =>
    http.request<unknown>(API_ROUTES.syncConflictResolve(id), { method: 'POST' }),
} as const;
