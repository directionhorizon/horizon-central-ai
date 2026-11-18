import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, CheckCircle2, Cpu, KeyRound, Loader2, Plus, RefreshCw, Server, Trash2 } from 'lucide-react';
import { modelsApi } from '../../api/models';
import { describeApiError } from '../../api/errors';
import type { LlmProvider, ModelSelection } from '../../api/entities';
import { useConnections, type LlmConnection } from '../../shared/ConnectionsContext';

type LlmPreset = {
  id: string;
  name: string;
  baseUrl: string;
  keyEnv: string;
  model: string;
};

const LLM_PRESETS: LlmPreset[] = [
  { id: 'hermes', name: 'Hermes local', baseUrl: 'http://127.0.0.1:8642/v1', keyEnv: 'HERMES_API_SERVER_KEY', model: 'hermes-agent' },
  { id: 'lmstudio', name: 'LM Studio', baseUrl: 'http://127.0.0.1:1234/v1', keyEnv: '', model: '' },
  { id: 'ollama', name: 'Ollama', baseUrl: 'http://127.0.0.1:11434/v1', keyEnv: '', model: '' },
  { id: 'openai', name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', keyEnv: 'OPENAI_API_KEY', model: 'gpt-4o-mini' },
  { id: 'openrouter', name: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', keyEnv: 'OPENROUTER_API_KEY', model: '' },
  { id: 'custom', name: 'Personnalisé', baseUrl: '', keyEnv: '', model: '' },
];

const statusStyle: Record<string, string> = {
  available: 'bg-emerald-400/10 text-emerald-300',
  unverified: 'bg-amber-400/10 text-amber-300',
  unavailable: 'bg-rose-400/10 text-rose-300',
  unconfigured: 'bg-slate-500/10 text-slate-300',
};

const badge = (value: string) =>
  `rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle[value] ?? 'bg-white/5 text-slate-300'}`;

export const ModelManagerLive = () => {
  const [providers, setProviders] = useState<LlmProvider[]>([]);
  /** Sélection réellement enregistrée côté moteur (source de vérité). */
  const [selection, setSelection] = useState<ModelSelection>({ mode: 'auto', provider_id: null, model: null });
  /** Brouillon édité dans le formulaire : rien n'est envoyé tant qu'on ne valide pas. */
  const [draft, setDraft] = useState<ModelSelection>({ mode: 'auto', provider_id: null, model: null });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [keyEnv, setKeyEnv] = useState('');
  const [defaultModel, setDefaultModel] = useState('');

  const { llmConnections, addLlmConnection, updateLlmConnection, removeLlmConnection } = useConnections();
  const [localPreset, setLocalPreset] = useState(LLM_PRESETS[0].id);
  const [localName, setLocalName] = useState(LLM_PRESETS[0].name);
  const [localBaseUrl, setLocalBaseUrl] = useState(LLM_PRESETS[0].baseUrl);
  const [localKeyEnv, setLocalKeyEnv] = useState(LLM_PRESETS[0].keyEnv);
  const [localModel, setLocalModel] = useState(LLM_PRESETS[0].model);
  const [localNotice, setLocalNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const response = await modelsApi.list();
      setProviders(response.items);
      setSelection(response.selection);
      setDraft(response.selection);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const run = async (key: string, action: () => Promise<void>, message: string) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(message);
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !baseUrl.trim()) return;
    void run(
      'create',
      async () => {
        await modelsApi.create({
          name: name.trim(),
          base_url: baseUrl.trim(),
          api_key_env: keyEnv.trim(),
          default_model: defaultModel.trim(),
        });
        setName('');
        setBaseUrl('');
        setKeyEnv('');
        setDefaultModel('');
      },
      'Fournisseur enregistré. Lancez un test de connexion pour le vérifier.',
    );
  };

  const handleTest = (provider: LlmProvider) =>
    void run(
      provider.id,
      async () => {
        const result = await modelsApi.test(provider.id);
        setNotice(`Test ${provider.name} : ${result.status} — ${result.detail}`);
      },
      'Test de connexion terminé.',
    );

  /**
   * La sélection n'est plus enregistrée automatiquement au moindre clic
   * (ancien `onBlur`) : c'est ce qui faisait apparaître « Sélection de modèle
   * enregistrée » alors que rien n'avait été choisi. On enregistre uniquement
   * sur action explicite, et on n'affiche le message que si la valeur diffère
   * réellement de celle déjà en base.
   */
  const selectionChanged =
    draft.mode !== selection.mode ||
    (draft.provider_id ?? '') !== (selection.provider_id ?? '') ||
    (draft.model ?? '') !== (selection.model ?? '');

  const describeSelection = (value: ModelSelection) => {
    const provider = providers.find((item) => item.id === value.provider_id);
    const mode = value.mode === 'manual' ? 'manuel' : 'automatique';
    if (value.mode === 'auto' && !provider) return `mode ${mode} (premier fournisseur vérifié)`;
    return `mode ${mode}${provider ? ` · ${provider.name}` : ''}${value.model ? ` · ${value.model}` : ''}`;
  };

  const handleSaveSelection = () => {
    if (!selectionChanged) {
      setNotice('Aucune modification : la sélection par défaut est inchangée.');
      return;
    }
    void run(
      'selection',
      async () => {
        const saved = await modelsApi.setSelection(draft);
        setSelection(saved);
        setDraft(saved);
      },
      `Sélection par défaut enregistrée (${describeSelection(draft)}).`,
    );
  };

  const applyLlmPreset = (presetId: string) => {
    setLocalPreset(presetId);
    const preset = LLM_PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    setLocalName(preset.name);
    setLocalBaseUrl(preset.baseUrl);
    setLocalKeyEnv(preset.keyEnv);
    setLocalModel(preset.model);
  };

  const handleAddLocalLlm = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanName = localName.trim();
    const cleanBaseUrl = localBaseUrl.trim();
    if (!cleanName || !cleanBaseUrl) return;
    addLlmConnection({
      name: cleanName,
      baseUrl: cleanBaseUrl,
      keyEnv: localKeyEnv.trim(),
      model: localModel.trim(),
      enabled: true,
    });
    setLocalNotice(`Connexion « ${cleanName} » enregistrée dans le navigateur.`);
    setLocalPreset('custom');
    setLocalName('');
    setLocalBaseUrl('');
    setLocalKeyEnv('');
    setLocalModel('');
  };

  const toggleLocalLlm = (connection: LlmConnection) => {
    updateLlmConnection(connection.id, { enabled: !connection.enabled });
    setLocalNotice(
      `Connexion « ${connection.name} » ${connection.enabled ? 'désactivée' : 'activée'} dans l’interface.`,
    );
  };

  const handleRemoveLocalLlm = (connection: LlmConnection) => {
    removeLlmConnection(connection.id);
    setLocalNotice(`Connexion « ${connection.name} » retirée de l’interface.`);
  };

  const availableProviders = providers.filter((provider) => provider.status === 'available');

  return (
    <div className="min-h-screen bg-[#0a0b10] text-slate-100">
      <main className="mx-auto min-h-screen w-full max-w-[1500px] px-5 pb-12 pt-8 sm:px-8 lg:px-10">
        <header className="mb-7 border-b border-white/[0.07] pb-6">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-400">
            <Cpu size={14} /> Gestionnaire de modèles
          </div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-white">Gestionnaire de modèles</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Fournisseurs LLM réels, vérifiés par un appel réseau. Les clés ne sont jamais stockées en base ni renvoyées au navigateur :
            seule la variable d'environnement qui les contient est référencée.
          </p>
        </header>

        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-400/25 bg-rose-400/[0.07] p-4">
            <AlertTriangle size={17} className="mt-0.5 shrink-0 text-rose-300" />
            <p className="text-xs leading-5 text-rose-100">{error}</p>
          </div>
        )}
        {notice && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-cyan-400/25 bg-cyan-400/[0.06] p-4">
            <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-cyan-300" />
            <p className="text-xs leading-5 text-cyan-100">{notice}</p>
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
          <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Fournisseurs ({providers.length})</h2>
                <p className="mt-1 text-xs text-slate-500">{availableProviders.length} vérifié(s) disponible(s)</p>
              </div>
              <button
                type="button"
                onClick={() => void refresh()}
                className="flex h-8 items-center gap-2 rounded-lg border border-white/10 px-3 text-[11px] text-slate-300 hover:bg-white/5"
              >
                <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Actualiser
              </button>
            </div>
            <div className="space-y-3">
              {providers.map((provider) => (
                <article key={provider.id} className="rounded-lg border border-white/[0.07] bg-black/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white">{provider.name}</p>
                      <p className="mt-1 truncate text-[11px] text-slate-500">{provider.base_url}</p>
                      <p className="mt-1 text-[10px] text-slate-600">
                        Modèle : {provider.default_model || 'non défini'} · Type : {provider.kind}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={badge(provider.status)}>{provider.status}</span>
                      <span className="text-[10px] text-slate-600">
                        {provider.api_key_configured ? 'clé détectée côté serveur' : 'clé absente'}
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy === provider.id}
                      onClick={() => handleTest(provider)}
                      className="flex items-center gap-2 rounded-md border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-[11px] text-cyan-200 hover:bg-cyan-400/20 disabled:opacity-40"
                    >
                      {busy === provider.id ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                      Tester la connexion
                    </button>
                    <button
                      type="button"
                      disabled={busy === provider.id}
                      onClick={() =>
                        void run(
                          provider.id,
                          async () => {
                            await modelsApi.remove(provider.id);
                          },
                          'Fournisseur supprimé.',
                        )
                      }
                      className="flex items-center gap-2 rounded-md border border-white/10 px-3 py-1.5 text-[11px] text-slate-300 hover:bg-white/5 disabled:opacity-40"
                    >
                      <Trash2 size={13} /> Supprimer
                    </button>
                  </div>
                  {provider.last_checked_at && (
                    <p className="mt-2 text-[10px] text-slate-600">
                      Dernier test : {provider.last_checked_at} · {provider.last_error || 'aucune erreur'}
                    </p>
                  )}
                </article>
              ))}
              {providers.length === 0 && !loading && (
                <p className="p-6 text-center text-xs text-slate-500">
                  Aucun fournisseur enregistré. Ajoutez-en un pour activer les réponses IA.
                </p>
              )}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
              <h2 className="mb-1 text-base font-semibold text-white">Sélection par défaut</h2>
              <p className="mb-3 text-[11px] leading-5 text-slate-500">
                Utilisée par HORIZON CORE quand aucun modèle n'est défini pour un orchestrateur. Rien n'est
                enregistré tant que vous ne cliquez pas sur « Enregistrer ».
              </p>
              <div className="space-y-2">
                <label className="block">
                  <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
                    Mode de sélection
                  </span>
                  <select
                    value={draft.mode}
                    onChange={(event) => setDraft({ ...draft, mode: event.target.value as 'auto' | 'manual' })}
                    className="h-9 w-full rounded-lg border border-white/10 bg-[#171a24] px-3 text-xs text-slate-300"
                  >
                    <option value="auto">Automatique (premier fournisseur vérifié)</option>
                    <option value="manual">Manuel (fournisseur imposé)</option>
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
                    Fournisseur imposé
                  </span>
                  <select
                    value={draft.provider_id ?? ''}
                    onChange={(event) => {
                      const provider = providers.find((item) => item.id === event.target.value);
                      setDraft({
                        ...draft,
                        provider_id: event.target.value || null,
                        model: provider?.default_model || draft.model,
                      });
                    }}
                    className="h-9 w-full rounded-lg border border-white/10 bg-[#171a24] px-3 text-xs text-slate-300"
                  >
                    <option value="">Aucun — le mode automatique choisit</option>
                    {providers.map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} ({provider.status})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
                    Modèle imposé
                  </span>
                  <input
                    value={draft.model ?? ''}
                    onChange={(event) => setDraft({ ...draft, model: event.target.value })}
                    placeholder="Ex. gpt-4o-mini"
                    className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                  />
                </label>
                <button
                  type="button"
                  onClick={handleSaveSelection}
                  disabled={busy === 'selection'}
                  className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-400/15 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
                >
                  {busy === 'selection' ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                  Enregistrer la sélection
                </button>
                <p className="text-[10px] leading-4 text-slate-600">
                  Actuellement enregistré :{' '}
                  <span className="text-slate-300">{describeSelection(selection)}</span>
                  {selectionChanged ? ' — modification non enregistrée.' : ''}
                </p>
              </div>
            </section>

            <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
              <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
                <Plus size={15} className="text-cyan-300" /> Ajouter un fournisseur
              </h2>
              <form onSubmit={handleCreate} className="space-y-2">
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Nom (ex. OpenRouter)"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                />
                <input
                  value={baseUrl}
                  onChange={(event) => setBaseUrl(event.target.value)}
                  placeholder="URL de base OpenAI-compatible"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                />
                <div className="relative">
                  <KeyRound size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    value={keyEnv}
                    onChange={(event) => setKeyEnv(event.target.value)}
                    placeholder="Variable d'environnement de la clé"
                    className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-8 pr-3 text-xs outline-none focus:border-cyan-400/50"
                  />
                </div>
                <input
                  value={defaultModel}
                  onChange={(event) => setDefaultModel(event.target.value)}
                  placeholder="Modèle par défaut"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                />
                <button
                  type="submit"
                  disabled={busy === 'create' || !name.trim() || !baseUrl.trim()}
                  className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-400/15 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
                >
                  {busy === 'create' ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  Enregistrer
                </button>
              </form>
              <p className="mt-3 flex items-start gap-2 text-[10px] leading-4 text-slate-600">
                <Server size={12} className="mt-0.5 shrink-0" />
                La clé reste dans backend/.env sous le nom indiqué. Elle n'est jamais écrite en base ni transmise au frontend.
              </p>
            </section>
          </aside>
        </div>

        <section className="mt-6 rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-white/[0.07] pb-4">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-400">
                <Server size={14} /> Connexions interface
              </div>
              <h2 className="text-lg font-semibold text-white">Connexions LLM déclarées ici</h2>
              <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
                Fiches conservées dans ce navigateur, distinctes des fournisseurs vérifiés par le moteur. Aucun appel réseau,
                aucun test et aucune clé ne sont effectués ou stockés ici : indiquez seulement un nom de variable d’environnement.
              </p>
            </div>
            <span className="rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 text-[10px] text-cyan-200">
              {llmConnections.length} fiche(s)
            </span>
          </div>

          {localNotice && (
            <div className="mb-4 flex items-start gap-3 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.05] p-3">
              <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-cyan-300" />
              <p className="text-xs leading-5 text-cyan-100">{localNotice}</p>
            </div>
          )}

          <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
            <div className="space-y-3">
              {llmConnections.map((connection) => (
                <article key={connection.id} className="rounded-lg border border-white/[0.07] bg-black/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white">{connection.name}</p>
                      <p className="mt-1 truncate text-[11px] text-slate-500">{connection.baseUrl}</p>
                      <p className="mt-1 text-[10px] text-slate-600">
                        Modèle : {connection.model || 'non défini'} · Variable : {connection.keyEnv || 'aucune'}
                      </p>
                    </div>
                    <span
                      className={
                        connection.enabled
                          ? 'rounded-full bg-emerald-400/10 px-2 py-0.5 text-[10px] text-emerald-300'
                          : 'rounded-full bg-slate-500/10 px-2 py-0.5 text-[10px] text-slate-300'
                      }
                    >
                      {connection.enabled ? 'active dans l’interface' : 'désactivée'}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => toggleLocalLlm(connection)}
                      className="flex items-center gap-2 rounded-md border border-white/10 px-3 py-1.5 text-[11px] text-slate-300 hover:bg-white/5"
                    >
                      <CheckCircle2 size={13} /> {connection.enabled ? 'Désactiver' : 'Activer'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveLocalLlm(connection)}
                      className="flex items-center gap-2 rounded-md border border-white/10 px-3 py-1.5 text-[11px] text-slate-300 hover:bg-white/5"
                    >
                      <Trash2 size={13} /> Retirer
                    </button>
                  </div>
                </article>
              ))}
              {llmConnections.length === 0 && (
                <p className="rounded-lg border border-dashed border-white/10 p-6 text-center text-xs text-slate-500">
                  Aucune connexion locale. Choisissez un modèle prédéfini ou saisissez une URL personnalisée.
                </p>
              )}
            </div>

            <form onSubmit={handleAddLocalLlm} className="space-y-2 rounded-lg border border-white/[0.07] bg-black/20 p-4">
              <label className="block">
                <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
                  Modèle prédéfini
                </span>
                <select
                  value={localPreset}
                  onChange={(event) => applyLlmPreset(event.target.value)}
                  className="h-9 w-full rounded-lg border border-white/10 bg-[#171a24] px-3 text-xs text-slate-300"
                >
                  {LLM_PRESETS.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
              </label>
              <input
                value={localName}
                onChange={(event) => setLocalName(event.target.value)}
                placeholder="Nom affiché"
                className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <input
                value={localBaseUrl}
                onChange={(event) => setLocalBaseUrl(event.target.value)}
                placeholder="URL de base (http://127.0.0.1:…/v1)"
                className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <div className="relative">
                <KeyRound size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  value={localKeyEnv}
                  onChange={(event) => setLocalKeyEnv(event.target.value)}
                  placeholder="Nom de la variable de clé (facultatif)"
                  className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-8 pr-3 text-xs outline-none focus:border-cyan-400/50"
                />
              </div>
              <input
                value={localModel}
                onChange={(event) => setLocalModel(event.target.value)}
                placeholder="Modèle par défaut (facultatif)"
                className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <button
                type="submit"
                disabled={!localName.trim() || !localBaseUrl.trim()}
                className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-400/15 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
              >
                <Plus size={14} /> Enregistrer la fiche
              </button>
              <p className="flex items-start gap-2 text-[10px] leading-4 text-slate-600">
                <Server size={12} className="mt-0.5 shrink-0" />
                Ne saisissez jamais une clé : seulement le nom de la variable qui la contient.
              </p>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
};
