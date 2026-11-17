/**
 * Client HTTP centralisé, unique point de sortie réseau du frontend.
 *
 * - base URL lue dans src/config/env.ts
 * - délai maximal par requête (AbortController)
 * - erreurs normalisées en ApiError
 * - aucune clé ni secret n'est jamais transmis
 */

import { apiConfig } from '../config/env';
import { ApiError } from './errors';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  method?: HttpMethod;
  /** Corps JSON. `undefined` = pas de corps envoyé. */
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
  headers?: Record<string, string>;
}

interface BackendErrorBody {
  detail?: unknown;
}

/**
 * Jeton administrateur (mode déploiement distant).
 * Saisi une seule fois via la boîte de dialogue affichée sur un 401,
 * puis conservé dans le stockage local du navigateur.
 */
const TOKEN_STORAGE_KEY = 'horizon-local-ai:admin-token:v1';

const readToken = (): string => {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)?.trim() ?? '';
  } catch {
    return '';
  }
};

const askToken = (): string => {
  const value = window.prompt('Jeton administrateur HORIZON :')?.trim() ?? '';
  if (value) {
    try {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, value);
    } catch {
      /* stockage indisponible : le jeton reste valable pour la session */
    }
  }
  return value;
};

const buildUrl = (path: string): string => {
  const base = apiConfig.baseUrl;
  if (/^https?:\/\//i.test(path)) return path;
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
};

const extractDetail = (payload: unknown): string | null => {
  if (!payload || typeof payload !== 'object') return null;
  const detail = (payload as BackendErrorBody).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const msg = (item as { msg?: unknown }).msg;
          return typeof msg === 'string' ? msg : null;
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
    if (parts.length > 0) return parts.join(' · ');
  }
  return null;
};

const readBody = async (response: Response): Promise<unknown> => {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
};

/**
 * Exécute une requête et désérialise la réponse JSON.
 * `T` est le type attendu du contrat backend.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal, timeoutMs, headers } = options;
  const controller = new AbortController();
  const effectiveTimeout = timeoutMs ?? apiConfig.timeoutMs;
  let timedOut = false;

  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, effectiveTimeout);

  const onExternalAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', onExternalAbort, { once: true });
  }

  try {
    const send = (token: string) =>
      fetch(buildUrl(path), {
        method,
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...(token ? { 'X-Horizon-Token': token } : {}),
          ...headers,
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });

    let response = await send(readToken());

    if (response.status === 401) {
      const token = askToken();
      if (token) response = await send(token);
    }

    const payload = await readBody(response);

    if (!response.ok) {
      const detail = extractDetail(payload);
      const kind = response.status === 422 ? 'validation' : 'http';
      throw new ApiError({
        kind,
        status: response.status,
        message: detail ?? `HTTP ${response.status} ${response.statusText}`.trim(),
        details: payload,
      });
    }

    if (response.status === 204) return undefined as T;
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError({
        kind: timedOut ? 'timeout' : 'aborted',
        message: timedOut
          ? `Délai dépassé (${effectiveTimeout} ms)`
          : 'Requête annulée',
        details: error,
      });
    }
    throw new ApiError({
      kind: 'network',
      message: error instanceof Error ? error.message : 'Échec réseau inconnu',
      details: error,
    });
  } finally {
    window.clearTimeout(timeoutId);
    if (signal) signal.removeEventListener('abort', onExternalAbort);
  }
}

/** Variante avec une seule nouvelle tentative, réservée aux lectures (GET). */
export async function requestWithRetry<T>(
  path: string,
  options: RequestOptions = {},
  retries = 1,
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await request<T>(path, options);
    } catch (error) {
      lastError = error;
      const retryable =
        error instanceof ApiError && (error.kind === 'network' || error.kind === 'timeout');
      if (!retryable || attempt === retries) break;
      await new Promise((resolve) => window.setTimeout(resolve, 300 * (attempt + 1)));
    }
  }
  throw lastError;
}

export const http = { request, requestWithRetry } as const;
