import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, Plus, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';
import { integrationsApi } from '../../api/integrations';
import { describeApiError } from '../../api/errors';
import type {
  Integration,
  IntegrationCatalogResponse,
  IntegrationStats,
  IntegrationStatus,
  IntegrationTestResult,
} from '../../api/entities';

const STATUS_TONE: Record<IntegrationStatus, string> = {
  connected: 'hz-badge--ok',
  not_configured: '',
  pending: 'hz-badge--warn',
  expired: 'hz-badge--warn',
  unavailable: 'hz-badge--danger',
  error: 'hz-badge--danger',
  partial: 'hz-badge--warn',
};

const STATUS_TEXT: Record<IntegrationStatus, string> = {
  connected: 'Connecté (vérifié)',
  not_configured: 'Non configuré',
  pending: 'En attente d’autorisation',
  expired: 'Autorisation expirée',
  unavailable: 'Indisponible',
  error: 'Erreur',
  partial: 'Connexion partielle',
};

/**
 * Espace « Connexions et intégrations ».
 *
 * Aucune clé n'est saisie ni affichée : on ne renseigne que le NOM de la variable
 * d'environnement qui la porte. Un service n'est déclaré connecté qu'après un
 * test réel exécuté côté backend.
 */
export function Integrations() {
  const [catalog, setCatalog] = useState<IntegrationCatalogResponse | null>(null);
  const [items, setItems] = useState<Integration[]>([]);
  const [stats, setStats] = useState<IntegrationStats | null>(null);
  const [category, setCategory] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tests, setTests] = useState<Record<string, IntegrationTestResult>>({});
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '',
    category: 'app',
    method: 'api_key',
    endpoint: '',
    api_key_env: '',
    permissions: '',
    capabilities: '',
  });

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [nextCatalog, nextList] = await Promise.all([
        integrationsApi.catalog(),
        integrationsApi.list(category ? { category } : {}),
      ]);
      setCatalog(nextCatalog);
      setItems(nextList.items);
      setStats(nextList.stats);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const labels = useMemo(() => {
    const categories = new Map((catalog?.categories ?? []).map((item) => [item.id, item.label]));
    const methods = new Map((catalog?.methods ?? []).map((item) => [item.id, item.label]));
    return { categories, methods };
  }, [catalog]);

  const create = async () => {
    if (!form.name.trim()) {
      setError('Le nom du service est obligatoire.');
      return;
    }
    setBusy('create');
    setError(null);
    setNotice(null);
    try {
      await integrationsApi.create({
        name: form.name.trim(),
        category: form.category,
        method: form.method,
        endpoint: form.endpoint.trim() || undefined,
        api_key_env: form.api_key_env.trim() || undefined,
        permissions: form.permissions.trim() || undefined,
        capabilities: form.capabilities.trim() || undefined,
      });
      setNotice('Fiche créée. Lancez un test pour vérifier réellement la connexion.');
      setForm({ ...form, name: '', endpoint: '', api_key_env: '', permissions: '', capabilities: '' });
      setShowForm(false);
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  const test = async (integration: Integration) => {
    setBusy(integration.id);
    setError(null);
    try {
      const result = await integrationsApi.test(integration.id);
      setTests((current) => ({ ...current, [integration.id]: result }));
      setNotice(
        result.verified
          ? `${integration.name} : connexion vérifiée (${result.detail}).`
          : `${integration.name} : non vérifiée — ${result.detail}.`,
      );
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  const archive = async (integration: Integration) => {
    setBusy(integration.id);
    try {
      await integrationsApi.archive(integration.id);
      setNotice(`${integration.name} archivé (aucune donnée supprimée).`);
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#090c13] text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[.18em] text-cyan-300">
            HORIZON CENTRAL AI / INTÉGRATIONS
          </p>
          <h1 className="mt-1 text-lg font-semibold tracking-tight">Connexions et intégrations</h1>
          <p className="mt-1 text-xs text-slate-500">
            Orchestrateurs, applications, fournisseurs IA, MCP, API, machines, stockage, communication.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" className="hz-btn" onClick={() => void refresh()}>
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Actualiser
          </button>
          <button type="button" className="hz-btn hz-btn--primary" onClick={() => setShowForm((value) => !value)}>
            <Plus size={12} /> Nouvelle connexion
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-4 p-5">
        {error && (
          <div className="hz-alert hz-alert--danger">
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
            <p className="hz-alert__text">{error}</p>
          </div>
        )}
        {notice && (
          <div className="hz-alert hz-alert--info">
            <CheckCircle2 size={15} className="mt-0.5 shrink-0" />
            <p className="hz-alert__text">{notice}</p>
          </div>
        )}

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="hz-kpi">
            <p className="hz-kpi__label">Connexions enregistrées</p>
            <p className="hz-kpi__value">{stats?.total ?? 0}</p>
          </div>
          <div className="hz-kpi">
            <p className="hz-kpi__label">Vérifiées réellement</p>
            <p className="hz-kpi__value">{stats?.connected ?? 0}</p>
          </div>
          <div className={stats && stats.needs_action > 0 ? 'hz-kpi hz-kpi--accent' : 'hz-kpi'}>
            <p className="hz-kpi__label">À traiter</p>
            <p className="hz-kpi__value">{stats?.needs_action ?? 0}</p>
          </div>
        </section>

        <div className="flex flex-wrap items-center gap-1.5">
          <button type="button" className={category === '' ? 'hz-btn hz-btn--primary' : 'hz-btn'} onClick={() => setCategory('')}>
            Toutes
          </button>
          {(catalog?.categories ?? []).map((item) => (
            <button
              key={item.id}
              type="button"
              className={category === item.id ? 'hz-btn hz-btn--primary' : 'hz-btn'}
              onClick={() => setCategory(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {showForm && (
          <section className="hz-panel p-4">
            <p className="hz-eyebrow">Nouvelle connexion</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <input className="hz-input" placeholder="Nom du service" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              <select className="hz-select" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
                {(catalog?.categories ?? []).map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
              <select className="hz-select" value={form.method} onChange={(event) => setForm({ ...form, method: event.target.value })}>
                {(catalog?.methods ?? []).map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
              <input className="hz-input" placeholder="Endpoint (https://… ou hôte:port)" value={form.endpoint} onChange={(event) => setForm({ ...form, endpoint: event.target.value })} />
              <input className="hz-input" placeholder="Nom de la variable de clé" value={form.api_key_env} onChange={(event) => setForm({ ...form, api_key_env: event.target.value })} />
              <input className="hz-input" placeholder="Permissions demandées" value={form.permissions} onChange={(event) => setForm({ ...form, permissions: event.target.value })} />
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className="hz-hint flex items-center gap-1.5">
                <ShieldCheck size={12} /> Ne saisissez jamais une clé ici : indiquez seulement le nom de la variable.
              </p>
              <button type="button" className="hz-btn hz-btn--primary" disabled={busy === 'create'} onClick={() => void create()}>
                {busy === 'create' ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />} Enregistrer
              </button>
            </div>
          </section>
        )}

        <section className="space-y-2">
          {items.map((integration) => {
            const result = tests[integration.id];
            return (
              <article key={integration.id} className="hz-card p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-100">{integration.name}</span>
                  <span className="hz-badge">{labels.categories.get(integration.category) ?? integration.category}</span>
                  <span className="hz-badge">{labels.methods.get(integration.method) ?? integration.method}</span>
                  <span className={`hz-badge ${STATUS_TONE[integration.status]}`}>{STATUS_TEXT[integration.status]}</span>
                  {integration.api_key_env && (
                    <span className={integration.secret_present ? 'hz-badge hz-badge--ok' : 'hz-badge hz-badge--warn'}>
                      clé {integration.secret_present ? 'présente' : 'absente'} ({integration.api_key_env})
                    </span>
                  )}
                </div>
                <p className="hz-hint mt-1">
                  {integration.endpoint_host ? `hôte : ${integration.endpoint_host} · ` : 'aucun endpoint · '}
                  vérifié :{' '}
                  {integration.last_checked_at
                    ? new Date(integration.last_checked_at).toLocaleString()
                    : 'jamais'}
                  {integration.permissions ? ` · permissions : ${integration.permissions}` : ''}
                  {integration.last_error ? ` · ${integration.last_error}` : ''}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="hz-btn"
                    disabled={busy === integration.id}
                    onClick={() => void test(integration)}
                  >
                    {busy === integration.id ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} Tester
                  </button>
                  <button
                    type="button"
                    className="hz-btn hz-btn--ghost"
                    disabled={busy === integration.id}
                    onClick={() => void archive(integration)}
                  >
                    <Trash2 size={12} /> Archiver
                  </button>
                  {result && (
                    <span className={result.verified ? 'hz-hint text-emerald-300' : 'hz-hint text-amber-200'}>
                      {result.verified ? 'vérifié' : 'non vérifié'} · {result.detail}
                    </span>
                  )}
                </div>
              </article>
            );
          })}
          {items.length === 0 && !loading && (
            <p className="hz-card p-6 text-center text-xs text-slate-500">
              Aucune connexion enregistrée. Créez une fiche pour centraliser un service.
            </p>
          )}
        </section>
      </main>
    </div>
  );
}