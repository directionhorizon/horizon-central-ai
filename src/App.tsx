import { type ReactNode, useEffect, useRef } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Cpu, Network, Database, Bot, Activity, FolderKanban, Cloud, Gauge, Plug, Sparkles, Users } from 'lucide-react';
import { BackendUnavailable } from './components/BackendUnavailable';
import { MainWorkbench } from './pages/main-workbench/MainWorkbench';
import { ModelManagerLive } from './pages/model-manager/ModelManagerLive';
import { OrchestratorRegistry } from './pages/orchestrator-registry/OrchestratorRegistry';
import { Projects } from './pages/projects/Projects';
import { KnowledgeMemoryLive } from './pages/knowledge-memory-hub/KnowledgeMemoryLive';
import { AIControlCenter } from './pages/ai-control-center/AIControlCenter';
import { SystemMonitorLive } from './pages/system-monitor/SystemMonitorLive';
import { SyncCenter } from './pages/sync-center/SyncCenter';
import { Integrations } from './pages/integrations/Integrations';
import { SkillsLibrary } from './pages/skills/SkillsLibrary';
import { AgentsToolsCatalog } from './pages/agents-tools-catalog/AgentsToolsCatalog';
import { Cockpit } from './pages/cockpit/Cockpit';
import { ChatSessionProvider, useChatSession } from './shared/ChatSessionContext';
import { ConnectionsProvider } from './shared/ConnectionsContext';

type PageId = 'cockpit' | 'workbench' | 'projects' | 'models' | 'orchestrators' | 'agents' | 'integrations' | 'skills' | 'memory' | 'control' | 'monitor' | 'sync';
/**
 * Navigation par espaces (étape 1) : 11 pages deviennent 4 espaces.
 *
 * - **Travailler** : Espace de travail + Poste de pilotage (deux vues du même objet).
 * - **Missions** : Projets & missions.
 * - **Capacités** : Orchestrateurs, Modèles, Connexions, Compétences (onglets).
 * - **Système** : Mémoire, Centre de contrôle, Supervision, Synchronisation (onglets).
 *
 * Aucune adresse ne change : chaque page garde sa route et ses liens. Seule la
 * barre est regroupée, et les pages d'un même espace deviennent des onglets.
 *
 * La page « Agents & outils » est un onglet de l'espace Capacités : elle
 * regroupe les agents d'orchestration et le rattachement de compétences
 * (sélecteur avec recherche, filtres, compétences héritées). La route /catalog
 * redirige vers /orchestrators pour ne casser aucun lien existant.
 * Intitulés en français uniquement : plus de mélange FR/EN dans la barre.
 */
const pages = [
  { id: 'workbench' as const, path: '/workbench', label: 'Espace de travail', icon: LayoutDashboard },
  { id: 'cockpit' as const, path: '/cockpit', label: 'Conversation', icon: Gauge },
  { id: 'projects' as const, path: '/projects', label: 'Projets & missions', icon: FolderKanban },
  { id: 'orchestrators' as const, path: '/orchestrators', label: 'Orchestrateurs', icon: Network },
  { id: 'agents' as const, path: '/agents', label: 'Agents & outils', icon: Users },
  { id: 'models' as const, path: '/models', label: 'Modèles', icon: Cpu },
  { id: 'integrations' as const, path: '/integrations', label: 'Connexions', icon: Plug },
  { id: 'skills' as const, path: '/skills', label: 'Compétences', icon: Sparkles },
  { id: 'memory' as const, path: '/memory', label: 'Mémoire & connaissance', icon: Database },
  { id: 'control' as const, path: '/control', label: 'Centre de contrôle', icon: Bot },
  { id: 'monitor' as const, path: '/monitor', label: 'Supervision', icon: Activity },
  { id: 'sync' as const, path: '/sync', label: 'Synchronisation', icon: Cloud },
];

type NavGroup = {
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  pages: PageId[];
};

/** Les 4 espaces de travail. L'ordre suit le parcours réel : travailler, organiser, brancher, surveiller. */
const groups: NavGroup[] = [
  { id: 'work', label: 'Travailler', icon: LayoutDashboard, pages: ['workbench', 'cockpit'] },
  { id: 'missions', label: 'Missions', icon: FolderKanban, pages: ['projects'] },
  { id: 'capabilities', label: 'Capacités', icon: Network, pages: ['orchestrators', 'agents', 'models', 'integrations', 'skills'] },
  { id: 'system', label: 'Système', icon: Activity, pages: ['memory', 'control', 'monitor', 'sync'] },
];

