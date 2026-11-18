import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, ArrowRight, CheckCircle2, CircleDashed, CircleX, GitBranch, Loader2,
  PauseCircle, PlayCircle, Settings2,
} from 'lucide-react';
import { http } from '../api/http';
import { API_ROUTES } from '../config/env';
import type { Mission, MissionStep, Orchestrator, StepStatus } from '../api/entities';
import { ExecutionView } from './ExecutionView';

/** Référence « Workflow Builder » : étapes RÉELLES d'une mission (aucun bloc inventé). */

const STEP_TONE: Record<StepStatus, string> = {
  pending: 'wf-node',
  running: 'wf-node wf-node--running',
  completed: 'wf-node wf-node--done',
  failed: 'wf-node wf-node--failed',
  skipped: 'wf-node wf-node--skipped',
};

function StepIcon({ status, size = 12 }: { status: StepStatus; size?: number }) {
  if (status === 'running') return <Loader2 size={size} className="animate-spin" />;
  if (status === 'completed') return <CheckCircle2 size={size} />;
  if (status === 'failed') return <CircleX size={size} />;
  if (status === 'skipped') return <PauseCircle size={size} />;
  return <CircleDashed size={size} />;
}

export function MissionWorkflow() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [orchestrators, setOrchestrators] = useState<Orchestrator[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [missionData, orchestratorData] = await Promise.all([
        http.requestWithRetry<{ items: Mission[] }>(API_ROUTES.missions),
        http.requestWithRetry<{ items: Orchestrator[] }>(API_ROUTES.orchestrators),
      ]);
      setMissions(missionData.items ?? []);
      setOrchestrators(orchestratorData.items ?? []);
      setSelectedId((current) => current ?? missionData.items?.[0]?.id ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Chargement impossible.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let alive = true;
    setLoadingDetail(true);
    void (async () => {
      try {
        const mission = await http.requestWithRetry<Mission>(API_ROUTES.mission(selectedId));
        if (alive) setDetail(mission);
      } catch (caught) {
        if (alive) setError(caught instanceof Error ? caught.message : 'Détail indisponible.');
      } finally {
        if (alive) setLoadingDetail(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [selectedId]);

  const orchestratorName = useMemo(() => {
    const index = new Map(orchestrators.map((item) => [item.id, item.name]));
    return (id: string | null) => (id ? index.get(id) ?? 'orchestrateur inconnu' : 'non affecté');
  }, [orchestrators]);

  const steps = (detail?.steps ?? []).slice().sort((a, b) => a.position - b.position);
  const completed = steps.filter((step) => step.status === 'completed').length;

  if (loading) {
    return (
      <section className="hz-panel p-4">
        <p className="hz-hint flex items-center gap-2">
          <Loader2 size={13} className="animate-spin" /> Chargement des missions…
        </p>
      </section>
    );
  }

  return (
    <section className="hz-panel p-0">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
        <div>
          <p className="hz-eyebrow">Orchestration</p>
          <h2 className="mt-0.5 flex items-center gap-2 text-sm font-semibold text-slate-100">
            <GitBranch size={14} className="text-cyan-300" /> Distribution des missions
          </h2>
        </div>
        <p className="hz-hint">Étapes réelles · aucune étape simulée</p>
      </div>

      {error && <p className="hz-hint px-4 pt-3 text-amber-200">{error}</p>}

      {missions.length === 0 ? (
        <p className="hz-hint px-4 py-6">
          Aucune mission enregistrée : le workflow s’affichera dès qu’une mission existera.
        </p>
      ) : (
        <div className="grid gap-0 lg:grid-cols-[210px_minmax(0,1fr)_250px]">
          <ul className="divide-y divide-white/5 border-b border-white/10 lg:border-b-0 lg:border-r">
            {missions.map((mission) => (
              <li key={mission.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(mission.id)}
                  className={`flex w-full flex-col gap-1 px-3 py-2.5 text-left transition ${
                    selectedId === mission.id ? 'bg-cyan-400/10 text-cyan-100' : 'text-slate-300 hover:bg-white/5'
                  }`}
                >
                  <span className="line-clamp-2 text-[12px] font-medium">{mission.title}</span>
                  <span className="text-[10px] uppercase tracking-[.12em] text-slate-500">{mission.status}</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="min-w-0 p-3">
            {loadingDetail ? (
              <p className="hz-hint flex items-center gap-2">
                <Loader2 size={12} className="animate-spin" /> Chargement du workflow…
              </p>
            ) : steps.length === 0 ? (
              <p className="hz-hint">
                Cette mission n’a pas encore d’étape enregistrée : HORIZON CORE n’a rien distribué.
              </p>
            ) : (
              <div className="wf-canvas">
                <div className="wf-start">
                  <span className="wf-start__label">HORIZON CORE</span>
                  <span className="wf-start__meta">{orchestratorName(detail?.orchestrator_id ?? null)}</span>
                </div>
                {steps.map((step: MissionStep) => (
                  <div key={step.id} className="wf-chain">
                    <span className="wf-link" aria-hidden="true" />
                    <div className={STEP_TONE[step.status]}>
                      <span className="wf-node__pos">{step.position}</span>
                      <span className="wf-node__icon"><StepIcon status={step.status} /></span>
                      <span className="wf-node__title">{step.title}</span>
                      <span className="wf-node__meta">{orchestratorName(step.assigned_orchestrator_id)}</span>
                    </div>
                  </div>
                ))}
                <span className="wf-link" aria-hidden="true" />
                <div className="wf-start wf-start--end">
                  <span className="wf-start__label">{detail?.status ?? '—'}</span>
                  <span className="wf-start__meta">{completed}/{steps.length} étape(s)</span>
                </div>
              </div>
            )}
          </div>
          <aside className="border-t border-white/10 p-3 lg:border-t-0 lg:border-l">
            <p className="hz-eyebrow flex items-center gap-1.5"><Settings2 size={11} /> Configuration</p>
            {detail ? (
              <dl className="mt-2 space-y-1.5 text-[11px]">
                <div className="flex justify-between gap-2"><dt className="text-slate-500">Statut</dt><dd className="text-slate-200">{detail.status}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-slate-500">Priorité</dt><dd className="text-slate-200">{detail.priority}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-slate-500">Orchestrateur</dt><dd className="truncate text-slate-200">{orchestratorName(detail.orchestrator_id)}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-slate-500">Étapes</dt><dd className="text-slate-200">{completed}/{steps.length}</dd></div>
                {detail.checkpoint_count !== undefined && (
                  <div className="flex justify-between gap-2"><dt className="text-slate-500">Points de contrôle</dt><dd className="text-slate-200">{detail.checkpoint_count}</dd></div>
                )}
                <div className="flex justify-between gap-2"><dt className="text-slate-500">Mise à jour</dt><dd className="text-slate-300">{new Date(detail.updated_at).toLocaleString()}</dd></div>
              </dl>
            ) : (
              <p className="hz-hint mt-2">Sélectionnez une mission.</p>
            )}
            {detail?.status === 'paused' && (
              <p className="hz-hint mt-2 flex items-center gap-1.5 text-amber-200"><PauseCircle size={11} /> Mission suspendue : reprise manuelle requise.</p>
            )}
            {detail?.status === 'failed' && (
              <p className="hz-hint mt-2 flex items-center gap-1.5 text-rose-200"><AlertTriangle size={11} /> Échec enregistré : intervention nécessaire.</p>
            )}
            {detail?.status === 'running' && (
              <p className="hz-hint mt-2 flex items-center gap-1.5 text-cyan-200"><PlayCircle size={11} /> Exécution en cours.</p>
            )}
            {detail?.status === 'completed' && (
              <p className="hz-hint mt-2 flex items-center gap-1.5 text-emerald-200"><CheckCircle2 size={11} /> Mission livrée.</p>
            )}
            <p className="hz-hint mt-3 flex items-center gap-1"><ArrowRight size={10} /> Blocs = étapes réellement enregistrées.</p>
          </aside>
        </div>
      )}

      {detail && (
        <div className="border-t border-white/10 p-3">
          <ExecutionView
            missionId={detail.id}
            missionTitle={detail.title}
            stepId={steps.find((step) => step.status === 'running')?.id ?? null}
            stepTitle={steps.find((step) => step.status === 'running')?.title ?? null}
          />
        </div>
      )}
    </section>
  );
}

export default MissionWorkflow;