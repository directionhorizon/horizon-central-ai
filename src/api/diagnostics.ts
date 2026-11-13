/**
 * Diagnostic technique (réservé aux administrateurs).
 *
 * L'appel échoue volontairement (401/403) lorsque `HORIZON_ADMIN_TOKEN` est
 * configuré et qu'aucun jeton n'est fourni : l'interface affiche alors un accès
 * protégé au lieu des détails d'infrastructure.
 */
import { API_ROUTES } from '../config/env';
import { http } from './http';

export interface DiagnosticsPayload {
  generated_at: string;
  version: string;
  database: { path: string; exists: boolean; size_kb: number | null };
  ui: { dist_dir: string; bundled: boolean };
  connectivity: { online: boolean; target: string; checked_at: string; error: string };
  sync_provider: { configured: boolean; provider: string; required_env: string[] };
  sync_worker: { auto_enabled: boolean; interval_s: number; env_flag: string };
  auth: { auth_enabled: boolean; token_env: string; mode: string };
  metrics: Record<string, unknown>;
  llm: {
    providers: number;
    available: number;
    key_env_names: string[];
    key_env_present: Record<string, boolean>;
  };
  integrations: { total: number; by_status: Record<string, number>; connected: number; needs_action: number };
}

export const diagnosticsApi = {
  get: (): Promise<DiagnosticsPayload> =>
    http.requestWithRetry<DiagnosticsPayload>(API_ROUTES.adminDiagnostics),
} as const;