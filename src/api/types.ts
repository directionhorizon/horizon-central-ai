/**
 * Types des contrats API réellement exposés par backend/app.py (v1).
 * Toute divergence constatée avec docs/contracts/CORE_API_CONTRACT_v0.1.md
 * est signalée en commentaire, sans être corrigée ici.
 */

/** Statut d'exécution renvoyé par le backend. Aucun modèle n'est branché :
 *  la valeur observée est toujours `accepted_no_model`. */
export type ExecutionStatus = 'accepted_no_model' | 'completed' | 'failed' | string;

export type MessageRole = 'user' | 'assistant' | 'system';

export interface SessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface SessionDetail extends SessionSummary {
  messages: SessionMessage[];
}

/** GET /sessions renvoie { items: [...] } sans métadonnées de pagination. */
export interface SessionListResponse {
  items: SessionSummary[];
}

export interface ExecutionInfo {
  status: ExecutionStatus;
  provider_id: string | null;
  model_id: string | null;
  fallback_used: boolean;
}

/** Réponse 202 de POST /sessions/{id}/messages. */
export interface MessageAcceptedResponse {
  session_id: string;
  message: SessionMessage;
  execution: ExecutionInfo;
  warnings: string[];
}

export interface SessionResetResponse {
  session_id: string;
  status: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export type CapabilityStatus = 'available' | 'not_configured' | 'unverified' | 'degraded' | 'unavailable';

export interface Capability {
  id: string;
  status: CapabilityStatus;
  verified_at: string | null;
  detail: string;
}

export interface CapabilitiesResponse {
  schema_version: string;
  generated_at: string;
  capabilities: Capability[];
}
