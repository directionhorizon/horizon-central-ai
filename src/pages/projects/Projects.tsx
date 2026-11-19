import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { AlertTriangle, Boxes, CheckCircle2, FolderKanban, ListChecks, Loader2, PlayCircle, Plus, RefreshCw, Sparkles } from 'lucide-react';
import { projectsApi } from '../../api/projects';
import { missionsApi } from '../../api/missions';
import { coreApi } from '../../api/system';
import { describeApiError } from '../../api/errors';
import type { Mission, ProjectDetail, ProjectSummary, StepStatus } from '../../api/entities';
import { ProjectOverview } from '../../components/ProjectOverview';
import { ExecutionView } from '../../components/ExecutionView';

const statusStyle: Record<string, string> = {
  active: 'bg-emerald-400/10 text-emerald-300',
  paused: 'bg-amber-400/10 text-amber-300',
  archived: 'bg-slate-500/10 text-slate-400',
  draft: 'bg-slate-500/10 text-slate-300',
  planned: 'bg-cyan-400/10 text-cyan-300',
  running: 'bg-cyan-400/15 text-cyan-200',
  paused_mission: 'bg-amber-400/10 text-amber-300',
  completed: 'bg-emerald-400/10 text-emerald-300',
  failed: 'bg-rose-400/10 text-rose-300',
  cancelled: 'bg-slate-500/10 text-slate-400',
  pending: 'bg-slate-500/10 text-slate-400',
  skipped: 'bg-slate-500/10 text-slate-500',
};

const badge = (value: string) =>
  `rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle[value] ?? 'bg-white/5 text-slate-300'}`;

const NEXT_STEP_STATUS: Record<StepStatus, StepStatus[]> = {
  pending: ['running', 'skipped'],
  running: ['completed', 'failed'],
  completed: [],
  failed: ['running'],
  skipped: ['pending'],
};

/**
 * Certains enregistrements en base ne sont pas des projets métier : ce sont
 * des artefacts de test E2E créés par les campagnes de vérification. Ils ne
 * sont plus présentés comme des projets : masqués par défaut, signalés comme
 * « données de test » et affichables sur demande explicite.
 */
const isTestArtifact = (project: ProjectSummary) =>
  /(?:^|[^a-z])(test|e2e|exemple|d[ée]mo)(?:[^a-z]|$)/i.test(project.name);

