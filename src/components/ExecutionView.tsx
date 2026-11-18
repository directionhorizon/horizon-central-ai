import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle, Bot, CheckCircle2, CircleX, Clock3, Coins, Loader2, PlayCircle,
  Square, WandSparkles, Zap,
} from 'lucide-react';
import { missionsApi } from '../api/missions';
import type { OrchestratorRun, PendingControl } from '../api/entities';

/**
 * Vue d'exécution CORE ↔ Hermes (contrat v1.0 §13).
 * Aucun secret, aucun aperçu brut d'outil : uniquement des références et le livrable final.
 */

const ACTIVE = new Set(['queued', 'started', 'running', 'waiting_for_approval', 'stopping', 'dispatching', 'unknown']);
const POLL_MIN_MS = 2000;
const POLL_MAX_MS = 10000;

function pendingControls(run: OrchestratorRun | null): PendingControl[] {
  const list = run?.raw_status?.pending_controls ?? [];
  return list
    .map((item) => ({
      request_id: String(item.request_id ?? item.prompt_id ?? ''),
      execution_generation: Number(item.execution_generation ?? 0),
      kind: item.kind ?? item.type,
    }))
    .filter((item) => item.request_id.length > 0);
}

function elapsed(run: OrchestratorRun | null): string {
  if (!run) return '—';
  const start = new Date(run.started_at ?? run.requested_at).getTime();
  const end = run.finished_at ? new Date(run.finished_at).getTime() : Date.now();
  const seconds = Math.max(0, Math.floor((end - start) / 1000));
  const minutes = Math.floor(seconds / 60);
  return minutes > 0 ? `${minutes} min ${seconds % 60} s` : `${seconds} s`;
}

