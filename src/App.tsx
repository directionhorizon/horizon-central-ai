import { type ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Cpu, Network, Database, Bot, Activity, FolderKanban, Cloud, Gauge, Plug, Sparkles } from 'lucide-react';
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
import { Cockpit } from './pages/cockpit/Cockpit';
import { ChatSessionProvider, useChatSession } from './shared/ChatSessionContext';
import { ConnectionsProvider } from './shared/ConnectionsContext';

type PageId = 'cockpit' | 'workbench' | 'projects' | 'models' | 'orchestrators' | 'integrations' | 'skills' | 'memory' | 'control' | 'monitor' | 'sync';
/**
 * Ordre de navigation = ordre de travail réel :
 * 1. on travaille (Espace de travail), 2. on pilote (Poste de pilotage),
 * 3. on organise (Projets & missions), 4. on branche (Orchestrateurs, Modèles,
 * Connexions), 5. on consulte (Mémoire, Centre de contrôle, Supervision, Sync).
 *
 * La page « Agents & Tools » a été retirée de la barre : elle doublonnait
 * Orchestrateurs (agents) et Connexions (services). La route /catalog redirige
 * vers /orchestrators pour ne casser aucun lien existant.
 * Intitulés en français uniquement : plus de mélange FR/EN dans la barre.
 */
const pages = [
  { id: 'workbench' as const, path: '/workbench', label: 'Espace de travail', icon: LayoutDashboard },
  { id: 'cockpit' as const, path: '/cockpit', label: 'Poste de pilotage', icon: Gauge },
  { id: 'projects' as const, path: '/projects', label: 'Projets & missions', icon: FolderKanban },
  { id: 'orchestrators' as const, path: '/orchestrators', label: 'Orchestrateurs', icon: Network },
  { id: 'models' as const, path: '/models', label: 'Modèles', icon: Cpu },
  { id: 'integrations' as const, path: '/integrations', label: 'Connexions', icon: Plug },
  { id: 'skills' as const, path: '/skills', label: 'Compétences', icon: Sparkles },
  { id: 'memory' as const, path: '/memory', label: 'Mémoire & connaissance', icon: Database },
  { id: 'control' as const, path: '/control', label: 'Centre de contrôle', icon: Bot },
  { id: 'monitor' as const, path: '/monitor', label: 'Supervision', icon: Activity },
  { id: 'sync' as const, path: '/sync', label: 'Synchronisation', icon: Cloud },
];

const CONVERSATION_PAGE_IDS: PageId[] = ['cockpit', 'workbench', 'control'];

const workspace = (id: PageId, node: ReactNode) => (
  <div className="hz-view" data-horizon-workspace={id}>{node}</div>
);

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId } = useChatSession();

  const active = pages.find((page) => location.pathname.startsWith(page.path)) ?? pages[0];

  return (
    <div className="horizon-integration">
      <nav className="horizon-nav" aria-label="HORIZON workspaces">
        <div className="horizon-brand">
          <span className="horizon-mark" aria-hidden="true">H</span>
          <span className="horizon-brand-text">
            <strong>HORIZON</strong>
            <small>CENTRAL AI</small>
          </span>
        </div>
        <div className="horizon-tabs">
          {pages.map((page) => {
            const Icon = page.icon;
            const isActive = active.id === page.id;
            return (
              <button
                key={page.id}
                type="button"
                className={isActive ? 'active' : ''}
                onClick={() => {
                  const target = CONVERSATION_PAGE_IDS.includes(page.id) && sessionId
                    ? `${page.path}/${sessionId}`
                    : page.path;
                  navigate(target);
                }}
              >
                <Icon size={15} />
                <span>{page.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
      <div className="horizon-page">
        <Routes>
          <Route path="/" element={<Navigate to="/workbench" replace />} />
          <Route path="/cockpit" element={workspace('cockpit', <Cockpit />)} />
          <Route path="/cockpit/:sessionId" element={workspace('cockpit', <Cockpit />)} />
          <Route path="/workbench" element={workspace('workbench', <MainWorkbench />)} />
          <Route path="/workbench/:sessionId" element={workspace('workbench', <MainWorkbench />)} />
          <Route path="/projects" element={workspace('projects', <Projects />)} />
          <Route path="/models" element={workspace('models', <ModelManagerLive />)} />
          <Route path="/orchestrators" element={workspace('orchestrators', <OrchestratorRegistry />)} />
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
      </div>
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
