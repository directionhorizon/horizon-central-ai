import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, Cpu, Database, HardDrive, ListChecks, Loader2, MemoryStick, RefreshCw, Server } from 'lucide-react';
import { systemApi } from '../../api/system';
import { describeApiError } from '../../api/errors';
import type { OperationEntry, SystemMetrics, SystemStatus } from '../../api/entities';

const pct = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(1)} %` : '—';

const mb = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? `${Math.round(value)} Mo` : '—';

export const SystemMonitorLive = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [operations, setOperations] = useState<OperationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [nextMetrics, nextStatus, nextOperations] = await Promise.all([
        systemApi.metrics(),
        systemApi.status(),
        systemApi.operations(20),
      ]);
      setMetrics(nextMetrics);
      setStatus(nextStatus);
      setOperations(nextOperations.items);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const memoryUsedPercent =
    metrics?.memory.supported && metrics.memory.total_mb
      ? (100 * (metrics.memory.total_mb - (metrics.memory.available_mb ?? 0))) / metrics.memory.total_mb
      : null;

  const diskUsedPercent =
    metrics?.disk.supported && typeof metrics.disk.used_percent === 'number'
      ? metrics.disk.used_percent
      : metrics?.disk.supported && metrics.disk.total_gb
        ? (100 * (metrics.disk.total_gb - (metrics.disk.free_gb ?? 0))) / metrics.disk.total_gb
        : null;

  const gb = (value: number | null | undefined) =>
    typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(1)} Go` : '—';

  return (
    <div className="min-h-screen bg-[#090c13] text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-6 py-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[.18em] text-cyan-300">HORIZON / OPERATIONS</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">System Monitor</h1>
          <p className="mt-1 text-sm text-slate-500">Mesures réelles collectées par le backend local</p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualiser
        </button>
      </header>
      <div className="mx-auto max-w-[1400px] space-y-6 p-5 sm:p-7">
        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-rose-400/25 bg-rose-400/[0.07] p-4">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-300" />
            <p className="text-xs leading-5 text-rose-100">{error}</p>
          </div>
        )}
        <p className="text-[11px] text-slate-500">
          Source : {metrics?.source ?? '—'} · dernière mesure {metrics?.measured_at ?? '—'} · rafraîchissement automatique toutes les 30 s
        </p>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
            <div className="flex items-center justify-between text-xs text-slate-400"><span>CPU</span><Cpu size={16} className="text-cyan-300" /></div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{loading ? '—' : pct(metrics?.cpu_percent)}</p>
            <p className="mt-1 text-[11px] text-slate-600">Charge instantanée mesurée</p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
            <div className="flex items-center justify-between text-xs text-slate-400"><span>Mémoire</span><MemoryStick size={16} className="text-emerald-300" /></div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{loading ? '—' : pct(memoryUsedPercent)}</p>
            <p className="mt-1 text-[11px] text-slate-600">
              {mb(metrics?.memory.available_mb)} libres / {mb(metrics?.memory.total_mb)}
            </p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
            <div className="flex items-center justify-between text-xs text-slate-400"><span>Disque C:</span><HardDrive size={16} className="text-amber-300" /></div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{loading ? '—' : pct(diskUsedPercent)}</p>
            <p className="mt-1 text-[11px] text-slate-600">
              {gb(metrics?.disk.free_gb)} libres / {gb(metrics?.disk.total_gb)}
            </p>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
            <div className="flex items-center justify-between text-xs text-slate-400"><span>Fournisseurs IA</span><CheckCircle2 size={16} className="text-cyan-300" /></div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">
              {loading ? '—' : `${status?.llm.available_providers ?? 0}/${status?.llm.providers ?? 0}`}
            </p>
            <p className="mt-1 text-[11px] text-slate-600">Vérifiés / enregistrés</p>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5">
            <div className="flex items-center gap-2"><Database size={16} className="text-cyan-300" /><h2 className="text-sm font-semibold">État de la base locale</h2></div>
            <dl className="mt-4 space-y-2 text-xs">
              {[
                ['Projets', status?.counts.projects],
                ['Orchestrateurs', status?.counts.orchestrators],
                ['Missions', status?.counts.missions],
                ['Sessions', status?.counts.sessions],
                ['Opérations journalisées', status?.counts.operations],
              ].map(([label, value]) => (
                <div key={String(label)} className="flex items-center justify-between rounded-lg bg-white/[0.025] px-3 py-2">
                  <dt className="text-slate-400">{label}</dt>
                  <dd className="font-semibold tabular-nums text-slate-100">{loading ? '—' : String(value ?? 0)}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 rounded-lg border border-white/[0.07] p-3 text-[11px] leading-5 text-slate-500">
              <p className="flex items-center gap-2 text-slate-300"><Server size={13} /> Authentification : {status?.auth.mode ?? '—'}</p>
              <p className="mt-1">Fournisseurs IA : {status?.llm.status ?? '—'} ({status?.llm.available_providers ?? 0} vérifié(s))</p>
              <p className="mt-1">Généré le {status?.generated_at ?? '—'}</p>
            </div>
          </section>

          <section className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5">
            <div className="flex items-center gap-2"><ListChecks size={16} className="text-cyan-300" /><h2 className="text-sm font-semibold">Journal des opérations ({operations.length})</h2></div>
            <div className="mt-4 max-h-[340px] space-y-2 overflow-y-auto pr-1">
              {operations.map((entry) => (
                <article key={entry.id} className="rounded-lg bg-white/[0.025] p-3">
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="font-medium text-slate-200">{entry.action}</span>
                    <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">{entry.target_type}</span>
                    <span className={entry.result === 'success' ? 'text-emerald-300' : 'text-rose-300'}>{entry.result}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">{entry.detail || '—'}</p>
                  <p className="mt-1 text-[10px] text-slate-600">{entry.created_at} · {entry.actor}</p>
                </article>
              ))}
              {operations.length === 0 && !loading && (
                <p className="p-6 text-center text-xs text-slate-500">Aucune opération journalisée.</p>
              )}
            </div>
          </section>
        </div>

        <p className="flex items-center gap-2 text-center text-[10px] text-slate-600">
          <Activity size={12} /> Mesures issues de /api/v1/system/metrics, /system/status et /operations. Aucune valeur n'est simulée.
        </p>
      </div>
    </div>
  );
};
