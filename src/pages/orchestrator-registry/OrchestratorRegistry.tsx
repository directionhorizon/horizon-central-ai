import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, Network, Plus, RefreshCw, Search, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { orchestratorsApi } from '../../api/orchestrators';
import { projectsApi } from '../../api/projects';
import { skillsApi } from '../../api/skills';
import { describeApiError } from '../../api/errors';
import type { Orchestrator, ProjectSummary, SkillSummary } from '../../api/entities';
import { MissionWorkflow } from '../../components/MissionWorkflow';

const healthStyle: Record<string, string> = {
  available: 'bg-emerald-400/10 text-emerald-300',
  degraded: 'bg-amber-400/10 text-amber-300',
  unverified: 'bg-slate-500/10 text-slate-300',
  unavailable: 'bg-rose-400/10 text-rose-300',
};

const statusStyle: Record<string, string> = {
  active: 'bg-cyan-400/10 text-cyan-300',
  inactive: 'bg-amber-400/10 text-amber-300',
  disabled: 'bg-slate-500/10 text-slate-400',
};

const badge = (map: Record<string, string>, value: string) =>
  `rounded-full px-2 py-0.5 text-[10px] font-medium ${map[value] ?? 'bg-white/5 text-slate-300'}`;

/**
 * Libellés lisibles : les valeurs techniques du backend (active, unverified…)
 * ne sont plus affichées telles quelles. L'administrateur lit du français ;
 * la valeur brute reste disponible en infobulle.
 */
const STATUS_LABEL: Record<string, string> = {
  active: 'Actif',
  inactive: 'Inactif',
  disabled: 'Désactivé',
};
const HEALTH_LABEL: Record<string, string> = {
  available: 'Disponible',
  degraded: 'Dégradé',
  unverified: 'Non vérifié',
  unavailable: 'Injoignable',
};
const FILTER_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'All', label: 'Tous les états' },
  { value: 'active', label: 'Actifs' },
  { value: 'inactive', label: 'Inactifs' },
  { value: 'disabled', label: 'Désactivés' },
  { value: 'available', label: 'Disponibles' },
  { value: 'degraded', label: 'Dégradés' },
  { value: 'unverified', label: 'Non vérifiés' },
  { value: 'unavailable', label: 'Injoignables' },
];

