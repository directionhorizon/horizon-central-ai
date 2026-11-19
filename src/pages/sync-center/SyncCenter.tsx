import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpFromLine,
  Cloud,
  CloudOff,
  HardDrive,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { syncApi } from '../../api/sync';
import { describeApiError } from '../../api/errors';
import type { SyncConflict, SyncQueueItem, SyncStatus } from '../../api/entities';

const card = 'rounded-xl border border-white/[0.08] bg-white/[0.02] p-5';
const badge = 'rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-slate-400';

export const SyncCenter = () => {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [pending, setPending] = useState<SyncQueueItem[]>([]);
  const [failed, setFailed] = useState<SyncQueueItem[]>([]);
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<null | 'push' | 'pull'>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [nextStatus, nextPending, nextFailed, nextConflicts] = await Promise.all([
        syncApi.status(),
        syncApi.queue('pending', 50),
        syncApi.queue('failed', 20),
        syncApi.conflicts(false),
      ]);
      setStatus(nextStatus);
      setPending(nextPending.items);
      setFailed(nextFailed.items);
      setConflicts(nextConflicts.items);
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

  const run = async (kind: 'push' | 'pull') => {
    setBusy(kind);
    setError(null);
    setNotice(null);
    try {
      const result = kind === 'push' ? await syncApi.push() : await syncApi.pull();
      if (result.status === 'not_configured') {
        setNotice(result.detail ?? 'Aucun fournisseur distant configuré : la file locale est conservée.');
      } else if (kind === 'push') {
        const pushed = await Promise.resolve(result as { pushed: number; failed: number; conflicts: number });
        setNotice(
          `Envoi terminé : ${pushed.pushed} poussé(s), ${pushed.failed} échec(s), ${pushed.conflicts} conflit(s).`,
        );
      } else {
        const pulled = await Promise.resolve(result as { pulled: number; conflicts: number });
        setNotice(`Réception terminée : ${pulled.pulled} élément(s), ${pulled.conflicts} conflit(s).`);
      }
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setBusy(null);
    }
  };

  const resolve = async (id: string) => {
    setError(null);
    try {
      await syncApi.resolveConflict(id);
      setNotice('Conflit marqué comme résolu. Aucune donnée locale n’a été écrasée.');
      await refresh();
    } catch (caught) {
      setError(describeApiError(caught));
    }
  };

  const online = status?.online ?? false;
  const configured = status?.provider_configured ?? false;

  return (
    <div className="min-h-screen bg-[#090c13] text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-6 py-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[.18em] text-cyan-300">
            HORIZON / LOCAL-FIRST
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Synchronisation</h1>
          <p className="mt-1 text-sm text-slate-500">
            Les données locales restent disponibles hors ligne ; le cloud est optionnel.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
              online
                ? 'border-emerald-400/30 bg-emerald-400/[0.08] text-emerald-200'
                : 'border-amber-400/30 bg-amber-400/[0.08] text-amber-200'
            }`}
          >
            {online ? <Wifi size={14} /> : <WifiOff size={14} />}
            {loading ? 'Vérification…' : online ? 'Internet détecté' : 'Hors ligne'}
          </span>
          <button
            type="button"
            onClick={() => void refresh()}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualiser
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-[1400px] space-y-6 p-5 sm:p-7">
        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-rose-400/25 bg-rose-400/[0.07] p-4">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-300" />
            <div>
              <p className="text-xs leading-5 text-rose-100">{error}</p>
              <p className="mt-1 text-[11px] text-rose-200/60">
                Si le backend local est arrêté, l’interface est indisponible mais la base SQLite reste intacte
                sur le disque. Relancez HORIZON pour la retrouver.
              </p>
            </div>
          </div>
        )}
        {notice && (
          <>
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>File d’attente</span>
              <ArrowUpFromLine size={16} className="text-cyan-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.pending ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Écritures locales à pousser</p>
          </div>
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Déjà synchronisées</span>
              <Cloud size={16} className="text-emerald-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.synced ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Envoyées au service distant</p>
          </div>
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Échecs</span>
              <CloudOff size={16} className="text-amber-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.failed ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Réessai manuel possible</p>
          </div>
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Conflits ouverts</span>
              <AlertTriangle size={16} className="text-rose-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.conflicts ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Aucun écrasement silencieux</p>
          </div>
        </section>

          <div className="flex items-start gap-3 rounded-xl border border-cyan-400/25 bg-cyan-400/[0.06] p-4">
            <ShieldCheck size={18} className="mt-0.5 shrink-0 text-cyan-300" />
            <p className="text-xs leading-5 text-cyan-100">{notice}</p>
          </div>
          </>
        )}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>File d’attente</span>
              <ArrowUpFromLine size={16} className="text-cyan-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.pending ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Écritures locales à pousser</p>
          </div>
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Déjà synchronisées</span>
              <Cloud size={16} className="text-emerald-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.synced ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Envoyées au service distant</p>
          </div>
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Échecs</span>
              <CloudOff size={16} className="text-amber-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.failed ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Réessai manuel possible</p>
          </div>
          <div className={card}>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Conflits ouverts</span>
              <AlertTriangle size={16} className="text-rose-300" />
            </div>
            <p className="mt-3 text-3xl font-semibold tabular-nums">{status?.queue.conflicts ?? 0}</p>
            <p className="mt-1 text-[11px] text-slate-600">Aucun écrasement silencieux</p>
          </div>
        </section>

        <section className={`${card} flex flex-wrap items-center justify-between gap-4`}>
          <div className="text-xs leading-6 text-slate-400">
            <p className="flex items-center gap-2 text-slate-200">
              <HardDrive size={14} className="text-cyan-300" /> Stockage de référence :{' '}
              {status?.primary_store === 'supabase' ? 'Supabase (distant)' : 'SQLite (local)'}
              {status?.secondary_store === 'sqlite' ? ' · copie locale SQLite pour le hors-ligne' : ''}
            </p>
            <p>
              Synchronisation distante :{' '}
              <span className="text-slate-200">{configured ? 'configurée' : 'non configurée'}</span>
              {configured
                ? ' — un test réel est nécessaire avant de la déclarer opérationnelle.'
                : ' — rien n’est perdu : les écritures sont conservées localement puis envoyées dès que Supabase est configuré.'}
            </p>
            <p className="text-[11px] text-slate-500">
              Dernière synchronisation :{' '}
              {status?.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : 'jamais'} · envoi
              automatique : {status?.worker_active ? 'actif' : 'inactif'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void run('push')}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs text-cyan-100 hover:bg-cyan-400/20 disabled:opacity-40"
            >
              {busy === 'push' ? <Loader2 size={14} className="animate-spin" /> : <ArrowUpFromLine size={14} />}
              Pousser la file
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void run('pull')}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5 disabled:opacity-40"
            >
              {busy === 'pull' ? <Loader2 size={14} className="animate-spin" /> : <ArrowDownToLine size={14} />}
              Récupérer le distant
            </button>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className={card}>
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className="text-rose-300" />
              <h2 className="text-sm font-semibold">Conflits de synchronisation ({conflicts.length})</h2>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-slate-500">
              Un conflit est consigné lorsque local et distant divergent. Rien n’est écrasé automatiquement :
              la résolution reste une décision humaine.
            </p>
            <div className="mt-4 max-h-[320px] space-y-2 overflow-y-auto pr-1">
              {conflicts.map((item) => (
                <article key={item.id} className="rounded-lg bg-white/[0.025] p-3">
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="font-medium text-slate-200">{item.entity}</span>
                    <span className={badge}>{item.entity_id.slice(0, 8)}</span>
                    <span className="text-rose-300">non résolu</span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">{item.reason}</p>
                  <p className="mt-1 text-[10px] text-slate-600">
                    local {item.local_updated_at ?? '—'} · distant {item.remote_updated_at ?? '—'}
                  </p>
                  <button
                    type="button"
                    onClick={() => void resolve(item.id)}
                    className="mt-2 rounded-lg border border-white/10 px-2 py-1 text-[10px] text-slate-300 hover:bg-white/5"
                  >
                    Marquer comme résolu
                  </button>
                </article>
              ))}
              {conflicts.length === 0 && !loading && (
                <p className="p-6 text-center text-xs text-slate-500">Aucun conflit ouvert.</p>
              )}
            </div>
          </section>

          <section className={card}>
            <div className="flex items-center gap-2">
              <ArrowUpFromLine size={16} className="text-cyan-300" />
              <h2 className="text-sm font-semibold">File locale en attente ({pending.length})</h2>
            </div>
            <div className="mt-4 max-h-[320px] space-y-2 overflow-y-auto pr-1">
              {pending.map((item) => (
                <article key={item.id} className="rounded-lg bg-white/[0.025] p-3">
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="font-medium text-slate-200">{item.entity}</span>
                    <span className={badge}>{item.operation}</span>
                    <span className="text-cyan-300">{item.status}</span>
                    <span className="text-slate-500">{item.attempts} tentative(s)</span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-600">
                    {item.entity_id.slice(0, 8)} · {item.created_at}
                  </p>
                </article>
              ))}
              {pending.length === 0 && !loading && (
                <p className="p-6 text-center text-xs text-slate-500">File vide : tout est synchronisé ou rien n’a été écrit.</p>
              )}
              {failed.length > 0 && (
                <div className="mt-3 rounded-lg border border-amber-400/20 bg-amber-400/[0.05] p-3">
                  <p className="text-[11px] text-amber-200">
                    {failed.length} écriture(s) en échec — détail : {failed[0].last_error || 'inconnu'}
                  </p>
                </div>
              )}
            </div>
          </section>
        </div>

        <p className="flex items-center gap-2 text-[10px] text-slate-600">
          <ShieldCheck size={12} /> Vos données restent locales. Les détails techniques (chemins, sondes,
          variables attendues) sont réservés au diagnostic protégé.
        </p>
      </div>
    </div>
  );
};

