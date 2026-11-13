/**
 * Module API santé / capacités — routes déjà présentes dans backend/app.py.
 */

import { API_ROUTES } from '../config/env';
import { http } from './http';
import type { CapabilitiesResponse, HealthResponse } from './types';

export const capabilitiesApi = {
  /** GET /api/v1/health */
  health: (): Promise<HealthResponse> => http.requestWithRetry<HealthResponse>(API_ROUTES.health),

  /** GET /api/v1/capabilities */
  capabilities: (): Promise<CapabilitiesResponse> =>
    http.requestWithRetry<CapabilitiesResponse>(API_ROUTES.capabilities),
} as const;

export interface BackendSnapshot {
  health: HealthResponse;
  capabilities: CapabilitiesResponse;
}
