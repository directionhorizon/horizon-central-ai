import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { systemApi, type UpdateStatus } from '../api/system';

/**
 * Bouton « Mettre a jour ».
 *
 * Une seule action, adaptee a l'environnement :
 * - installation locale : recupere le code (git pull) et recompile l'interface ;
 * - serveur en ligne : declenche le deploiement GitHub (build + mise en ligne).
 *
 * L'etat vient du moteur (/api/v1/system/update). Aucun secret n'est affiche.
 */
export const UpdateButton = () => {
  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const timer = useRef<number | null>(null);

  const poll = useCallback(async () => {
    try {
      const next = await systemApi.updateStatus();
      setStatus(next);
      if (next.state === 'running') {
        timer.current = window.setTimeout(() => void poll(), 2500);
        return;
      }
      if (next.state === 'done') {
        setMessage(next.detail);
        setError('');
      } else if (next.state === 'error') {
        setError(next.detail);
        setMessage('');
      }
    } catch {
      /* le bouton reste disponible ; le prochain cycle reprendra */
    }
  }, []);

  useEffect(() => {
    void poll();
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [poll]);

  const start = useCallback(async () => {
    setMessage('');
    setError('');
    try {
      const next = await systemApi.startUpdate();
      setStatus(next);
      void poll();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Mise a jour impossible.');
    }
  }, [poll]);

  if (!status) return null;

  const running = status.state === 'running';
  const disabled = running || !status.available;
  const hint = !status.available
    ? `Mise a jour non disponible (${status.detail || status.mode || 'environnement inconnu'})`
    : status.mode === 'server'
      ? 'Declenche le deploiement en ligne (GitHub)'
      : 'Recupere le code et recompile l interface locale';

  return (
    <div className="hz-update" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <button
        type="button"
        onClick={() => void start()}
        disabled={disabled}
        title={hint}
        className="flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-xs font-medium text-cyan-100 hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw size={14} className={running ? 'animate-spin' : ''} />
        {running ? 'Mise a jour...' : 'Mettre a jour'}
      </button>
      {(message || error) && (
        <span
          className={`max-w-[280px] truncate text-[11px] ${error ? 'text-rose-300' : 'text-emerald-300'}`}
          title={error || message}
        >
          {error || message}
        </span>
      )}
    </div>
  );
};

export default UpdateButton;
