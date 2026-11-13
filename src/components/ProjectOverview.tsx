import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, FolderKanban, GitBranch, Loader2, Radio } from 'lucide-react';
import { http } from '../api/http';
import { API_ROUTES } from '../config/env';
import type { Mission, ProjectSummary } from '../api/entities';

/**
 * Référence « Systems Overview » : projets, activités et événements RÉELS.
 * Progression = missions terminées / missions existantes. Rien d'inventé.
 */

const STATUS_LABEL: Record<string, string> = {
  active: 'Actif',
  paused: 'Suspendu',
  archived: 'Archivé',
};

export function ProjectOverview() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [projectData, missionData] = await Promise.all([
        http.requestWithRetry<{ items: ProjectSummary[] }>(API_ROUTES.projects),
        http.requestWithRetry<{ items: Mission[] }>(API_ROUTES.missions),
      ]);
      setProjects(projectData.items ?? []);
      setMissions(missionData.items ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Chargement impossible.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  /**
   * Les artefacts de test E2E (noms contenant test / e2e / exemple / démo) ne
   * sont pas des projets métier : ils sont exclus de la vue d'ensemble, qui ne
   * doit montrer que le travail réel. La page Projets les affiche sur demande.
   */
  const realProjects = useMemo(
    () =>
      projects.filter(
        (project) => !/(?:^|[^a-z])(test|e2e|exemple|d[ée]mo)(?:[^a-z]|$)/i.test(project.name),
      ),
    [projects],
  );
  const realProjectIds = useMemo(() => new Set(realProjects.map((project) => project.id)), [realProjects]);
  const realMissions = useMemo(
    () => missions.filter((mission) => realProjectIds.has(mission.project_id)),
    [missions, realProjectIds],
  );

  const byProject = useMemo(() => {
    const index = new Map<string, Mission[]>();
    for (const mission of realMissions) {
      const list = index.get(mission.project_id) ?? [];
      list.push(mission);
      index.set(mission.project_id, list);
    }
    return index;
  }, [realMissions]);

  const running = realMissions.filter((mission) => mission.status === 'running').length;
  const activeProjects = realProjects.filter((project) => project.status === 'active').length;
  const timeline = useMemo(
    () => realMissions.slice().sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)).slice(0, 7),
    [realMissions],
  );

  if (loading) {
    return (
      <section className="hz-panel p-4">
        <p className="hz-hint flex items-center gap-2">
          <Loader2 size={13} className="animate-spin" /> Chargement de la vue d’ensemble…
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      {error && <p className="hz-hint text-amber-200">{error}</p>}

      <div className="so-header">
        <div>
          <p className="hz-eyebrow flex items-center gap-1.5"><Radio size={11} /> Vue d’ensemble</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Projets et activité</h2>
          <p className="hz-hint mt-1">
            {realProjects.length} projet(s) enregistré(s) · {realMissions.length} mission(s) · {running} en cours
          </p>
        </div>
        <div className="so-kpis">
          <div className="so-kpi">
            <FolderKanban size={12} />
            <span className="so-kpi__value">{activeProjects}</span>
            <span className="so-kpi__label">actifs</span>
          </div>
          <div className="so-kpi">
            <GitBranch size={12} />
            <span className="so-kpi__value">{realMissions.length}</span>
            <span className="so-kpi__label">missions</span>
          </div>
          <div className="so-kpi">
            <Activity size={12} />
            <span className="so-kpi__value">{running}</span>
            <span className="so-kpi__label">en cours</span>
          </div>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-3 sm:grid-cols-2">
          {realProjects.map((project) => {
            const list = byProject.get(project.id) ?? [];
            const done = list.filter((mission) => mission.status === 'completed').length;
            const ratio = list.length > 0 ? Math.round((done / list.length) * 100) : 0;
            return (
              <article key={project.id} className="so-card">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-[13px] font-semibold text-slate-100">{project.name}</h3>
                  <span className="hz-badge">{STATUS_LABEL[project.status] ?? project.status}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">
                  {project.description || 'Aucune description enregistrée.'}
                </p>
                <div className="mt-2.5 h-1 overflow-hidden rounded-full bg-white/10">
                  <div className="so-bar" style={{ width: `${ratio}%` }} />
                </div>
                <p className="mt-1.5 flex flex-wrap items-center justify-between gap-1 text-[10px] text-slate-500">
                  <span>{list.length > 0 ? `${done}/${list.length} mission(s) terminée(s)` : 'aucune mission'}</span>
                  <span>{project.orchestrator_count} orchestrateur(s) · maj {new Date(project.updated_at).toLocaleDateString()}</span>
                </p>
              </article>
            );
          })}
          {realProjects.length === 0 && (
            <p className="hz-card p-5 text-center text-xs text-slate-500">Aucun projet enregistré pour le moment.</p>
          )}
        </div>

        <aside className="so-card">
          <p className="hz-eyebrow">Chronologie</p>
          <ol className="mt-2 space-y-2.5">
            {timeline.map((mission) => (
              <li key={mission.id} className="relative pl-4">
                <span className={`so-dot so-dot--${mission.status}`} aria-hidden="true" />
                <p className="line-clamp-1 text-[11px] font-medium text-slate-200">{mission.title}</p>
                <p className="text-[10px] text-slate-500">
                  {mission.status} · {new Date(mission.updated_at).toLocaleString()}
                </p>
              </li>
            ))}
            {timeline.length === 0 && <li className="hz-hint">Aucun événement enregistré.</li>}
          </ol>
        </aside>
      </div>
    </section>
  );
}

export default ProjectOverview;