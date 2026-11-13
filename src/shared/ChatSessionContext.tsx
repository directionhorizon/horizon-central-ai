import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { sessionsApi } from '../api/sessions';
import { ApiError, describeApiError, toApiError } from '../api/errors';
import type { ExecutionInfo, MessageRole, SessionMessage, SessionSummary } from '../api/types';

export type ChatAttachment = {
  name: string;
  meta: string;
  type: 'code' | 'document';
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  time: string;
  attachment?: ChatAttachment;
};

/** États explicites de chargement exposés à l'UI. */
export type ChatSessionStatus = 'idle' | 'loading' | 'ready' | 'error';

type ChatSessionValue = {
  /** Messages de la session courante, lus depuis le backend. */
  messages: ChatMessage[];
  sessionId: string | null;
  sessionTitle: string | null;
  status: ChatSessionStatus;
  error: ApiError | null;
  errorMessage: string | null;
  /** Statut d'exécution renvoyé par le backend (accepted_no_model conservé tel quel). */
  execution: ExecutionInfo | null;
  warnings: string[];
  sessions: SessionSummary[];
  sessionsLoading: boolean;
  refreshSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<string | null>;
  ensureSession: () => Promise<string | null>;
  loadSession: (id: string) => Promise<void>;
  sendMessage: (content: string, attachment?: ChatAttachment) => Promise<void>;
  resetSession: () => Promise<void>;
  /** Compatibilité : envoi asynchrone déclenché sans attendre le résultat. */
  addUserMessage: (content: string, attachment?: ChatAttachment) => void;
  clearError: () => void;
};

const STORAGE_KEY = 'horizon-local-ai:last-session:v1';

const formatTime = (value: string | undefined): string => {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const toChatMessage = (message: SessionMessage): ChatMessage => ({
  id: message.id,
  role: message.role,
  content: message.content,
  time: formatTime(message.created_at),
});

/** localStorage : simple mémorisation du dernier identifiant utile. */
const readLastSessionId = (): string | null => {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value && value.trim().length > 0 ? value : null;
  } catch {
    return null;
  }
};

const writeLastSessionId = (id: string): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Stockage désactivé ou plein : le serveur reste la source de vérité.
  }
};

const clearLastSessionId = (): void => {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignoré volontairement.
  }
};

const SESSION_ROUTE = /^\/(?:workbench|control|cockpit)\/([^/]+)\/?$/;
const CONVERSATION_ROUTES = ['/workbench', '/control', '/cockpit'];

const isConversationPath = (pathname: string): boolean =>
  CONVERSATION_ROUTES.some((base) => pathname === base || pathname === `${base}/`);

const conversationBase = (pathname: string): string => {
  if (pathname.startsWith('/control')) return '/control';
  if (pathname.startsWith('/cockpit')) return '/cockpit';
  return '/workbench';
};

const ChatSessionContext = createContext<ChatSessionValue | null>(null);

