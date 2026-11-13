import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { capabilitiesApi } from '../api/capabilities';
import { apiConfig } from '../config/env';
import { describeApiError } from '../api/errors';

const POLL_MS = 15000;

/**
 * Garde-fou backend : l'interface ne reste jamais silencieusement inutilisable.
 *
 * - l'application s'affiche normalement dès que le moteur répond ;
 * - si le moteur local devient injoignable (arrêt, port occupé, redémarrage),
 *   un écran explicite remplace l'interface, avec la cause mesurée et un bouton
 *   de reconnexion manuelle ;
 * - la surveillance est passive (une requête légère toutes les 15 s) et ne
 *   bloque pas le premier affichage.
 */
export function BackendUnavailable({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'checking' | 'online' | 'offline'>('checking');
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);

  const check = useCallback(async (): Promise<void> => {
    setAttempt((value) => value + 1);
    try {
      await capabilitiesApi.health();
      setState('online');
      setMessage('');
    } catch (caught) {
      setState('offline');
      setMessage(describeApiError(caught));
    }
  }, []);

  useEffect(() => {
    void check();
    const timer = window.setInterval(() => {
      void check();
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [check]);

  if (state !== 'offline') {
    return <>{children}</>;
  }

  return (
    <div className="hz-offline" role="alert">
      <div className="hz-offline__card">
        <p className="hz-offline__eyebrow">HORIZON CENTRAL AI · moteur local</p>
        <h1 className="hz-offline__title">
          <AlertTriangle size={18} /> Moteur local injoignable
        </h1>
        <p className="hz-offline__text">
          L’interface ne peut plus communiquer avec le moteur local
          (<code>{apiConfig.baseUrl}</code>). Les données déjà présentes sur l’ordinateur ne sont pas
          perdues.
        </p>
        <ul className="hz-offline__list">
          <li>Vérifiez que le moteur est démarré : relancez le raccourci <strong>HORIZON CENTRAL AI</strong>.</li>
          <li>Si le moteur a été arrêté volontairement, relancez-le puis cliquez sur « Réessayer ».</li>
          <li>Après un redémarrage, le port local reste le même : aucune configuration à refaire.</li>
        </ul>
        {message && <p className="hz-offline__detail">Cause mesurée : {message}</p>}
        <div className="hz-offline__actions">
          <button type="button" className="hz-btn hz-btn--primary" onClick={() => void check()}>
            <RefreshCw size={12} /> Réessayer ({attempt})
          </button>
          <button type="button" className="hz-btn" onClick={() => window.location.reload()}>
            Recharger l’interface
          </button>
        </div>
      </div>
    </div>
  );
}

export default BackendUnavailable;
