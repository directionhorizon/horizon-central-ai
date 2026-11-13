import { BrainCircuit, CircleCheck, CircleDashed, CircleX, Loader2, PauseCircle } from 'lucide-react';
import type { Mission, StepStatus } from '../api/entities';

/**
 * Représentation de l'activité RÉELLE de HORIZON CORE.
 *
 * Chaque état est déduit d'un fait observé (requête en cours, planification en
 * cours, statut d'exécution renvoyé par le backend, statut de mission). Aucune
 * animation n'est affichée lorsque le système est inactif.
 */
export type CoreActivityState =
  | 'idle'
  | 'analyzing'
  | 'planning'
  | 'executing'
  | 'verifying'
  | 'delivered'
  | 'attention'
  | 'error';

const LABELS: Record<CoreActivityState, string> = {
  idle: 'Inactif — en attente d’une demande',
  analyzing: 'Analyse de la demande',
  planning: 'Planification en cours',
  executing: 'Exécution en cours',
  verifying: 'Vérification des étapes',
  delivered: 'Livraison effectuée',
  attention: 'Intervention nécessaire',
  error: 'Erreur signalée par le moteur',
};

export function deriveCoreState(input: {
  sending: boolean;
  planning: boolean;
  error: string | null;
  executionStatus: string | null;
  mission: Mission | null;
}): CoreActivityState {
  const { sending, planning, error, executionStatus, mission } = input;
  if (planning) return 'planning';
  if (sending) return 'analyzing';
  if (error || executionStatus === 'failed') return 'error';
  if (mission) {
    if (mission.status === 'failed' || mission.status === 'paused') return 'attention';
    if (mission.status === 'running') {
      const steps: StepStatus[] = (mission.steps ?? []).map((step) => step.status);
      if (steps.length > 0 && steps.every((status) => status === 'completed')) return 'verifying';
      return 'executing';
    }
    if (mission.status === 'completed') return 'delivered';
  }
  if (executionStatus === 'completed') return 'delivered';
  return 'idle';
}

const ACTIVE: ReadonlyArray<CoreActivityState> = ['analyzing', 'planning', 'executing', 'verifying'];

export function CoreActivity({ state, detail }: { state: CoreActivityState; detail?: string }) {
  const active = ACTIVE.includes(state);
  const tone =
    state === 'error' || state === 'attention'
      ? 'hz-badge--danger'
      : state === 'delivered'
        ? 'hz-badge--ok'
        : active
          ? 'hz-badge--accent'
          : '';
  return (
    <span className={`hz-badge ${tone}`} title={detail ?? LABELS[state]} aria-live="polite">
      {active ? (
        <Loader2 size={11} className="animate-spin" />
      ) : state === 'delivered' ? (
        <CircleCheck size={11} />
      ) : state === 'error' || state === 'attention' ? (
        <CircleX size={11} />
      ) : (
        <CircleDashed size={11} />
      )}
      HORIZON CORE · {LABELS[state]}
    </span>
  );
}

/** Indicateur discret : n'affiche rien si le moteur est réellement inactif. */
export function CoreActivityDot({ state }: { state: CoreActivityState }) {
  if (!ACTIVE.includes(state)) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-[10px] text-cyan-300">
      <span className="hz-live-dot" aria-hidden="true" />
      <BrainCircuit size={11} />
    </span>
  );
}

/* --- Pipeline de mission : uniquement des états réels --------------------- */

type StageState = 'done' | 'current' | 'pending' | 'failed' | 'paused';

const STAGES = ['Demande', 'Analyse', 'Planification', 'Affectation', 'Exécution', 'Vérification', 'Livraison'] as const;

export function MissionPipeline({ mission }: { mission: Mission | null }) {
  if (!mission) {
    return <p className="hz-hint">Aucune mission active : la pipeline s’affichera dès qu’une mission existe.</p>;
  }

  const steps = mission.steps ?? [];
  const completed = steps.filter((step) => step.status === 'completed').length;
  const total = steps.length;
  const assigned = Boolean(mission.orchestrator_id) || steps.some((step) => step.assigned_orchestrator_id);

  const states: StageState[] = STAGES.map(() => 'pending');
  const setStage = (index: number, value: StageState) => {
    if (index >= 0) states[index] = value;
  };

  setStage(0, 'done');
  if (mission.status !== 'draft') {
    setStage(1, 'done');
    setStage(2, 'done');
  }
  if (assigned) setStage(3, 'done');
  if (mission.status === 'running' || mission.status === 'completed') {
    setStage(3, 'done');
    setStage(4, mission.status === 'completed' ? 'done' : 'current');
  }
  if (mission.status === 'completed') {
    setStage(4, 'done');
    setStage(5, 'done');
    setStage(6, 'done');
  }
  if (total > 0 && completed === total && mission.status !== 'completed') {
    setStage(5, 'current');
  }
  if (mission.status === 'failed') {
    const firstPending = states.findIndex((state) => state !== 'done');
    setStage(firstPending === -1 ? 5 : firstPending, 'failed');
  }
  if (mission.status === 'paused') {
    const current = states.findIndex((state) => state === 'current' || state === 'pending');
    setStage(current === -1 ? 4 : current, 'paused');
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {STAGES.map((stage, index) => {
          const state = states[index];
          const icon =
            state === 'done' ? (
              <CircleCheck size={11} />
            ) : state === 'failed' ? (
              <CircleX size={11} />
            ) : state === 'paused' ? (
              <PauseCircle size={11} />
            ) : state === 'current' ? (
              <Loader2 size={11} className="animate-spin" />
            ) : (
              <CircleDashed size={11} />
            );
          const tone =
            state === 'done'
              ? 'hz-badge--ok'
              : state === 'failed'
                ? 'hz-badge--danger'
                : state === 'paused'
                  ? 'hz-badge--warn'
                  : state === 'current'
                    ? 'hz-badge--accent'
                    : '';
          return (
            <span key={stage} className={`hz-badge ${tone}`} title={`${stage} — ${state}`}>
              {icon}
              {stage}
            </span>
          );
        })}
      </div>
      <p className="hz-hint">
        {mission.title} · statut <strong>{mission.status}</strong>
        {total > 0 ? ` · ${completed}/${total} étape(s) terminée(s)` : ' · aucune étape enregistrée'}
        {mission.orchestrator_id ? ' · orchestrateur affecté' : ' · aucun orchestrateur affecté'}
      </p>
    </div>
  );
}