export const Projects = () => {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [showTestArtifacts, setShowTestArtifacts] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [missionTitle, setMissionTitle] = useState('');
  const [planRequest, setPlanRequest] = useState('');
  const [stepDraft, setStepDraft] = useState<Record<string, string>>({});
  const [executionMissionId, setExecutionMissionId] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    const response = await projectsApi.list();
    setProjects(response.items);
    setSelectedId((current) => current ?? response.default_project_id ?? response.items[0]?.id ?? null);
  }, []);

  const loadDetail = useCallback(async (projectId: string) => {
    const [projectDetail, missionList] = await Promise.all([
      projectsApi.get(projectId),
      missionsApi.list({ projectId }),
    ]);
    setDetail(projectDetail);
    setMissions(missionList.items);
  }, []);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      await loadProjects();
      if (selectedId) await loadDetail(selectedId);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, [loadProjects, loadDetail, selectedId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selectedProject = useMemo(
    () => projects.find((item) => item.id === selectedId) ?? null,
    [projects, selectedId],
  );

  /** Liste affichée : les artefacts de test restent masqués sauf demande. */
  const visibleProjects = useMemo(
    () => projects.filter((project) => showTestArtifacts || !isTestArtifact(project)),
    [projects, showTestArtifacts],
  );
  const testArtifactCount = useMemo(
    () => projects.filter(isTestArtifact).length,
    [projects],
  );

  const run = async (action: () => Promise<void>, message: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(message);
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(false);
    }
  };

  const handleCreateProject = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newName.trim()) return;
    void run(async () => {
      const created = await projectsApi.create({ name: newName.trim(), description: newDescription.trim() });
      setNewName('');
      setNewDescription('');
      setSelectedId(created.id);
    }, 'Projet créé.');
  };

  const handleCreateMission = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedId || !missionTitle.trim()) return;
    void run(async () => {
      await missionsApi.create({ project_id: selectedId, title: missionTitle.trim() });
      setMissionTitle('');
    }, 'Mission créée.');
  };

  const handlePlan = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedId || !planRequest.trim()) return;
    void run(async () => {
      const result = await coreApi.plan(selectedId, planRequest.trim());
      setPlanRequest('');
      if (result.status === 'no_model') {
        setNotice(`Planification refusée : ${result.detail ?? 'aucun fournisseur vérifié.'}`);
      }
    }, 'Planification traitée par HORIZON CORE.');
  };

  return (
    <div className="min-h-screen bg-[#0a0b10] text-slate-100">
      <div className="mx-auto w-full max-w-[1500px] px-5 pb-14 pt-8 sm:px-8 lg:px-10">
        <header className="mb-7 border-b border-white/[0.07] pb-6">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-400">
            <FolderKanban size={14} /> Projets &amp; missions
          </div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-white">Project Manager</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Projets réels, missions réelles, persistés en base. Chaque chiffre affiché provient du backend : aucune valeur de démonstration.
          </p>
        </header>

        <div className="mb-6">
          <ProjectOverview />
        </div>

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

        <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
          <section className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">
                Projets ({visibleProjects.length}
                {testArtifactCount > 0 && !showTestArtifacts ? ` + ${testArtifactCount} donnée(s) de test masquée(s)` : ''})
              </h2>
              <button
                type="button"
                onClick={() => void refresh()}
                className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-slate-200"
                aria-label="Rafraîchir"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>
            <div className="space-y-2">
              {visibleProjects.map((project) => (
                <button
                  key={project.id}
                  type="button"
                  onClick={() => setSelectedId(project.id)}
                  className={`w-full rounded-lg border p-3 text-left transition ${
                    selectedId === project.id
                      ? 'border-cyan-400/40 bg-cyan-400/[0.07]'
                      : 'border-white/[0.06] bg-white/[0.02] hover:border-white/15'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-medium text-white">{project.name}</span>
                    <span className={badge(project.status)}>{project.status}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">
                    {project.mission_count} mission(s) · {project.orchestrator_count} orchestrateur(s)
                    {isTestArtifact(project) ? ' · donnée de test' : ''}
                  </p>
                </button>
              ))}
              {visibleProjects.length === 0 && !loading && (
                <p className="p-3 text-xs text-slate-500">
                  Aucun projet métier enregistré.
                  {testArtifactCount > 0 ? ' Seules des données de test existent pour l’instant.' : ''}
                </p>
              )}
            </div>
            {testArtifactCount > 0 && (
              <label className="mt-3 flex items-center gap-2 border-t border-white/[0.07] pt-3 text-[10px] text-slate-500">
                <input
                  type="checkbox"
                  checked={showTestArtifacts}
                  onChange={(event) => setShowTestArtifacts(event.target.checked)}
                  className="h-3 w-3 accent-cyan-400"
                />
                Afficher les {testArtifactCount} enregistrement(s) de test (E2E)
              </label>
            )}

            <form onSubmit={handleCreateProject} className="mt-4 space-y-2 border-t border-white/[0.07] pt-4">
              <input
                value={newName}
                onChange={(event) => setNewName(event.target.value)}
                placeholder="Nom du nouveau projet"
                className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <input
                value={newDescription}
                onChange={(event) => setNewDescription(event.target.value)}
                placeholder="Description (optionnelle)"
                className="h-9 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
              />
              <button
                type="submit"
                disabled={busy || !newName.trim()}
                className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-400/15 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
              >
                {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Créer le projet
              </button>
            </form>
          </section>

          <section className="space-y-5">
            {selectedProject ? (
              <>
                <div className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-white">{selectedProject.name}</h2>
                      <p className="mt-1 text-xs leading-5 text-slate-400">
                        {selectedProject.description || 'Aucune description.'}
                      </p>
                    </div>
                    <span className={badge(selectedProject.status)}>{selectedProject.status}</span>
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                      <span className="block text-[10px] uppercase tracking-wider text-slate-500">Missions</span>
                      <strong className="mt-1 block text-lg text-white">{detail?.missions.length ?? 0}</strong>
                    </div>
                    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                      <span className="block text-[10px] uppercase tracking-wider text-slate-500">Orchestrateurs</span>
                      <strong className="mt-1 block text-lg text-white">{detail?.orchestrators.length ?? 0}</strong>
                    </div>
                    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                      <span className="block text-[10px] uppercase tracking-wider text-slate-500">Identifiant</span>
                      <strong className="mt-1 block truncate text-[11px] text-slate-300">{selectedProject.id}</strong>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
                    <Sparkles size={15} className="text-cyan-300" /> Planifier avec HORIZON CORE
                  </h3>
                  <form onSubmit={handlePlan} className="flex flex-col gap-2 sm:flex-row">
                    <input
                      value={planRequest}
                      onChange={(event) => setPlanRequest(event.target.value)}
                      placeholder="Décrire la demande à transformer en mission"
                      className="h-9 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                    />
                    <button
                      type="submit"
                      disabled={busy || !planRequest.trim()}
                      className="flex h-9 items-center justify-center gap-2 rounded-lg bg-cyan-400/15 px-4 text-xs font-medium text-cyan-200 hover:bg-cyan-400/25 disabled:opacity-40"
                    >
                      {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Planifier
                    </button>
                  </form>
                  <p className="mt-2 text-[10px] leading-4 text-slate-500">
                    Sans fournisseur LLM vérifié, HORIZON CORE refuse explicitement la planification : aucune mission n'est créée.
                  </p>
                </div>

                <div className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
                    <ListChecks size={15} className="text-cyan-300" /> Missions ({missions.length})
                  </h3>
                  <form onSubmit={handleCreateMission} className="mb-4 flex flex-col gap-2 sm:flex-row">
                    <input
                      value={missionTitle}
                      onChange={(event) => setMissionTitle(event.target.value)}
                      placeholder="Titre de la mission"
                      className="h-9 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs outline-none focus:border-cyan-400/50"
                    />
                    <button
                      type="submit"
                      disabled={busy || !missionTitle.trim()}
                      className="flex h-9 items-center justify-center gap-2 rounded-lg bg-white/5 px-4 text-xs font-medium text-slate-200 hover:bg-white/10 disabled:opacity-40"
                    >
                      <Plus size={14} /> Ajouter
                    </button>
                  </form>
                  <div className="space-y-3">
                    {missions.map((mission) => (
                      <article key={mission.id} className="rounded-lg border border-white/[0.07] bg-black/20 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs font-medium text-white">{mission.title}</span>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => setExecutionMissionId(mission.id)}
                              className="inline-flex items-center gap-1 rounded border border-cyan-400/30 px-2 py-0.5 text-[10px] text-cyan-200 hover:bg-cyan-400/10"
                            >
                              <PlayCircle size={11} /> Exécuter
                            </button>
                            <span className={badge(mission.priority)}>{mission.priority}</span>
                            <span className={badge(mission.status)}>{mission.status}</span>
                          </div>
                        </div>
                        {mission.description && (
                          <p className="mt-1 text-[10px] leading-4 text-slate-500">{mission.description}</p>
                        )}
                        <ul className="mt-2 space-y-1">
                          {(mission.steps ?? []).map((step) => (
                            <li key={step.id} className="flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
                              <span className="w-4 text-slate-600">{step.position + 1}</span>
                              <span className="flex-1 truncate">{step.title}</span>
                              <span className={badge(step.status)}>{step.status}</span>
                              {NEXT_STEP_STATUS[step.status].map((next) => (
                                <button
                                  key={next}
                                  type="button"
                                  disabled={busy}
                                  onClick={() =>
                                    void run(
                                      async () => {
                                        await missionsApi.updateStep(mission.id, step.id, { status: next });
                                      },
                                      `Étape « ${step.title} » → ${next}.`,
                                    )
                                  }
                                  className="rounded border border-white/10 px-1.5 py-0.5 text-[9px] text-slate-300 hover:border-cyan-400/40 hover:text-cyan-200 disabled:opacity-40"
                                >
                                  {next}
                                </button>
                              ))}
                            </li>
                          ))}
                        </ul>
                        <form
                          onSubmit={(event) => {
                            event.preventDefault();
                            const title = (stepDraft[mission.id] ?? '').trim();
                            if (!title) return;
                            void run(async () => {
                              await missionsApi.addStep(mission.id, title);
                              setStepDraft((current) => ({ ...current, [mission.id]: '' }));
                            }, 'Étape ajoutée.');
                          }}
                          className="mt-2 flex gap-2"
                        >
                          <input
                            value={stepDraft[mission.id] ?? ''}
                            onChange={(event) =>
                              setStepDraft((current) => ({ ...current, [mission.id]: event.target.value }))
                            }
                            placeholder="Nouvelle étape"
                            className="h-7 flex-1 rounded border border-white/10 bg-white/[0.03] px-2 text-[10px] outline-none focus:border-cyan-400/40"
                          />
                          <button type="submit" className="rounded border border-white/10 px-2 text-[10px] text-slate-300 hover:bg-white/5">
                            +
                          </button>
                        </form>
                      </article>
                    ))}
                    {missions.length === 0 && <p className="text-xs text-slate-500">Aucune mission pour ce projet.</p>}
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-5">
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-white">
                    <Boxes size={15} className="text-cyan-300" /> Orchestrateurs associés
                  </h3>
                  {detail && detail.orchestrators.length > 0 ? (
                    <ul className="space-y-2">
                      {detail.orchestrators.map((item) => (
                        <li key={item.id} className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                          <span className="flex-1 truncate">{item.name}</span>
                          <span className={badge(item.status)}>{item.status}</span>
                          <span className={badge(item.health_status)}>{item.health_status}</span>
                          <span className="text-[10px] text-slate-600">{item.role}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500">
                      Aucun orchestrateur associé. Enregistrez-en un dans la page Orchestrateurs.
                    </p>
                  )}
                </div>

                {executionMissionId && (
                  <ExecutionView
                    missionId={executionMissionId}
                    missionTitle={missions.find((item) => item.id === executionMissionId)?.title ?? 'Mission'}
                  />
                )}
              </>
            ) : (
              <div className="rounded-xl border border-white/[0.08] bg-[#12151e]/80 p-8 text-center text-xs text-slate-500">
                {loading ? 'Chargement des projets…' : 'Sélectionnez ou créez un projet.'}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};
