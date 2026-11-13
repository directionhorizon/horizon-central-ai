/**
 * Normalisation des erreurs réseau / HTTP.
 * Aucune donnée sensible n'est ajoutée au message affiché à l'utilisateur.
 */

export type ApiErrorKind = 'network' | 'timeout' | 'http' | 'validation' | 'parse' | 'aborted';

export interface ApiErrorInit {
  kind: ApiErrorKind;
  message: string;
  status?: number | null;
  details?: unknown;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly details: unknown;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = 'ApiError';
    this.kind = init.kind;
    this.status = init.status ?? null;
    this.details = init.details ?? null;
  }
}

export const isApiError = (value: unknown): value is ApiError => value instanceof ApiError;

/** Convertit n'importe quelle valeur levée en ApiError exploitable par l'UI. */
export function toApiError(value: unknown): ApiError {
  if (isApiError(value)) return value;
  if (value instanceof Error) {
    return new ApiError({ kind: 'network', message: value.message, details: value });
  }
  return new ApiError({ kind: 'network', message: 'Erreur inconnue lors de l’appel au service local.', details: value });
}

/** Message court, sûr, destiné à l'affichage (aucun secret, aucune stack). */
export function describeApiError(value: unknown): string {
  const error = toApiError(value);
  switch (error.kind) {
    case 'timeout':
      return 'Le service local ne répond pas dans le délai prévu. Vérifiez que le backend FastAPI est démarré.';
    case 'network':
      return 'Service local injoignable. Vérifiez le backend (http://127.0.0.1:8000) et la configuration CORS.';
    case 'aborted':
      return 'Requête annulée.';
    case 'validation':
      return `Requête refusée par le service local (HTTP 422). ${error.message}`;
    case 'parse':
      return 'Réponse illisible reçue du service local (format inattendu).';
    case 'http':
    default:
      if (error.status === 404) return 'Ressource introuvable côté service local (HTTP 404).';
      if (error.status === 500) return 'Erreur interne du service local (HTTP 500).';
      return error.status
        ? `Erreur du service local (HTTP ${error.status}). ${error.message}`
        : error.message;
  }
}