const pageById = (id: PageId) => pages.find((page) => page.id === id)!;

const CONVERSATION_PAGE_IDS: PageId[] = ['cockpit', 'workbench', 'control'];

const workspace = (id: PageId, node: ReactNode) => (
  <div className="hz-view" data-horizon-workspace={id}>{node}</div>
);

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId } = useChatSession();
  // Dernière page visitée dans chaque espace : revenir sur un espace ramène là où
  // l'on travaillait, au lieu de forcer la première page.
  const lastVisited = useRef<Partial<Record<string, PageId>>>({});

  const active = pages.find((page) => location.pathname.startsWith(page.path)) ?? pages[0];
  const activeGroup = groups.find((group) => group.pages.includes(active.id)) ?? groups[0];

  // Mémorise la page réellement affichée, y compris quand on arrive par un lien direct.
  useEffect(() => {
    lastVisited.current[activeGroup.id] = active.id;
  }, [active.id, activeGroup.id]);

  const goTo = (pageId: PageId) => {
    const page = pageById(pageId);
    const target = CONVERSATION_PAGE_IDS.includes(page.id) && sessionId
      ? `${page.path}/${sessionId}`
      : page.path;
    navigate(target);
  };

  return (
    <div className="horizon-integration">
      <nav className="horizon-nav" aria-label="Espaces HORIZON">
        <div className="horizon-brand">
          <span className="horizon-mark" aria-hidden="true">H</span>
          <span className="horizon-brand-text">
            <strong>HORIZON</strong>
            <small>CENTRAL AI</small>
          </span>
        </div>
        <div className="horizon-tabs">
          {groups.map((group) => {
            const Icon = group.icon;
            const isActive = activeGroup.id === group.id;
            return (
              <button
                key={group.id}
                type="button"
                className={isActive ? 'active' : ''}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => {
                  const target = lastVisited.current[group.id] ?? group.pages[0];
                  goTo(target);
                }}
              >
                <Icon size={15} />
                <span>{group.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
      {activeGroup.pages.length > 1 && (
        <nav className="horizon-subnav" aria-label={`Sections de ${activeGroup.label}`}>
          {activeGroup.pages.map((pageId) => {
            const page = pageById(pageId);
            const isActive = active.id === page.id;
            return (
              <button
                key={page.id}
                type="button"
                className={isActive ? 'active' : ''}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => {
                  lastVisited.current[activeGroup.id] = page.id;
                  goTo(page.id);
                }}
              >
                {page.label}
              </button>
            );
          })}
        </nav>
      )}
      <main className="horizon-page" id="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/workbench" replace />} />
          <Route path="/cockpit" element={workspace('cockpit', <Cockpit />)} />
          <Route path="/cockpit/:sessionId" element={workspace('cockpit', <Cockpit />)} />
          <Route path="/workbench" element={workspace('workbench', <MainWorkbench />)} />
          <Route path="/workbench/:sessionId" element={workspace('workbench', <MainWorkbench />)} />
          <Route path="/projects" element={workspace('projects', <Projects />)} />
          <Route path="/models" element={workspace('models', <ModelManagerLive />)} />
          <Route path="/orchestrators" element={workspace('orchestrators', <OrchestratorRegistry />)} />
        <Route path="/agents" element={workspace('agents', <AgentsToolsCatalog />)} />
          {/* Ancienne page « Agents & Tools » : doublon d'Orchestrateurs + Connexions. */}
          <Route path="/catalog" element={<Navigate to="/orchestrators" replace />} />
          <Route path="/integrations" element={workspace('integrations', <Integrations />)} />
          <Route path="/skills" element={workspace('skills', <SkillsLibrary />)} />
          <Route path="/memory" element={workspace('memory', <KnowledgeMemoryLive />)} />
          <Route path="/control" element={workspace('control', <AIControlCenter />)} />
          <Route path="/control/:sessionId" element={workspace('control', <AIControlCenter />)} />
          <Route path="/monitor" element={workspace('monitor', <SystemMonitorLive />)} />
          <Route path="/sync" element={workspace('sync', <SyncCenter />)} />
          <Route path="*" element={<Navigate to="/workbench" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BackendUnavailable>
      <BrowserRouter>
        <ConnectionsProvider>
          <ChatSessionProvider>
            <AppShell />
          </ChatSessionProvider>
        </ConnectionsProvider>
      </BrowserRouter>
    </BackendUnavailable>
  );
}