export function ChatSessionProvider({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string | null>(null);
  const [status, setStatus] = useState<ChatSessionStatus>('idle');
  const [error, setError] = useState<ApiError | null>(null);
  const [execution, setExecution] = useState<ExecutionInfo | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const sessionIdRef = useRef<string | null>(null);
  const loadedRef = useRef<string | null>(null);
  const bootstrappingRef = useRef(false);

  const routeSessionId = useMemo(() => {
    const match = SESSION_ROUTE.exec(location.pathname);
    return match ? decodeURIComponent(match[1]) : null;
  }, [location.pathname]);

  const refreshSessions = useCallback(async (): Promise<void> => {
    setSessionsLoading(true);
    try {
      const response = await sessionsApi.list();
      setSessions(response.items);
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (id: string): Promise<void> => {
    setStatus('loading');
    setError(null);
    try {
      const detail = await sessionsApi.get(id);
      setSessionId(detail.id);
      sessionIdRef.current = detail.id;
      setSessionTitle(detail.title);
      setMessages(detail.messages.map(toChatMessage));
      writeLastSessionId(detail.id);
      loadedRef.current = detail.id;
      setStatus('ready');
    } catch (caught) {
      const apiError = toApiError(caught);
      setError(apiError);
      setStatus('error');
      if (apiError.status === 404) {
        sessionIdRef.current = null;
        loadedRef.current = null;
        setSessionId(null);
        setMessages([]);
        clearLastSessionId();
      }
    }
  }, []);

  const createSession = useCallback(
    async (title?: string): Promise<string | null> => {
      setStatus('loading');
      setError(null);
      try {
        const created = await sessionsApi.create(title ? { title } : {});
        setSessionId(created.id);
        sessionIdRef.current = created.id;
        loadedRef.current = created.id;
        setSessionTitle(created.title);
        setMessages([]);
        setExecution(null);
        setWarnings([]);
        writeLastSessionId(created.id);
        setSessions((current) => [created, ...current.filter((item) => item.id !== created.id)]);
        navigate(`${conversationBase(location.pathname)}/${created.id}`, { replace: false });
        setStatus('ready');
        return created.id;
      } catch (caught) {
        setError(toApiError(caught));
        setStatus('error');
        return null;
      }
    },
    [location.pathname, navigate],
  );

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (sessionIdRef.current) return sessionIdRef.current;
    return createSession();
  }, [createSession]);

  const sendMessage = useCallback(
    async (content: string, attachment?: ChatAttachment): Promise<void> => {
      const trimmed = content.trim();
      if (!trimmed && !attachment) return;

      const targetId = await ensureSession();
      if (!targetId) return;

      setStatus('loading');
      setError(null);

      const optimistic: ChatMessage = {
        id: `local-${Date.now()}`,
        role: 'user',
        content: trimmed || 'Please review the attached file.',
        time: formatTime(undefined),
        attachment,
      };
      setMessages((current) => [...current, optimistic]);

      try {
        const response = await sessionsApi.sendMessage(
          targetId,
          trimmed || 'Please review the attached file.',
        );
        setExecution(response.execution);
        setWarnings(
          attachment
            ? [
                ...response.warnings,
                `Pièce jointe « ${attachment.name} » non transmise : le backend n'accepte que le champ content.`,
              ]
            : response.warnings,
        );
        const detail = await sessionsApi.get(targetId);
        setMessages(detail.messages.map(toChatMessage));
        setSessionTitle(detail.title);
        setStatus('ready');
      } catch (caught) {
        setMessages((current) => current.filter((item) => item.id !== optimistic.id));
        setError(toApiError(caught));
        setStatus('error');
      }
    },
    [ensureSession],
  );

  const resetSession = useCallback(async (): Promise<void> => {
    const targetId = await ensureSession();
    if (!targetId) return;
    setStatus('loading');
    setError(null);
    try {
      await sessionsApi.reset(targetId);
      setExecution(null);
      setWarnings([]);
      const detail = await sessionsApi.get(targetId);
      setMessages(detail.messages.map(toChatMessage));
      setSessionTitle(detail.title);
      setStatus('ready');
    } catch (caught) {
      setError(toApiError(caught));
      setStatus('error');
    }
  }, [ensureSession]);

  const addUserMessage = useCallback(
    (content: string, attachment?: ChatAttachment): void => {
      void sendMessage(content, attachment);
    },
    [sendMessage],
  );

  const clearError = useCallback((): void => {
    setError(null);
    setStatus((current) => (current === 'error' ? 'ready' : current));
  }, []);

  const errorMessage = useMemo(() => (error ? describeApiError(error) : null), [error]);

  const value = useMemo<ChatSessionValue>(
    () => ({
      messages,
      sessionId,
      sessionTitle,
      status,
      error,
      errorMessage,
      execution,
      warnings,
      sessions,
      sessionsLoading,
      refreshSessions,
      createSession,
      ensureSession,
      loadSession,
      sendMessage,
      resetSession,
      addUserMessage,
      clearError,
    }),
    [
      messages,
      sessionId,
      sessionTitle,
      status,
      error,
      errorMessage,
      execution,
      warnings,
      sessions,
      sessionsLoading,
      refreshSessions,
      createSession,
      ensureSession,
      loadSession,
      sendMessage,
      resetSession,
      addUserMessage,
      clearError,
    ],
  );

  // Navigation pilotée par l'URL : /workbench/:id ou /control/:id.
  useEffect(() => {
    if (routeSessionId) {
      if (loadedRef.current !== routeSessionId) void loadSession(routeSessionId);
      return;
    }
    if (!isConversationPath(location.pathname)) return;
    if (bootstrappingRef.current) return;

    bootstrappingRef.current = true;
    const base = conversationBase(location.pathname);

    void (async () => {
      try {
        const stored = readLastSessionId();
        let targetId: string | null = null;

        if (stored) {
          const list = await sessionsApi.list();
          setSessions(list.items);
          if (list.items.some((item) => item.id === stored)) targetId = stored;
        }
        if (!targetId) {
          const created = await sessionsApi.create();
          targetId = created.id;
          setSessions((current) => [created, ...current]);
        }

        setSessionId(targetId);
        sessionIdRef.current = targetId;
        writeLastSessionId(targetId);
        navigate(`${base}/${targetId}`, { replace: true });
      } catch (caught) {
        setError(toApiError(caught));
        setStatus('error');
      } finally {
        bootstrappingRef.current = false;
      }
    })();
  }, [routeSessionId, location.pathname, navigate, loadSession]);

  return <ChatSessionContext.Provider value={value}>{children}</ChatSessionContext.Provider>;
}

export function useChatSession() {
  const value = useContext(ChatSessionContext);
  if (!value) throw new Error('useChatSession must be used inside ChatSessionProvider');
  return value;
}
