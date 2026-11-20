import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, Plus, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';
import { integrationsApi } from '../../api/integrations';
import { describeApiError } from '../../api/errors';
import { useConnections, type ToolConnection } from '../../shared/ConnectionsContext';
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

type ToolPreset = {
  id: string;
  name: string;
  category: string;
  method: string;
  endpoint: string;
  keyEnv: string;
  permissions: string;
  capabilities: string;
};

const TOOL_PRESETS: ToolPreset[] = [
  { id: 'supabase', name: 'Supabase', category: 'storage', method: 'api_key', endpoint: '', keyEnv: 'HORIZON_SUPABASE_KEY', permissions: 'read,write', capabilities: 'sync,knowledge' },
  { id: 'drive', name: 'Google Drive', category: 'storage', method: 'oauth2', endpoint: '', keyEnv: 'HORIZON_GOOGLE_DRIVE_TOKEN', permissions: 'drive.file', capabilities: 'memory-sync' },
  { id: 'github', name: 'GitHub privé', category: 'storage', method: 'api_key', endpoint: 'https://api.github.com', keyEnv: 'HORIZON_GITHUB_TOKEN', permissions: 'repo', capabilities: 'code-sync' },
  { id: 'hermes', name: 'Hermes local', category: 'orchestrator', method: 'endpoint', endpoint: 'http://127.0.0.1:8642/v1', keyEnv: 'HERMES_API_SERVER_KEY', permissions: 'runs:read,runs:write', capabilities: 'runs,sse,approval' },
  { id: 'windows', name: 'PC Windows local', category: 'machine', method: 'cli', endpoint: 'local://windows', keyEnv: '', permissions: 'local-execution', capabilities: 'system,metrics,files' },
  { id: 'mcp', name: 'Serveur MCP', category: 'mcp', method: 'mcp', endpoint: '', keyEnv: '', permissions: 'tools', capabilities: 'tools' },
  { id: 'custom', name: 'Personnalisé', category: 'app', method: 'rest', endpoint: '', keyEnv: '', permissions: '', capabilities: '' },
];

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

  const { toolConnections, addToolConnection, updateToolConnection, removeToolConnection } = useConnections();
  const [toolPreset, setToolPreset] = useState(TOOL_PRESETS[0].id);
  const [toolName, setToolName] = useState(TOOL_PRESETS[0].name);
  const [toolCategory, setToolCategory] = useState(TOOL_PRESETS[0].category);
  const [toolMethod, setToolMethod] = useState(TOOL_PRESETS[0].method);
  const [toolEndpoint, setToolEndpoint] = useState(TOOL_PRESETS[0].endpoint);
  const [toolKeyEnv, setToolKeyEnv] = useState(TOOL_PRESETS[0].keyEnv);
  const [toolPermissions, setToolPermissions] = useState(TOOL_PRESETS[0].permissions);
  const [toolCapabilities, setToolCapabilities] = useState(TOOL_PRESETS[0].capabilities);
  const [localNotice, setLocalNotice] = useState<string | null>(null);
  const [oauthProviders, setOauthProviders] = useState<
    Record<string, { label: string; configured: boolean; redirect_uri: string; scope: string }>
  >({});
  const [oauthName, setOauthName] = useState('');
  const [oauthBusy, setOauthBusy] = useState<string | null>(null);

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

  useEffect(() => {
    void (async () => {
      try {
        const providers = await integrationsApi.oauthProviders();
        setOauthProviders(providers.items);
      } catch {
        /* registre OAuth indisponible : la section reste vide */
      }
    })();
  }, []);

  const connectOauth = async (provider: string) => {
    setOauthBusy(provider);
    setError(null);
    setNotice(null);
    try {
      const started = await integrationsApi.oauthStart(provider, oauthName.trim());
      window.open(started.authorize_url, '_blank', 'noopener');
      setNotice(
        'Autorisez la connexion dans l’onglet ouvert, puis actualisez la liste des connexions.',
      );
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setOauthBusy(null);
    }
  };

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

  const applyToolPreset = (presetId: string) => {
    setToolPreset(presetId);
    const preset = TOOL_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    setToolName(preset.name);
    setToolCategory(preset.category);
    setToolMethod(preset.method);
    setToolEndpoint(preset.endpoint);
    setToolKeyEnv(preset.keyEnv);
    setToolPermissions(preset.permissions);
    setToolCapabilities(preset.capabilities);
  };

  const handleAddLocalTool = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanName = toolName.trim();
    if (!cleanName) return;
    addToolConnection({
      name: cleanName,
      category: toolCategory.trim() || 'app',
      method: toolMethod.trim() || 'rest',
      endpoint: toolEndpoint.trim(),
      keyEnv: toolKeyEnv.trim(),
      permissions: toolPermissions.trim(),
      capabilities: toolCapabilities.trim(),
      enabled: true,
    });
    setLocalNotice(`Connexion « ${cleanName} » enregistrée dans le navigateur.`);
    setToolPreset('custom');
    setToolName('');
    setToolCategory('app');
    setToolMethod('rest');
    setToolEndpoint('');
    setToolKeyEnv('');
    setToolPermissions('');
    setToolCapabilities('');
  };

  const toggleLocalTool = (connection: ToolConnection) => {
    updateToolConnection(connection.id, { enabled: !connection.enabled });
    setLocalNotice(
      `Connexion « ${connection.name} » ${connection.enabled ? 'désactivée' : 'activée'} dans l’interface.`,
    );
  };

  const handleRemoveLocalTool = (connection: ToolConnection) => {
    removeToolConnection(connection.id);
    setLocalNotice(`Connexion « ${connection.name} » retirée de l’interface.`);
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

      <div className="mx-auto max-w-[1400px] space-y-4 p-5">
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

        <section className="hz-panel p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="hz-eyebrow">Connexion automatique (OAuth)</p>
              <h2 className="mt-1 text-base font-semibold text-slate-100">Comptes (Gmail, réseaux sociaux)</h2>
              <p className="hz-hint mt-1 max-w-3xl">
                Aucun jeton à saisir : cliquez « Connecter », puis autorisez dans l’onglet qui s’ouvre.
                Le jeton est récupéré et stocké localement, jamais affiché ni journalisé.
              </p>
            </div>
            <input
              className="hz-input max-w-[240px]"
              placeholder="Nom du compte (facultatif)"
              value={oauthName}
              onChange={(event) => setOauthName(event.target.value)}
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(oauthProviders).map(([key, provider]) => (
              <div key={key} className="hz-card flex flex-wrap items-center gap-2 p-3">
                <span className="text-sm font-semibold text-slate-100">{provider.label}</span>
                <span className={provider.configured ? 'hz-badge hz-badge--ok' : 'hz-badge hz-badge--warn'}>
                  {provider.configured ? 'application configurée' : 'application à créer'}
                </span>
                <button
                  type="button"
                  className="hz-btn hz-btn--primary"
                  disabled={!provider.configured || oauthBusy === key}
                  onClick={() => void connectOauth(key)}
                >
                  {oauthBusy === key ? <Loader2 size={12} className="animate-spin" /> : null} Connecter
                </button>
              </div>
            ))}
            {Object.keys(oauthProviders).length === 0 && (
              <p className="hz-hint">Aucun fournisseur OAuth disponible pour le moment.</p>
            )}
          </div>
        </section>

        <section className="hz-panel p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="hz-eyebrow">Interface locale · sans backend</p>
              <h2 className="mt-1 text-base font-semibold text-slate-100">Connexions outils déclarées ici</h2>
              <p className="hz-hint mt-1 max-w-3xl">
                Fiches conservées dans ce navigateur, distinctes des connexions vérifiées par le moteur. Aucun appel réseau,
                aucun test et aucune clé ne sont effectués ou stockés ici : indiquez seulement un nom de variable
                d’environnement.
              </p>
            </div>
            <span className="hz-badge hz-badge--ok">{toolConnections.length} fiche(s)</span>
          </div>

          {localNotice && (
            <div className="hz-alert hz-alert--info mt-4">
              <CheckCircle2 size={15} className="mt-0.5 shrink-0" />
              <p className="hz-alert__text">{localNotice}</p>
            </div>
          )}

          <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_400px]">
            <div className="space-y-2">
              {toolConnections.map((connection) => (
                <article key={connection.id} className="hz-card p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-100">{connection.name}</p>
                      <p className="hz-hint mt-1 truncate">{connection.endpoint || 'aucun endpoint'}</p>
                      <p className="hz-hint mt-1">
                        catégorie : {connection.category || 'app'} · méthode : {connection.method || 'rest'}
                        {connection.keyEnv ? ` · variable : ${connection.keyEnv}` : ''}
                      </p>
                      {connection.permissions && (
                        <p className="hz-hint mt-1">permissions : {connection.permissions}</p>
                      )}
                      {connection.capabilities && (
                        <p className="hz-hint mt-1">capacités : {connection.capabilities}</p>
                      )}
                    </div>
                    <span
                      className={
                        connection.enabled
                          ? 'hz-badge hz-badge--ok'
                          : 'hz-badge'
                      }
                    >
                      {connection.enabled ? 'active dans l’interface' : 'désactivée'}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="hz-btn"
                      onClick={() => toggleLocalTool(connection)}
                    >
                      <CheckCircle2 size={12} /> {connection.enabled ? 'Désactiver' : 'Activer'}
                    </button>
                    <button
                      type="button"
                      className="hz-btn hz-btn--ghost"
                      onClick={() => handleRemoveLocalTool(connection)}
                    >
                      <Trash2 size={12} /> Retirer
                    </button>
                  </div>
                </article>
              ))}
              {toolConnections.length === 0 && (
                <p className="hz-card p-6 text-center text-xs text-slate-500">
                  Aucune connexion locale. Choisissez un outil prédéfini ou créez une fiche personnalisée.
                </p>
              )}
            </div>

            <form onSubmit={handleAddLocalTool} className="space-y-2 rounded-lg border border-white/[0.07] bg-black/20 p-4">
              <label className="block">
                <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
                  Outil prédéfini
                </span>
                <select
                  className="hz-select"
                  value={toolPreset}
                  onChange={(event) => applyToolPreset(event.target.value)}
                >
                  {TOOL_PRESETS.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
              </label>
              <input
                className="hz-input"
                placeholder="Nom affiché"
                value={toolName}
                onChange={(event) => setToolName(event.target.value)}
              />
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  className="hz-input"
                  placeholder="Catégorie"
                  value={toolCategory}
                  onChange={(event) => setToolCategory(event.target.value)}
                />
                <input
                  className="hz-input"
                  placeholder="Méthode"
                  value={toolMethod}
                  onChange={(event) => setToolMethod(event.target.value)}
                />
              </div>
              <input
                className="hz-input"
                placeholder="Endpoint (facultatif)"
                value={toolEndpoint}
                onChange={(event) => setToolEndpoint(event.target.value)}
              />
              <div className="relative">
                <ShieldCheck size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  className="hz-input pl-8"
                  placeholder="Nom de la variable de clé (facultatif)"
                  value={toolKeyEnv}
                  onChange={(event) => setToolKeyEnv(event.target.value)}
                />
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  className="hz-input"
                  placeholder="Permissions"
                  value={toolPermissions}
                  onChange={(event) => setToolPermissions(event.target.value)}
                />
                <input
                  className="hz-input"
                  placeholder="Capacités"
                  value={toolCapabilities}
                  onChange={(event) => setToolCapabilities(event.target.value)}
                />
              </div>
              <button
                type="submit"
                className="hz-btn hz-btn--primary w-full justify-center"
                disabled={!toolName.trim()}
              >
                <Plus size={12} /> Enregistrer la fiche
              </button>
              <p className="hz-hint flex items-start gap-1.5">
                <ShieldCheck size={12} className="mt-0.5 shrink-0" />
                Ne saisissez jamais une clé : seulement le nom de la variable qui la contient.
              </p>
            </form>
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
      </div>
    </div>
  );
}