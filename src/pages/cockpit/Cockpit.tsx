import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, ArrowUpRight, Boxes, BrainCircuit, ChevronLeft, ChevronRight,
  Cpu, Database, Gauge, Loader2, Network, PanelRightOpen, RefreshCw, Send, Settings2,
  ShieldCheck, Sparkles, Wifi, WifiOff, X,
} from 'lucide-react';
import { projectsApi } from '../../api/projects';
import { missionsApi } from '../../api/missions';
import { orchestratorsApi } from '../../api/orchestrators';
import { modelsApi } from '../../api/models';
import { systemApi, coreApi } from '../../api/system';
import { syncApi } from '../../api/sync';
import { describeApiError } from '../../api/errors';
import { apiConfig } from '../../config/env';
import type {
  Mission, Orchestrator, ProjectSummary, SyncStatus, SystemStatus,
} from '../../api/entities';
import { useChatSession } from '../../shared/ChatSessionContext';
import { ModelManagerLive } from '../model-manager/ModelManagerLive';
import { KnowledgeMemoryLive } from '../knowledge-memory-hub/KnowledgeMemoryLive';
import { AgentsToolsCatalog } from '../agents-tools-catalog/AgentsToolsCatalog';
import { SystemMonitorLive } from '../system-monitor/SystemMonitorLive';
import { SyncCenter } from '../sync-center/SyncCenter';
import { ThemeControls } from '../../theme/ThemeControls';
import { useTheme } from '../../theme/ThemeProvider';
import { useWorkspaceLayout, RAIL_WIDTH } from '../../workspace/useWorkspaceLayout';
import { CoreActivity, MissionPipeline, deriveCoreState } from '../../components/CoreActivity';
import { ExecutionView } from '../../components/ExecutionView';

type DrawerId = 'models' | 'memory' | 'tools' | 'security' | 'sync' | 'monitor' | 'settings';

const panel = 'hz-panel';
const chip = 'hz-btn hz-btn--ghost';
const chipOn = 'hz-btn hz-btn--primary';

const DRAWERS: ReadonlyArray<{ id: DrawerId; label: string; icon: typeof Cpu }> = [
  // Les espaces Modèles, Mémoire, Outils & agents, Synchronisation et Supervision
  // disposent déjà de leur propre page dans la barre supérieure : ne pas les
  // dupliquer ici. Il ne reste que ce qui n'existe nulle part ailleurs.
  { id: 'security', label: 'Sécurité & permissions', icon: ShieldCheck },
  { id: 'settings', label: 'Préférences', icon: Settings2 },
];