export const OrchestratorRegistry = () => {
  const [orchestrators, setOrchestrators] = useState<Orchestrator[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('All');
  const [expanded, setExpanded] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [kind, setKind] = useState('local');
  const [endpoint, setEndpoint] = useState('');
  const [description, setDescription] = useState('');
  const [capability, setCapability] = useState('');
  const [linkTarget, setLinkTarget] = useState<Record<string, string>>({});
  const [allSkills, setAllSkills] = useState<SkillSummary[]>([]);
  const [skillTarget, setSkillTarget] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [list, projectList, skillList] = await Promise.all([
        orchestratorsApi.list(),
        projectsApi.list(),
        skillsApi.list({ status: 'active' }),
      ]);
      setOrchestrators(list.items);
      setProjects(projectList.items);
      setAllSkills(skillList.items);
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

  const visible = useMemo(
    () =>
      orchestrators.filter(
        (item) =>
          (filter === 'All' || item.status === filter || item.health_status === filter) &&
          [item.name, item.kind, item.description, item.endpoint, ...item.capabilities.map((c) => c.capability_id)]
            .join(' ')
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [orchestrators, filter, query],
  );

  const stats = useMemo(
    () => ({
      total: orchestrators.length,
      active: orchestrators.filter((item) => item.status === 'active').length,
      verified: orchestrators.filter((item) => item.health_status === 'available').length,
    }),
    [orchestrators],
  );

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) return;
    void run(
      'create',
      async () => {
        await orchestratorsApi.create({
          name: name.trim(),
          kind: kind.trim() || 'local',
          description: description.trim(),
          endpoint: endpoint.trim(),
          capabilities: capability.trim()
            ? [{ capability_id: capability.trim().toLowerCase(), level: 'standard', detail: '' }]
            : [],
        });
        setName('');
        setEndpoint('');
        setDescription('');
        setCapability('');
      },
      'Orchestrateur enregistré.',
    );
  };

  return (
    <div className="min-h-screen bg-[#0A0B10] text-slate-100">
      <div className="mx-auto min-h-screen w-full max-w-[1500px]">
        <div className="mx-auto max-w-[1500px] px-8 py-8 lg:px-10">
          <header className="mb-8">
            <div className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-400">
              <Network size={14} /> Registre des orchestrateurs
            </div>
            <h1 className="text-4xl font-semibold tracking-[-0.04em] text-white">Orchestrateurs</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Les orchestrateurs enregistrés, leurs capacités déclarées, leurs projets et leur disponibilité
              vérifiée par un appel réel. Aucune donnée de démonstration sur cette page.
            </p>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-500">
              Un orchestrateur exécute des enchaînements de tâches. Les services et applications externes
              (Gmail, Drive, GitHub…) se déclarent dans <span className="text-slate-300">Connexions</span>.
            </p>
          </header>

          <div className="mb-8">
            <MissionWorkflow />
          </div>

          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-400/25 bg-rose-400/[0.07] p-4">
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-300" />
              <p className="text-xs leading-5 text-rose-100">{error}</p>
            </div>
          )}
          {notice && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-cyan-400/25 bg-cyan-400/[0.06] p-4">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-cyan-300" />
              <p className="text-xs leading-5 text-cyan-100">{notice}</p>
            </div>
          )}

          <section className="mb-9 grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
              <Network size={18} className="text-cyan-300" />
              <p className="mt-3 text-2xl font-semibold">{stats.total}</p>
              <p className="mt-1 text-xs text-slate-500">Orchestrateurs enregistrés</p>
            </div>
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
              <ShieldCheck size={18} className="text-cyan-300" />
              <p className="mt-3 text-2xl font-semibold">{stats.active}</p>
              <p className="mt-1 text-xs text-slate-500">Actifs</p>
            </div>
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
              <Wifi size={18} className="text-emerald-300" />
              <p className="mt-3 text-2xl font-semibold">{stats.verified}</p>
              <p className="mt-1 text-xs text-slate-500">Vérifiés disponibles</p>
            </div>
          </section>

          <section className="mb-9 overflow-hidden rounded-xl border border-white/[0.08] bg-[#12151e]/80">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.07] p-5">
              <div>
                <h2 className="text-base font-semibold">Orchestrateurs</h2>
                <p className="mt-1 text-xs text-slate-500">Enregistrer, vérifier, associer, désactiver</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <label className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Rechercher"
                    className="h-9 w-52 rounded-lg border border-white/10 bg-white/[0.04] pl-9 pr-3 text-xs outline-none focus:border-cyan-400/50"
                  />
                </label>
                <select
                  value={filter}
                  onChange={(event) => setFilter(event.target.value)}
                  aria-label="Filtrer par état"
                  className="h-9 rounded-lg border border-white/10 bg-[#171a24] px-3 text-xs text-slate-300"
                >
                  {FILTER_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => void refresh()}
                  className="flex h-9 items-center gap-2 rounded-lg border border-white/10 px-3 text-xs text-slate-300 hover:bg-white/5"
                >
                  <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualiser
                </button>
              </div>
            </div>
            <div className="divide-y divide-white/[0.06]">
              {visible.map((item) => (
                <article key={item.id} className="p-5">
                  <button
                    type="button"
                    onClick={() => setExpanded(expanded === item.id ? '' : item.id)}
                    className="flex w-full flex-wrap items-center gap-4 text-left"
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-cyan-300">
                      {item.health_status === 'available' ? <Wifi size={20} /> : <WifiOff size={20} />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-white">{item.name}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {item.kind} · {item.endpoint || 'aucun endpoint'} · {item.capabilities.length} capacité(s)
                      </p>
                    </div>
                    <span className={badge(statusStyle, item.status)} title={item.status}>
                      {STATUS_LABEL[item.status] ?? item.status}
                    </span>
                    <span className={badge(healthStyle, item.health_status)} title={item.health_status}>
                      {HEALTH_LABEL[item.health_status] ?? item.health_status}
                    </span>
                  </button>
                  {expanded === item.id && (
                    <div className="ml-14 mt-4 space-y-4 rounded-lg bg-black/20 p-4">
                      {item.description && <p className="text-xs leading-5 text-slate-300">{item.description}</p>}
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={busy === item.id}
                          onClick={() =>
                            void run(
                              item.id,
                              async () => {
                                const result = await orchestratorsApi.check(item.id);
                                setNotice(`Vérification ${item.name} : ${result.health_status} — ${result.detail}`);
                              },
                              'Vérification terminée.',
                            )
                          }
                          className="flex items-center gap-2 rounded-md border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-[11px] text-cyan-200 hover:bg-cyan-400/20 disabled:opacity-40"
                        >
                          {busy === item.id ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                          Vérifier la disponibilité
                        </button>
                        <button
                          type="button"
                          disabled={busy === item.id || item.status === 'disabled'}
                          onClick={() =>
                            void run(
                              item.id,
                              async () => {
                                await orchestratorsApi.disable(item.id);
                              },
                              'Orchestrateur désactivé (fiche conservée).',
                            )
                          }
                          className="rounded-md border border-white/10 px-3 py-1.5 text-[11px] text-slate-300 hover:bg-white/5 disabled:opacity-40"
                        >
                          Désactiver
                        </button>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Capacités</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.capabilities.map((cap) => (
                            <span key={cap.id} className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-slate-300">
                              {cap.capability_id}
                            </span>
                          ))}
                          {item.capabilities.length === 0 && (
                            <span className="text-[11px] text-slate-500">Aucune capacité déclarée.</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Projets associés</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.projects.map((project) => (
                            <span key={project.project_id} className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-[10px] text-cyan-200">
                              {project.project_name} · {project.role}
                            </span>
                          ))}
                          {item.projects.length === 0 && (
                            <span className="text-[11px] text-slate-500">Aucun projet associé.</span>
                          )}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <select
                            value={linkTarget[item.id] ?? ''}
                            onChange={(event) =>
                              setLinkTarget((current) => ({ ...current, [item.id]: event.target.value }))
                            }
                            className="h-8 rounded-md border border-white/10 bg-[#171a24] px-2 text-[11px] text-slate-300"
                          >
                            <option value="">Sélectionner un projet…</option>
                            {projects
                              .filter((project) => !item.projects.some((p) => p.project_id === project.id))
                              .map((project) => (
                                <option key={project.id} value={project.id}>
                                  {project.name}
                                </option>
                              ))}
                          </select>
                          <button
                            type="button"
                            disabled={busy === item.id || !linkTarget[item.id]}
                            onClick={() => {
                              const projectId = linkTarget[item.id];
                              if (!projectId) return;
                              void run(
                                item.id,
                                async () => {
                                  await orchestratorsApi.linkProject(item.id, projectId);
                                  setLinkTarget((current) => ({ ...current, [item.id]: '' }));
                                },
                                'Projet associé.',
                              );
                            }}
                            className="rounded-md border border-white/10 px-3 py-1 text-[11px] text-slate-300 hover:bg-white/5 disabled:opacity-40"
                          >
                            Associer
                          </button>
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Compétences</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.skills.map((skill) => (
                            <span
                              key={skill.id}
                              className="inline-flex items-center gap-1 rounded-full bg-violet-400/10 px-2.5 py-1 text-[10px] text-violet-200"
                            >
                              {skill.name}
                              <button
                                type="button"
                                disabled={busy === item.id}
                                onClick={() =>
                                  void run(
                                    item.id,
                                    async () => {
                                      await orchestratorsApi.detachSkill(item.id, skill.id);
                                    },
                                    'Compétence retirée.',
                                  )
                                }
                                className="ml-1 text-violet-300 hover:text-rose-300 disabled:opacity-40"
                                title="Retirer cette compétence"
                              >
                                ×
                              </button>
                            </span>
                          ))}
                          {item.skills.length === 0 && (
                            <span className="text-[11px] text-slate-500">Aucune compétence associée.</span>
                          )}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <select
                            value={skillTarget[item.id] ?? ''}
                            onChange={(event) =>
                              setSkillTarget((current) => ({ ...current, [item.id]: event.target.value }))
                            }
                            className="h-8 rounded-md border border-white/10 bg-[#171a24] px-2 text-[11px] text-slate-300"
                          >
                            <option value="">Sélectionner une compétence…</option>
                            {allSkills
                              .filter((skill) => !item.skills.some((assigned) => assigned.id === skill.id))
                              .map((skill) => (
                                <option key={skill.id} value={skill.id}>
                                  {skill.name} — {skill.category}
                                </option>
                              ))}
                          </select>
                          <button
                            type="button"
                            disabled={busy === item.id || !skillTarget[item.id]}
                            onClick={() =>
                              void run(
                                item.id,
                                async () => {
                                  const target = skillTarget[item.id];
                                  if (!target) return;
                                  await orchestratorsApi.attachSkill(item.id, target);
                                  setSkillTarget((current) => ({ ...current, [item.id]: '' }));
                                },
                                'Compétence associée.',
                              )
                            }
                            className="rounded-md border border-white/10 px-3 py-1 text-[11px] text-slate-300 hover:bg-white/5 disabled:opacity-40"
                          >
                            Associer
                          </button>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-600">Dernière vérification : {item.last_checked_at ?? 'jamais'}</p>
                    </div>
                  )}
                </article>
              ))}
              {visible.length === 0 && (
                <p className="p-10 text-center text-xs text-slate-500">
                  {loading ? 'Chargement…' : 'Aucun orchestrateur ne correspond à ce filtre.'}
                </p>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
            <h2 className="mb-4 flex items-center gap-2 text-base font-semibold">
              <Plus size={16} className="text-cyan-300" /> Enregistrer un orchestrateur
            </h2>
            <form onSubmit={handleCreate} className="grid gap-3 md:grid-cols-2">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Nom (obligatoire)"
                className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <input
                value={kind}
                onChange={(event) => setKind(event.target.value)}
                placeholder="Type (local, cloud, mcp…)"
                className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <input
                value={endpoint}
                onChange={(event) => setEndpoint(event.target.value)}
                placeholder="Endpoint HTTP (optionnel) — ex. http://127.0.0.1:9000"
                className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50 md:col-span-2"
              />
              <input
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Description (optionnelle)"
                className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50 md:col-span-2"
              />
              <input
                value={capability}
                onChange={(event) => setCapability(event.target.value)}
                placeholder="Capacité initiale (ex. code)"
                className="h-9 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <button
                type="submit"
                disabled={busy === 'create' || !name.trim()}
                className="flex h-9 items-center justify-center gap-2 rounded-lg bg-cyan-400/15 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
              >
                {busy === 'create' ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                Enregistrer
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
};