function StatusBadge({ status }: { status: string }) {
  const tone = ACTIVE.has(status)
    ? 'bg-cyan-400/10 text-cyan-200 border-cyan-400/25'
    : status === 'completed'
      ? 'bg-emerald-400/10 text-emerald-200 border-emerald-400/25'
      : 'bg-slate-400/10 text-slate-300 border-slate-400/20';
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${tone}`}>
      {status}
    </span>
  );
}

export interface ExecutionViewProps {
  missionId: string;
  missionTitle: string;
  stepId?: string | null;
  stepTitle?: string | null;
  disabled?: boolean;
}

export function ExecutionView({
  missionId, missionTitle, stepId = null, stepTitle = null, disabled = false,
}: ExecutionViewProps) {
  const [run, setRun] = useState<OrchestratorRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const delayRef = useRef(POLL_MIN_MS);

  const loadLatest = useCallback(async () => {
    try {
      const result = await missionsApi.listRuns(missionId);
      const items = result.items ?? [];
      const match = stepId ? items.find((item) => item.step_id === stepId) : items[0];
      setRun(match ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Chargement des exécutions impossible.');
    } finally {
      setLoading(false);
    }
  }, [missionId, stepId]);

  useEffect(() => {
    setLoading(true);
    void loadLatest();
  }, [loadLatest]);

  const refresh = useCallback(async (target: OrchestratorRun) => {
    try {
      const fresh = await missionsApi.getRun(missionId, target.id, true);
      setRun(fresh);
      delayRef.current = POLL_MIN_MS;
      if (!ACTIVE.has(fresh.status)) return false;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Statut indisponible.');
      delayRef.current = Math.min(delayRef.current * 2, POLL_MAX_MS);
    }
    return true;
  }, [missionId]);

  useEffect(() => {
    if (!run || !ACTIVE.has(run.status)) return;
    let alive = true;
    const timer = window.setTimeout(async () => {
      if (alive) await refresh(run);
      if (alive) setTick((value) => value + 1);
    }, delayRef.current);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [run, refresh, tick]);

  const controls = useMemo(() => pendingControls(run), [run]);
  const isActive = run ? ACTIVE.has(run.status) : false;

  const doDispatch = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await missionsApi.dispatch(missionId, { step_id: stepId });
      setRun(result.run);
      delayRef.current = POLL_MIN_MS;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Lancement impossible.');
    } finally {
      setBusy(false);
    }
  };

  const doStop = async () => {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      await missionsApi.stopRun(missionId, run.id);
      setRun({ ...run, status: 'stopping', raw_status: { ...run.raw_status, status: 'stopping' } });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Arrêt impossible.');
    } finally {
      setBusy(false);
    }
  };

  const doControl = async (control: PendingControl, choice: 'once' | 'deny' | 'clarify', answer = '') => {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      if (choice === 'clarify') {
        await missionsApi.clarifyRun(missionId, run.id, control.request_id, control.execution_generation, answer);
      } else {
        await missionsApi.approveRun(missionId, run.id, control.request_id, control.execution_generation, choice);
      }
      await refresh(run);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Contrôle impossible.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <section className="hz-panel p-4">
        <p className="hz-hint flex items-center gap-2"><Loader2 size={13} className="animate-spin" /> Exécutions…</p>
      </section>
    );
  }

  return (
    <section className="hz-panel p-0">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
        <div>
          <p className="hz-eyebrow flex items-center gap-1.5"><Zap size={11} /> Exécution réelle</p>
          <h2 className="mt-0.5 text-sm font-semibold text-slate-100">
            {stepTitle ?? missionTitle}
          </h2>
        </div>
        {run && <StatusBadge status={run.status} />}
      </div>

      {error && (
        <p className="hz-hint flex items-center gap-1.5 px-4 pt-3 text-amber-200">
          <AlertTriangle size={11} /> {error}
        </p>
      )}

      {!run ? (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-4">
          <p className="hz-hint">Aucune exécution lancée. Hermes est l'orchestrateur pilote.</p>
          <button
            type="button"
            onClick={() => void doDispatch()}
            disabled={disabled || busy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-[11px] font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-40"
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <PlayCircle size={12} />}
            Lancer l'exécution
          </button>
        </div>
      ) : (
        <div className="space-y-3 p-4">
          <dl className="grid grid-cols-2 gap-2 text-[11px] lg:grid-cols-4">
            <div><dt className="text-slate-500">Orchestrateur</dt><dd className="flex items-center gap-1 text-slate-200"><Bot size={11} /> Hermes</dd></div>
            <div><dt className="text-slate-500">Écoulé</dt><dd className="flex items-center gap-1 text-slate-200"><Clock3 size={11} /> {elapsed(run)}</dd></div>
            <div><dt className="text-slate-500">run_id</dt><dd className="truncate font-mono text-slate-300" title={run.run_id}>{run.run_id.slice(0, 16) || '—'}</dd></div>
            <div><dt className="text-slate-500">Phase HORIZON</dt><dd className="text-slate-200">{run.phase}</dd></div>
          </dl>

          {run.status === 'waiting_for_approval' && controls.length === 0 && (
            <p className="hz-hint text-amber-200">Validation en attente : rafraîchissement en cours…</p>
          )}
          {controls.map((control) => (
            <div key={`${control.request_id}-${control.execution_generation}`} className="rounded-lg border border-amber-400/25 bg-amber-400/5 p-3">
              <p className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-100">
                <CheckCircle2 size={12} /> Demande d'approbation {control.kind ?? ''}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void doControl(control, 'once')}
                  disabled={busy}
                  className="rounded border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] text-emerald-100 hover:bg-emerald-400/20 disabled:opacity-40"
                >Autoriser</button>
                <button
                  type="button"
                  onClick={() => void doControl(control, 'deny')}
                  disabled={busy}
                  className="rounded border border-rose-400/30 bg-rose-400/10 px-2.5 py-1 text-[11px] text-rose-100 hover:bg-rose-400/20 disabled:opacity-40"
                >Refuser</button>
              </div>
            </div>
          ))}

          {isActive && (
            <div className="flex flex-wrap items-center gap-2">
              <p className="hz-hint flex items-center gap-1.5"><Loader2 size={11} className="animate-spin" /> Suivi toutes les 2 s…</p>
              <button
                type="button"
                onClick={() => void doStop()}
                disabled={busy || run.status === 'stopping'}
                className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-rose-400/25 px-2.5 py-1 text-[11px] text-rose-200 hover:bg-rose-400/10 disabled:opacity-40"
              ><Square size={11} /> Arrêter</button>
            </div>
          )}

          {run.error && (
            <p className="hz-hint flex items-start gap-1.5 rounded-lg border border-rose-400/20 bg-rose-400/5 p-2 text-rose-200">
              <CircleX size={12} className="mt-0.5 shrink-0" /> {run.error}
            </p>
          )}

          {run.output && (
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="hz-eyebrow flex items-center gap-1.5 mb-1.5"><WandSparkles size={11} /> Livrable</p>
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words font-sans text-[12px] leading-relaxed text-slate-200">{run.output}</pre>
            </div>
          )}

          {(run.usage && Object.keys(run.usage).length > 0) || (run.runtime && Object.keys(run.runtime).length > 0) ? (
            <p className="hz-hint flex flex-wrap items-center gap-3">
              <span className="flex items-center gap-1"><Coins size={11} /> {String(run.usage?.total_tokens ?? '—')} tokens</span>
              <span>Fournisseur : {String(run.runtime?.provider ?? '—')}</span>
              <span>Modèle : {String(run.runtime?.model ?? run.raw_status?.model ?? '—')}</span>
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}

export default ExecutionView;