export function Cockpit() {
  const navigate = useNavigate();
  const { resolved } = useTheme();
  const {
    messages, sessionTitle, status: chatStatus, errorMessage, execution, warnings,
    refreshSessions, createSession, sendMessage, resetSession, clearError,
  } = useChatSession();

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [orchestrators, setOrchestrators] = useState<Orchestrator[]>([]);
  const [providerCount, setProviderCount] = useState(0);
  const [availableModels, setAvailableModels] = useState(0);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<DrawerId | null>(null);
  /* Disposition indépendante des deux panneaux : largeurs, repli, persistance. */
  const ws = useWorkspaceLayout();
  const leftOpen = !ws.layout.leftCollapsed;
  const rightOpen = !ws.layout.rightCollapsed;
  const setLeftOpen = (_update: (value: boolean) => boolean) => ws.toggle('left');
  const setRightOpen = (_update: (value: boolean) => boolean) => ws.toggle('right');
  const feedRef = useRef<HTMLDivElement | null>(null);

  const refreshContext = useCallback(async () => {
    try {
      const [projectList, orchestratorList, modelList, system, sync] = await Promise.all([
        projectsApi.list(),
        orchestratorsApi.list(),
        modelsApi.list(),
        systemApi.status(),
        syncApi.status(),
      ]);
      setProjects(projectList.items);
      setProjectId((current) => current ?? projectList.default_project_id ?? projectList.items[0]?.id ?? null);
      setOrchestrators(orchestratorList.items);
      setProviderCount(modelList.items.length);
      setAvailableModels(modelList.items.filter((item) => item.status === 'available').length);
      setSystemStatus(system);
      setSyncStatus(sync);
      setError(null);
    } catch (caught) {
      setError(describeApiError(caught));
    }
  }, []);

  useEffect(() => {
    void refreshContext();
    void refreshSessions();
    const timer = window.setInterval(() => void refreshContext(), 30_000);
    return () => window.clearInterval(timer);
  }, [refreshContext, refreshSessions]);

  useEffect(() => {
    if (!projectId) return;
    void (async () => {
      try {
        const list = await missionsApi.list({ projectId });
        setMissions(list.items);
      } catch {
        setMissions([]);
      }
    })();
  }, [projectId]);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [messages.length]);

  const activeOrchestrators = useMemo(
    () => orchestrators.filter((item) => item.status === 'active'),
    [orchestrators],
  );
  const online = syncStatus?.online ?? false;
  const providerConfigured = syncStatus?.provider_configured ?? false;
  const activeProject = useMemo(
    () => projects.find((item) => item.id === projectId) ?? null,
    [projects, projectId],
  );

  /**
   * Ce qui nécessite réellement une intervention, déduit uniquement d'états
   * mesurés (sondes, registre, file locale). Aucun élément inventé.
   */
  const interventions = useMemo(() => {
    const items: Array<{ id: string; label: string }> = [];
    if (error) {
      items.push({ id: 'backend', label: 'Service local injoignable : vérifier que le moteur HORIZON est démarré.' });
    }
    if (syncStatus && !syncStatus.provider_configured) {
      items.push({
        id: 'sync-provider',
        label: 'Synchronisation distante non configurée : les données restent locales et rien n’est perdu.',
      });
    }
    if (syncStatus && syncStatus.queue.conflicts > 0) {
      items.push({
        id: 'conflicts',
        label: `${syncStatus.queue.conflicts} conflit(s) de synchronisation à arbitrer — aucune donnée n'est écrasée automatiquement.`,
      });
    }
    if (syncStatus && syncStatus.queue.failed > 0) {
      items.push({ id: 'failed', label: `${syncStatus.queue.failed} écriture(s) locale(s) en échec à relancer.` });
    }
    if (providerCount === 0) {
      items.push({ id: 'llm', label: 'Aucun fournisseur IA enregistré : HORIZON CORE répond « no_model ».' });
    } else if (availableModels === 0) {
      items.push({ id: 'llm-unverified', label: 'Fournisseur(s) enregistré(s) mais aucun modèle vérifié : lancer un test depuis l’espace Modèles.' });
    }
    const failedMissions = missions.filter((mission) => mission.status === 'failed').length;
    if (failedMissions > 0) {
      items.push({ id: 'mission-failed', label: `${failedMissions} mission(s) en échec à reprendre.` });
    }
    if (systemStatus?.auth.auth_enabled) {
      items.push({ id: 'auth', label: 'Jeton administrateur actif : les écritures exigent un en-tête Authorization.' });
    }
    return items;
  }, [error, syncStatus, providerCount, availableModels, missions, systemStatus]);

  /** Mission suivie dans le panneau contexte : la plus réellement active. */
  const activeMission = useMemo<Mission | null>(() => {
    const running = missions.find((item) => item.status === 'running');
    const paused = missions.find((item) => item.status === 'paused');
    const failed = missions.find((item) => item.status === 'failed');
    return running ?? paused ?? failed ?? missions[0] ?? null;
  }, [missions]);

  /** État réel de HORIZON CORE, déduit uniquement de faits observés. */
  const coreState = deriveCoreState({
    sending,
    planning,
    error,
    executionStatus: execution?.status ?? null,
    mission: activeMission,
  });


  const send = async () => {
    const content = draft.trim();
    if (!content) return;
    setSending(true);
    setError(null);
    setNotice(null);
    setDraft('');
    try {
      await sendMessage(content);
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setSending(false);
    }
  };

  /** Planification réelle via HORIZON CORE : aucun plan fabriqué sans modèle. */
  const plan = async () => {
    const content = draft.trim();
    if (!content || !projectId) return;
    setPlanning(true);
    setError(null);
    setNotice(null);
    try {
      const result = await coreApi.plan(projectId, content);
      if (result.status === 'planned' && result.mission) {
        setNotice(`Mission planifiée : ${result.mission.title}`);
        const list = await missionsApi.list({ projectId });
        setMissions(list.items);
      } else {
        setNotice(result.detail ?? 'HORIZON CORE ne peut pas planifier : aucun modèle configuré.');
      }
    } catch (caught) {
      setError(describeApiError(caught));
    } finally {
      setPlanning(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090c13] text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-3">
        <div className="flex items-center gap-2">
          <button type="button" className={leftOpen ? chipOn : chip} onClick={() => setLeftOpen((v) => !v)} title="Panneau gauche">
            <ChevronLeft size={12} className="mr-1 inline" />{leftOpen ? 'Masquer' : 'Afficher'}
          </button>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[.18em] text-cyan-300">HORIZON CENTRAL AI / POSTE DE PILOTAGE</p>
            <h1 className="text-lg font-semibold tracking-tight">
              {sessionTitle ?? 'Conversation avec HORIZON CORE'}
            </h1>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 ${chip}`}>
            {online ? <Wifi size={11} /> : <WifiOff size={11} />}
            {online ? 'Internet détecté' : 'Hors ligne'}
          </span>
          <span className={chip}>Thème : {resolved}</span>
          <button type="button" className={chip} onClick={() => void refreshContext()} title="Actualiser l’état">
            <RefreshCw size={11} className="mr-1 inline" />Actualiser
          </button>
          <button type="button" className={rightOpen ? chipOn : chip} onClick={() => setRightOpen((v) => !v)} title="Panneau droit">
            <PanelRightOpen size={12} className="mr-1 inline" />Contexte
          </button>
          <button
            type="button"
            className={chip}
            onClick={() => ws.reset()}
            title="Restaurer la disposition initiale : les deux panneaux visibles, largeurs par défaut"
          >
            <RefreshCw size={11} className="mr-1 inline" />Disposition
          </button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-1.5 border-b border-white/10 px-5 py-2">
        {DRAWERS.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.id} type="button" className={drawer === item.id ? chipOn : chip} onClick={() => setDrawer(item.id)}>
              <Icon size={11} className="mr-1 inline" />{item.label}
            </button>
          );
        })}
        <span className="hz-hint">
          Les espaces Modèles, Mémoire, Outils, Synchronisation et Supervision sont déjà dans la
          barre du haut — ils ne sont plus répétés ici.
        </span>
      </div>

      {(error || errorMessage) && (
        <div className="mx-5 mt-3 flex items-start gap-2 rounded-lg border border-rose-400/25 bg-rose-400/[0.07] p-3">
          <AlertTriangle size={15} className="mt-0.5 shrink-0 text-rose-300" />
          <p className="text-[11px] leading-5 text-rose-100">{error ?? errorMessage}</p>
          <button type="button" className="ml-auto text-rose-200" onClick={() => { setError(null); clearError(); }}>
            <X size={13} />
          </button>
        </div>
      )}
      {notice && (
        <div className="mx-5 mt-3 flex items-start gap-2 rounded-lg border border-cyan-400/25 bg-cyan-400/[0.06] p-3">
          <Sparkles size={15} className="mt-0.5 shrink-0 text-cyan-300" />
          <p className="text-[11px] leading-5 text-cyan-100">{notice}</p>
          <button type="button" className="ml-auto text-cyan-200" onClick={() => setNotice(null)}>
            <X size={13} />
          </button>
        </div>
      )}

      {/* Bandeau d'état : lecture immédiate de la situation réelle du système. */}
      <section className="hz-enter mx-5 mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="hz-kpi hz-lift">
          <p className="hz-kpi__label">Projet actif</p>
          <p className="hz-title truncate">{activeProject?.name ?? 'aucun projet'}</p>
          <p className="hz-hint">
            {activeProject
              ? `${activeProject.status} · ${activeProject.mission_count} mission(s) · ${activeProject.orchestrator_count} orchestrateur(s)`
              : 'Créer un projet pour démarrer un cycle de pilotage'}
          </p>
        </div>
        <div className="hz-kpi hz-lift">
          <p className="hz-kpi__label">Missions du projet</p>
          <p className="hz-kpi__value">{missions.length}</p>
          <p className="hz-hint">
            {missions.filter((mission) => mission.status === 'running').length} en cours ·{' '}
            {missions.filter((mission) => mission.status === 'failed').length} en échec
          </p>
        </div>
        <div className="hz-kpi hz-lift">
          <p className="hz-kpi__label">Orchestrateurs actifs</p>
          <p className="hz-kpi__value">
            {activeOrchestrators.length}
            <span className="text-sm font-semibold text-slate-500">/{orchestrators.length}</span>
          </p>
          <p className="hz-hint">{providerCount} fournisseur(s) IA · {availableModels} modèle(s) vérifié(s)</p>
        </div>
        <div className={interventions.length > 0 ? 'hz-kpi hz-kpi--accent hz-lift' : 'hz-kpi hz-lift'}>
          <p className="hz-kpi__label">Interventions requises</p>
          <p className="hz-kpi__value">{interventions.length}</p>
          <p className="hz-hint truncate">{interventions[0]?.label ?? 'aucune action en attente'}</p>
        </div>
      </section>

      {interventions.length > 0 && (
        <section className="hz-enter mx-5 mt-3 hz-alert hz-alert--warn">
          <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          <div className="hz-alert__text">
            <p className="font-semibold">Éléments nécessitant une décision ou une action</p>
            <ul className="mt-1 space-y-0.5">
              {interventions.map((item) => (
                <li key={item.id}>· {item.label}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {ws.viewport !== 'desktop' && (leftOpen || rightOpen) && (
        <button
          type="button"
          className="ws-backdrop"
          aria-label="Fermer les panneaux latéraux"
          onClick={() => {
            if (leftOpen) ws.toggle('left');
            if (rightOpen) ws.toggle('right');
          }}
        />
      )}

      <div
        className="ws-shell"
        style={
          {
            '--ws-left': `${leftOpen ? ws.layout.leftWidth : RAIL_WIDTH}px`,
            '--ws-right': `${rightOpen ? ws.layout.rightWidth : RAIL_WIDTH}px`,
          } as CSSProperties
        }
      >
        {/* ---------------- Panneau gauche : contexte de session uniquement ----------------
            Les listes complètes (projets, missions, sessions, orchestrateurs) vivent
            sur leurs propres pages. Ici on ne garde que le contexte de travail :
            projet actif, mission suivie, compteurs — pas de doublon visuel. */}
        {leftOpen ? (
          <aside className="ws-pane ws-pane--left hz-enter hz-enter--1 space-y-4">
            <section className={panel}>
              <div className="flex items-center justify-between px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Contexte de session</p>
                <button type="button" className={chip} onClick={() => navigate('/projects')} title="Ouvrir Projets & missions">
                  <ArrowUpRight size={11} />
                </button>
              </div>
              <div className="space-y-2 px-3 pb-3">
                <label className="block">
                  <span className="mb-1 block text-[10px] uppercase tracking-[.12em] text-slate-500">Projet actif</span>
                  <select
                    value={projectId ?? ''}
                    onChange={(event) => setProjectId(event.target.value || null)}
                    className="h-8 w-full rounded-lg border border-white/10 bg-white/[0.04] px-2 text-[11px] text-slate-200"
                  >
                    {projects.length === 0 && <option value="">Aucun projet</option>}
                    {projects.map((item) => (
                      <option key={item.id} value={item.id}>{item.name}</option>
                    ))}
                  </select>
                </label>
                <div className="rounded-lg bg-white/[0.025] px-2 py-1.5">
                  <p className="text-[10px] uppercase tracking-[.12em] text-slate-500">Mission suivie</p>
                  <p className="truncate text-[11px] font-medium text-slate-200">
                    {activeMission?.title ?? 'aucune mission'}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    {activeMission
                      ? `${activeMission.status} · ${(activeMission.steps ?? []).length} étape(s)`
                      : `${missions.length} mission(s) sur ce projet`}
                  </p>
                </div>
                <div className="flex items-center justify-between gap-2 text-[10px] text-slate-500">
                  <span>{missions.length} mission(s)</span>
                  <button type="button" className={chip} onClick={() => void createSession()} title="Nouvelle session">
                    + Nouvelle session
                  </button>
                </div>
                <button type="button" className={chip} onClick={() => navigate('/orchestrators')}>
                  Voir les orchestrateurs <ArrowUpRight size={10} className="ml-0.5 inline" />
                </button>
              </div>
            </section>

            <section className={panel}>
              <p className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Alertes</p>
              <div className="px-3 pb-3">
                {interventions.length === 0 ? (
                  <p className="text-[10px] text-slate-500">Aucune alerte : tout ce qui est mesuré répond.</p>
                ) : (
                  <ul className="space-y-1">
                    {interventions.slice(0, 4).map((item) => (
                      <li key={item.id} className="flex items-start gap-1.5 text-[10px] leading-4 text-slate-400">
                        <AlertTriangle size={10} className="mt-0.5 shrink-0 text-amber-300" />
                        {item.label}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          </aside>
        ) : (
          <div className="ws-rail ws-rail--left">
            <button
              type="button"
              className="ws-rail__btn"
              onClick={() => setLeftOpen((v) => !v)}
              title="Afficher la navigation"
              aria-label="Afficher la navigation"
            >
              <ChevronRight size={15} />
            </button>
            <span className="ws-rail__label">Navigation</span>
          </div>
        )}
        <div
          className="ws-handle ws-handle--left"
          role="separator"
          aria-orientation="vertical"
          aria-label="Ajuster la largeur du panneau gauche"
          onPointerDown={ws.startResize('left')}
        />

        {/* ---------------- Zone centrale : conversation HORIZON CORE ---------------- */}
        <main className="hz-enter hz-enter--2 flex flex-col">
          <section className={`${panel} flex flex-1 flex-col`}>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Conversation HORIZON CORE</p>
              <div className="flex items-center gap-2">
                {execution && (
                  <span className={chip}>
                    exécution : {execution.status}
                    {execution.model_id ? ` · ${execution.model_id}` : ''}
                  </span>
                )}
                <button type="button" className={chip} onClick={() => void resetSession()} title="Vider la conversation">Vider</button>
              </div>
            </div>

            <div ref={feedRef} className="max-h-[52vh] flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {messages.length === 0 && (
                <p className="py-10 text-center text-xs text-slate-500">
                  Aucun message. Écrivez une demande à HORIZON CORE.
                </p>
              )}
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={
                    message.role === 'user'
                      ? 'ml-auto max-w-[80%] rounded-xl bg-cyan-400/10 px-3 py-2'
                      : 'mr-auto max-w-[85%] rounded-xl bg-white/5 px-3 py-2'
                  }
                >
                  <p className="text-[10px] uppercase tracking-wide text-slate-500">
                    {message.role} · {message.time}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-slate-200">{message.content}</p>
                </article>
              ))}
              {chatStatus === 'loading' && (
                <p className="flex items-center gap-2 text-[11px] text-slate-500">
                  <Loader2 size={12} className="animate-spin" /> Chargement…
                </p>
              )}
            </div>

            {warnings.length > 0 && (
              <div className="border-t border-white/10 px-3 py-2">
                {warnings.map((warning) => (
                  <p key={warning} className="text-[10px] text-amber-200">⚠ {warning}</p>
                ))}
              </div>
            )}

            <div className="border-t border-white/10 p-3">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    void send();
                  }
                }}
                rows={3}
                placeholder="Décrivez la mission, la question ou l’action attendue…"
                className="w-full resize-y rounded-lg border border-white/10 bg-transparent px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400/40 focus:outline-none"
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={sending}
                  onClick={() => void send()}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-[11px] text-slate-200 hover:bg-white/5 disabled:opacity-40"
                >
                  {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Envoyer
                </button>
                <button
                  type="button"
                  disabled={planning || !projectId}
                  onClick={() => void plan()}
                  className="inline-flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-[11px] text-cyan-100 hover:bg-cyan-400/20 disabled:opacity-40"
                >
                  {planning ? <Loader2 size={12} className="animate-spin" /> : <BrainCircuit size={12} />} Planifier avec HORIZON CORE
                </button>
                <span className="text-[10px] text-slate-600">
                  {availableModels > 0
                    ? `${availableModels} modèle(s) vérifié(s) sur ${providerCount} fournisseur(s)`
                    : 'Aucun modèle vérifié : la planification répondra « no_model » (refus honnête).'}
                </span>
              </div>
            </div>
          </section>
        </main>

        {/* ---------------- Panneau droit : orchestrateurs, ressources, état ---------------- */}
        <div
          className="ws-handle ws-handle--right"
          role="separator"
          aria-orientation="vertical"
          aria-label="Ajuster la largeur du panneau droit"
          onPointerDown={ws.startResize('right')}
        />
        {rightOpen ? (
          <aside className="ws-pane ws-pane--right hz-enter hz-enter--3 space-y-4">
            <section className={panel}>
              <div className="flex items-center justify-between px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">HORIZON CORE</p>
                <span className="hz-hint">état mesuré</span>
              </div>
              <div className="flex flex-col gap-2 px-3 pb-3">
                <CoreActivity state={coreState} />
                <MissionPipeline mission={activeMission} />
              </div>
            </section>
            {activeMission && (
              <ExecutionView
                missionId={activeMission.id}
                missionTitle={activeMission.title}
                disabled={!activeMission.id}
              />
            )}
            <section className={panel}>
              <div className="flex items-center justify-between px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Orchestrateurs</p>
                <button type="button" className={chip} onClick={() => navigate('/orchestrators')} title="Ouvrir le registre">
                  <ArrowUpRight size={11} />
                </button>
              </div>
              {/* Synthèse seulement : la liste détaillée vit sur la page Orchestrateurs. */}
              <div className="px-3 pb-3">
                <p className="text-[11px] text-slate-300">
                  {activeOrchestrators.length} actif(s) sur {orchestrators.length} enregistré(s)
                </p>
                <p className="mt-1 text-[10px] text-slate-500">
                  {orchestrators.filter((item) => item.health_status === 'available').length} vérifié(s) disponible(s)
                  {' · '}
                  {orchestrators.filter((item) => item.health_status === 'unavailable').length} injoignable(s)
                </p>
              </div>
            </section>

            <section className={panel}>
              <p className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Ressources</p>
              {/* Seulement ce qui n'apparaît pas déjà dans le bandeau KPI du haut :
                  les compteurs Projets / Missions / Orchestrateurs y figurent déjà. */}
              <dl className="space-y-1 px-3 pb-3 text-[11px]">
                {[
                  ['Fournisseurs IA', `${providerCount}`],
                  ['Modèles vérifiés', `${availableModels}`],
                  ['Sessions', `${systemStatus?.counts.sessions ?? '—'}`],
                ].map(([text, value]) => (
                  <div key={text} className="flex items-center justify-between rounded-lg bg-white/[0.025] px-2 py-1">
                    <dt className="text-slate-400">{text}</dt>
                    <dd className="font-semibold tabular-nums text-slate-200">{value}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section className={panel}>
              <p className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Progression du projet</p>
              <div className="px-3 pb-3">
                {[
                  ['draft', 'brouillon'],
                  ['planned', 'planifiée'],
                  ['running', 'en cours'],
                  ['paused', 'en pause'],
                  ['completed', 'terminée'],
                  ['failed', 'en échec'],
                ].map(([state, label]) => {
                  const count = missions.filter((mission) => mission.status === state).length;
                  if (count === 0) return null;
                  return (
                    <div key={state} className="mb-1 flex items-center gap-2 text-[11px]">
                      <span className="w-20 text-slate-400">{label}</span>
                      <span className="h-1.5 flex-1 rounded-full bg-white/5">
                        <span
                          className="block h-1.5 rounded-full bg-cyan-400"
                          style={{ width: `${Math.round((100 * count) / Math.max(1, missions.length))}%` }}
                        />
                      </span>
                      <span className="tabular-nums text-slate-400">{count}</span>
                    </div>
                  );
                })}
                {missions.length === 0 && <p className="text-[10px] text-slate-500">Aucune mission pour ce projet.</p>}
              </div>
            </section>

            <section className={panel}>
              <p className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">État des connexions</p>
              <ul className="space-y-1 px-3 pb-3 text-[11px]">
                <li className="flex items-center gap-2 text-slate-400">
                  <Gauge size={12} /> Backend local : {systemStatus ? 'répond (vérifié)' : 'inconnu'}
                </li>
                <li className="flex items-center gap-2 text-slate-400">
                  {online ? <Wifi size={12} /> : <WifiOff size={12} />} Internet : {online ? 'détecté' : 'absent'}
                </li>
                <li className="flex items-center gap-2 text-slate-400">
                  <Network size={12} /> Synchronisation distante : {providerConfigured ? 'configurée' : 'non configurée'}
                </li>
                <li className="flex items-center gap-2 text-slate-400">
                  <Database size={12} /> File locale : {syncStatus?.queue.pending ?? 0} en attente ·{' '}
                  {syncStatus?.queue.conflicts ?? 0} conflit(s)
                </li>
                <li className="flex items-center gap-2 text-slate-400">
                  <ShieldCheck size={12} /> Authentification : {systemStatus?.auth.mode ?? '—'}
                </li>
              </ul>
              <p className="px-3 pb-3 text-[10px] text-slate-600">
                Aucune connexion n’est déclarée active sans vérification : les valeurs ci-dessus proviennent
                des sondes réelles du backend.
              </p>
            </section>
          </aside>
        ) : (
          <div className="ws-rail ws-rail--right">
            <button
              type="button"
              className="ws-rail__btn"
              onClick={() => setRightOpen((v) => !v)}
              title="Afficher le contexte"
              aria-label="Afficher le contexte"
            >
              <ChevronLeft size={15} />
            </button>
            <span className="ws-rail__label">Contexte</span>
          </div>
        )}
      </div>



      {/* ---------------- Espaces secondaires : tiroirs contextuels ---------------- */}
      {drawer && (
        <div className="hz-overlay fixed inset-0 z-[1500] flex justify-end bg-black/55" role="dialog" aria-modal="true">
          <button type="button" aria-label="Fermer" className="flex-1 cursor-default" onClick={() => setDrawer(null)} />
          <div className="hz-drawer flex h-full w-full max-w-[min(1100px,92vw)] flex-col border-l border-white/10 bg-[#0A0B10]">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[.16em] text-cyan-300">
                {DRAWERS.find((item) => item.id === drawer)?.label}
              </p>
              <button type="button" className={chip} onClick={() => setDrawer(null)}>
                <X size={12} className="mr-1 inline" />Fermer
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {drawer === 'models' && <ModelManagerLive />}
              {drawer === 'memory' && <KnowledgeMemoryLive />}
              {drawer === 'tools' && <AgentsToolsCatalog />}
              {drawer === 'sync' && <SyncCenter />}
              {drawer === 'monitor' && <SystemMonitorLive />}
              {drawer === 'settings' && (
                <div className="p-5">
                  <ThemeControls />
                  <div className={`${panel} mt-5 p-4`}>
                    <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Moteur et stockage</p>
                    <ul className="mt-2 space-y-1 text-[11px] text-slate-400">
                      <li>
                        Moteur de commande : <span className="text-slate-200">{apiConfig.baseUrl}</span> — il peut
                        être <strong>local</strong> (cet ordinateur) ou <strong>distant</strong> ; l’adresse est
                        définie par la variable <span className="text-slate-300">VITE_HORIZON_API_URL</span>.
                      </li>
                      <li>
                        Stockage de référence :{' '}
                        <span className="text-slate-200">
                          {syncStatus?.primary_store === 'supabase' ? 'Supabase (distant)' : 'SQLite (local)'}
                        </span>
                        {syncStatus?.secondary_store === 'sqlite'
                          ? ' — copie locale SQLite conservée pour le hors-ligne'
                          : ''}
                        .
                      </li>
                      <li>Les clés restent côté moteur : jamais dans l’interface.</li>
                      <li>Synchronisation distante : {providerConfigured ? 'configurée' : 'non configurée'}.</li>
                      <li>
                        Système :{' '}
                        {systemStatus
                          ? `${systemStatus.counts.projects} projet(s), ${systemStatus.counts.sessions} session(s)`
                          : '—'}
                      </li>
                    </ul>
                  </div>
                </div>
              )}
              {drawer === 'security' && (
                <div className="space-y-4 p-5">
                  <section className={panel}>
                    <p className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Authentification</p>
                    <ul className="space-y-1 px-3 pb-3 text-[11px] text-slate-400">
                      <li>Mode : {systemStatus?.auth.mode ?? '—'}</li>
                      <li>Jeton administrateur : {systemStatus?.auth.auth_enabled ? 'activé' : 'non activé'}</li>
                      <li>Détails techniques : diagnostic protégé (espace Supervision).</li>
                    </ul>
                    <p className="px-3 pb-3 text-[10px] text-slate-600">
                      Aucune saisie de jeton n’est proposée ici : l’interface ne transporte jamais de secret.
                    </p>
                  </section>
                  <section className={panel}>
                    <div className="flex items-center justify-between px-3 py-2.5">
                      <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-slate-500">Journal des opérations</p>
                      <button type="button" className={chip} onClick={() => navigate('/monitor')}>Supervision</button>
                    </div>
                    <p className="px-3 pb-3 text-[11px] text-slate-400">
                      Toutes les opérations sensibles sont journalisées localement et consultables dans
                      l’espace Supervision. Aucune donnée sensible n’y est écrite.
                    </p>
                  </section>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Cockpit;
