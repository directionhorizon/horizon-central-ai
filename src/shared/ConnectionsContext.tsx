import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type LlmConnection = {
  id: string;
  name: string;
  baseUrl: string;
  /** Nom de variable d'environnement uniquement : jamais une valeur de clé. */
  keyEnv: string;
  model: string;
  enabled: boolean;
  createdAt: string;
};

export type ToolConnection = {
  id: string;
  name: string;
  category: string;
  method: string;
  endpoint: string;
  /** Nom de variable d'environnement uniquement : jamais une valeur de clé. */
  keyEnv: string;
  permissions: string;
  capabilities: string;
  enabled: boolean;
  createdAt: string;
};

type ConnectionsState = {
  llm: LlmConnection[];
  tools: ToolConnection[];
};

type LlmInput = Omit<LlmConnection, 'id' | 'createdAt'>;
type ToolInput = Omit<ToolConnection, 'id' | 'createdAt'>;

type ConnectionsValue = {
  llmConnections: LlmConnection[];
  toolConnections: ToolConnection[];
  addLlmConnection: (input: LlmInput) => void;
  updateLlmConnection: (id: string, patch: Partial<LlmInput>) => void;
  removeLlmConnection: (id: string) => void;
  addToolConnection: (input: ToolInput) => void;
  updateToolConnection: (id: string, patch: Partial<ToolInput>) => void;
  removeToolConnection: (id: string) => void;
};

const STORAGE_KEY = 'horizon-local-ai:ui-connections:v1';
const EMPTY_STATE: ConnectionsState = { llm: [], tools: [] };

const ConnectionsContext = createContext<ConnectionsValue | null>(null);

const makeId = (prefix: string): string => {
  const random =
    typeof globalThis.crypto !== 'undefined' && typeof globalThis.crypto.randomUUID === 'function'
      ? globalThis.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${random}`;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const readString = (record: Record<string, unknown>, key: string): string =>
  typeof record[key] === 'string' ? (record[key] as string) : '';

const readBool = (record: Record<string, unknown>, key: string): boolean => record[key] === true;

const readLlm = (value: unknown): LlmConnection | null => {
  if (!isRecord(value)) return null;
  const name = readString(value, 'name').trim();
  if (!name) return null;
  return {
    id: readString(value, 'id') || makeId('llm'),
    name,
    baseUrl: readString(value, 'baseUrl').trim(),
    keyEnv: readString(value, 'keyEnv').trim(),
    model: readString(value, 'model').trim(),
    enabled: readBool(value, 'enabled'),
    createdAt: readString(value, 'createdAt') || new Date().toISOString(),
  };
};

const readTool = (value: unknown): ToolConnection | null => {
  if (!isRecord(value)) return null;
  const name = readString(value, 'name').trim();
  if (!name) return null;
  return {
    id: readString(value, 'id') || makeId('tool'),
    name,
    category: readString(value, 'category').trim(),
    method: readString(value, 'method').trim(),
    endpoint: readString(value, 'endpoint').trim(),
    keyEnv: readString(value, 'keyEnv').trim(),
    permissions: readString(value, 'permissions').trim(),
    capabilities: readString(value, 'capabilities').trim(),
    enabled: readBool(value, 'enabled'),
    createdAt: readString(value, 'createdAt') || new Date().toISOString(),
  };
};

const readState = (): ConnectionsState => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_STATE;
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return EMPTY_STATE;
    const llm = Array.isArray(parsed.llm)
      ? parsed.llm.map(readLlm).filter((item): item is LlmConnection => item !== null)
      : [];
    const tools = Array.isArray(parsed.tools)
      ? parsed.tools.map(readTool).filter((item): item is ToolConnection => item !== null)
      : [];
    return { llm, tools };
  } catch {
    return EMPTY_STATE;
  }
};

export function ConnectionsProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ConnectionsState>(readState);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Stockage indisponible ou plein : l'interface reste utilisable en mémoire.
    }
  }, [state]);

  const addLlmConnection = useCallback((input: LlmInput) => {
    const record: LlmConnection = {
      ...input,
      id: makeId('llm'),
      createdAt: new Date().toISOString(),
    };
    setState((current) => ({ ...current, llm: [record, ...current.llm] }));
  }, []);

  const updateLlmConnection = useCallback((id: string, patch: Partial<LlmInput>) => {
    setState((current) => ({
      ...current,
      llm: current.llm.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  }, []);

  const removeLlmConnection = useCallback((id: string) => {
    setState((current) => ({ ...current, llm: current.llm.filter((item) => item.id !== id) }));
  }, []);

  const addToolConnection = useCallback((input: ToolInput) => {
    const record: ToolConnection = {
      ...input,
      id: makeId('tool'),
      createdAt: new Date().toISOString(),
    };
    setState((current) => ({ ...current, tools: [record, ...current.tools] }));
  }, []);

  const updateToolConnection = useCallback((id: string, patch: Partial<ToolInput>) => {
    setState((current) => ({
      ...current,
      tools: current.tools.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  }, []);

  const removeToolConnection = useCallback((id: string) => {
    setState((current) => ({ ...current, tools: current.tools.filter((item) => item.id !== id) }));
  }, []);

  const value = useMemo<ConnectionsValue>(
    () => ({
      llmConnections: state.llm,
      toolConnections: state.tools,
      addLlmConnection,
      updateLlmConnection,
      removeLlmConnection,
      addToolConnection,
      updateToolConnection,
      removeToolConnection,
    }),
    [
      state.llm,
      state.tools,
      addLlmConnection,
      updateLlmConnection,
      removeLlmConnection,
      addToolConnection,
      updateToolConnection,
      removeToolConnection,
    ],
  );

  return <ConnectionsContext.Provider value={value}>{children}</ConnectionsContext.Provider>;
}

export function useConnections(): ConnectionsValue {
  const value = useContext(ConnectionsContext);
  if (!value) {
    throw new Error('useConnections doit être utilisé dans ConnectionsProvider');
  }
  return value;
}
