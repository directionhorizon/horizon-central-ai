import { useCallback, useEffect, useState } from 'react';
import { capabilitiesApi } from '../api/capabilities';
import { apiConfig } from '../config/env';
import { describeApiError, toApiError } from '../api/errors';
import type { CapabilitiesResponse, HealthResponse } from '../api/types';

export type BackendHealthState = 'checking' | 'online' | 'offline';

export interface BackendSnapshotState {
  state: BackendHealthState;
  health: HealthResponse | null;
  capabilities: CapabilitiesResponse | null;
  message: string;
}

/**
 * Indicateur de santé backend.
 * Interroge /api/v1/health et /api/v1/capabilities au montage, puis à la demande.
 * Aucune donnée sensible n'est affichée.
 */
export function BackendHealth() {
  const [snapshot, setSnapshot] = useState<BackendSnapshotState>({
    state: 'checking',
    health: null,
    capabilities: null,
    message: 'Vérification du service local…',
  });

  const check = useCallback(async (): Promise<void> => {
    setSnapshot((current) => ({ ...current, state: 'checking', message: 'Vérification du service local…' }));
    try {
      const [health, capabilities] = await Promise.all([
        capabilitiesApi.health(),
        capabilitiesApi.capabilities(),
      ]);
      const available = capabilities.capabilities.filter((item) => item.status === 'available').length;
      setSnapshot({
        state: 'online',
        health,
        capabilities,
        message: `${health.service} v${health.version} · ${available}/${capabilities.capabilities.length} capacités disponibles`,
      });
    } catch (caught) {
      const error = toApiError(caught);
      setSnapshot({
        state: 'offline',
        health: null,
        capabilities: null,
        message: describeApiError(error),
      });
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  const color =
    snapshot.state === 'online' ? '#34d399' : snapshot.state === 'offline' ? '#f87171' : '#fbbf24';
  const label =
    snapshot.state === 'online' ? 'Backend en ligne' : snapshot.state === 'offline' ? 'Backend hors ligne' : 'Backend…';

  return (
    <div className="horizon-health" title={`${snapshot.message} (${apiConfig.baseUrl})`}>
      <span
        aria-hidden="true"
        style={{
          display: 'inline-block',
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: color,
          boxShadow: `0 0 8px ${color}`,
          flexShrink: 0,
        }}
      />
      <span>{label}</span>
      <button
        type="button"
        onClick={() => void check()}
        className="horizon-health-refresh"
        aria-label="Revérifier le backend"
        title="Revérifier le backend"
      >
        ↻
      </button>
      <span className="horizon-health-detail" aria-live="polite">
        {snapshot.message}
      </span>
    </div>
  );
}

export default BackendHealth;
