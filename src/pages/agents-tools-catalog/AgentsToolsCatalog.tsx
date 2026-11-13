import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Boxes, CheckCircle2, ExternalLink, Loader2, Network, Plug, RefreshCw, ShieldQuestion } from 'lucide-react';
import { orchestratorsApi } from '../../api/orchestrators';
import { integrationsApi } from '../../api/integrations';
import { describeApiError } from '../../api/errors';
import type { Integration, Orchestrator } from '../../api/entities';

/**
 * Espace « Outils, agents et services ».
 *
 * Toutes les lignes affichées proviennent du moteur : orchestrateurs réellement
 * enregistrés et connexions réellement déclarées. Aucun environnement fictif.
 * Chaque domaine a sa page dédiée : on y renvoie au lieu de dupliquer.
 */

const HEALTH_LABEL: Record<string, string> = {
  available: 'Vérifié disponible',
  unavailable: 'Injoignable',
  degraded: 'Dégradé',
  unverified: 'Non vérifié',
};

const INTEGRATION_LABEL: Record<string, string> = {
  connected: 'Connecté (vérifié)',
  not_configured: 'Non configuré',
  pending: 'En attente',
  expired: 'Expiré',
  unavailable: 'Indisponible',
  error: 'Erreur',
  partial: 'Partiel',
};

export const AgentsToolsCatalog = () => {
  const navigate = useNavigate();
  const [orchestrators, setOrchestrators] = useState<Orchestrator[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [registry, connections] = await Promise.all([
        orchestratorsApi.list(),
        integrationsApi.list(),
      ]);
      setOrchestrators(registry.items ?? []);
      setIntegrations(connections.items ?? []);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const available = orchestrators.filter((item) => item.health_status === 'available').length;
  const connected = integrations.filter((item) => item.status === 'connected').length;

  return (
    <div className="min-h-screen bg-[#0A0B10] text-slate-100">
      <main className="mx-auto w-full max-w-[1500px] px-6 py-8 lg:px-10">
        <header className="mb-6">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-400">
            <Boxes size={14} /> Outils, agents et services
          </div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-white">
            Ce que HORIZON peut réellement mobiliser
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Cet espace répond à une seule question : <strong>quels agents et quels services sont
            réellement déclarés et joignables</strong>. Les listes viennent du moteur ; chaque domaine
            dispose de sa propre page pour l’ajout, la modification et le test.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="hz-btn" onClick={() => void load()}>
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Actualiser
            </button>
            <button type="button" className="hz-btn" onClick={() => navigate('/orchestrators')}>
              <Network size={12} /> Gérer les orchestrateurs
            </button>
            <button type="button" className="hz-btn" onClick={() => navigate('/integrations')}>
              <Plug size={12} /> Gérer les connexions
            </button>
          </div>
        </header>

        {error && <p className="hz-hint mb-4 text-amber-200">{error}</p>}

        <section className="hz-panel mb-4 p-4">
          <p className="hz-eyebrow">Lecture rapide</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            <p className="hz-hint">
              <strong className="text-slate-200">{orchestrators.length}</strong> orchestrateur(s) —
              <strong className="text-slate-200"> {available}</strong> vérifié(s) disponible(s)
            </p>
            <p className="hz-hint">
              <strong className="text-slate-200">{integrations.length}</strong> connexion(s) —
              <strong className="text-slate-200"> {connected}</strong> vérifiée(s) réellement
            </p>
            <p className="hz-hint">
              Aucun outil n’est exécuté depuis cette page : elle décrit, elle n’agit pas.
            </p>
          </div>
        </section>

        <section className="hz-panel mb-4 p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <p className="hz-eyebrow">Orchestrateurs (agents) enregistrés</p>
            <button type="button" className="hz-btn hz-btn--ghost" onClick={() => navigate('/orchestrators')}>
              Ouvrir le registre <ExternalLink size={11} className="ml-1 inline" />
            </button>
          </div>
          {loading ? (
            <p className="hz-hint flex items-center gap-2 p-4">
              <Loader2 size={12} className="animate-spin" /> Chargement…
            </p>
          ) : orchestrators.length === 0 ? (
            <p className="hz-hint p-4">
              Aucun orchestrateur enregistré. Créez-en un depuis la page Orchestrateurs pour qu’il
              apparaisse ici.
            </p>
          ) : (
            <ul className="divide-y divide-white/5">
              {orchestrators.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <span className="text-sm font-medium text-slate-100">{item.name}</span>
                  <span className="hz-badge">{item.kind}</span>
                  <span
                    className={
                      item.health_status === 'available' ? 'hz-badge hz-badge--ok' : 'hz-badge hz-badge--warn'
                    }
                  >
                    {HEALTH_LABEL[item.health_status] ?? item.health_status}
                  </span>
                  <span className="hz-hint">
                    {item.capabilities.length} capacité(s) déclarée(s) · statut {item.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="hz-panel p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <p className="hz-eyebrow">Services et applications connectés</p>
            <button type="button" className="hz-btn hz-btn--ghost" onClick={() => navigate('/integrations')}>
              Ouvrir les connexions <ExternalLink size={11} className="ml-1 inline" />
            </button>
          </div>
          {loading ? (
            <p className="hz-hint flex items-center gap-2 p-4">
              <Loader2 size={12} className="animate-spin" /> Chargement…
            </p>
          ) : integrations.length === 0 ? (
            <p className="hz-hint p-4">
              Aucune connexion déclarée. Ajoutez-en une depuis la page Connexions : le nom de la
              variable de clé suffit, la valeur reste côté moteur.
            </p>
          ) : (
            <ul className="divide-y divide-white/5">
              {integrations.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <span className="text-sm font-medium text-slate-100">{item.name}</span>
                  <span className="hz-badge">{item.category}</span>
                  <span className={item.status === 'connected' ? 'hz-badge hz-badge--ok' : 'hz-badge hz-badge--warn'}>
                    {INTEGRATION_LABEL[item.status] ?? item.status}
                  </span>
                  <span className="hz-hint">
                    {item.endpoint_host || 'aucun endpoint'}
                    {item.last_checked_at
                      ? ` · testé le ${new Date(item.last_checked_at).toLocaleString()}`
                      : ' · jamais testé'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <p className="hz-hint mt-6 flex items-center gap-1.5">
          <ShieldQuestion size={12} /> Une ligne n’est « vérifiée » qu’après un test réel exécuté par
          le moteur. <CheckCircle2 size={12} /> Aucune donnée de démonstration sur cette page.
        </p>
      </main>
    </div>
  );
};
