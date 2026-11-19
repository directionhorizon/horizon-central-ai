import { useMemo, useState } from 'react';
import { ArrowUpRight, BarChart3, Check, ChevronDown, Cloud, Database, FileCode2, FileText, Folder, FolderPlus, HardDrive, MoreHorizontal, Network, RefreshCw, Search, SlidersHorizontal, Sparkles, Upload } from 'lucide-react';
type Tab = 'Local Index' | 'Cloud Sync';
interface DocumentRecord {
  id: string;
  name: string;
  type: string;
  project: string;
  date: string;
  icon: 'code' | 'text' | 'folder';
  size: string;
}
const DOCUMENTS: DocumentRecord[] = [{
  id: 'horizon-core',
  name: 'horizon-core.config.ts',
  type: 'TypeScript',
  project: 'Horizon Core',
  date: 'Today, 09:42',
  icon: 'code',
  size: '18 KB'
}, {
  id: 'rag-architecture',
  name: 'rag-architecture.md',
  type: 'Markdown',
  project: 'Architecture v2',
  date: 'Today, 08:17',
  icon: 'text',
  size: '42 KB'
}, {
  id: 'agent-manifest',
  name: 'agent-manifest.json',
  type: 'JSON',
  project: 'Agent Runtime',
  date: 'Yesterday, 16:03',
  icon: 'code',
  size: '7 KB'
}, {
  id: 'research-notes',
  name: 'research-notes',
  type: 'Folder',
  project: 'Unassigned',
  date: 'Yesterday, 11:28',
  icon: 'folder',
  size: '128 items'
}, {
  id: 'prompt-library',
  name: 'prompt-library.md',
  type: 'Markdown',
  project: 'Horizon Core',
  date: '12 Jun 2025',
  icon: 'text',
  size: '86 KB'
}];
const GRAPH_POINTS = [{
  x: 12,
  y: 74,
  label: 'Design'
}, {
  x: 26,
  y: 45,
  label: 'Runtime'
}, {
  x: 41,
  y: 64,
  label: 'Agents'
}, {
  x: 56,
  y: 28,
  label: 'Models'
}, {
  x: 70,
  y: 48,
  label: 'Projects'
}, {
  x: 84,
  y: 20,
  label: 'Notes'
}];
export const KnowledgeMemoryHub = () => {
  const [activeTab, setActiveTab] = useState<Tab>('Local Index');
  const [query, setQuery] = useState('');
  const [isSyncEnabled, setIsSyncEnabled] = useState(true);
  const [isIndexing, setIsIndexing] = useState(false);
  const filteredDocuments = useMemo(() => DOCUMENTS.filter(document => `${document.name} ${document.type} ${document.project}`.toLowerCase().includes(query.toLowerCase())), [query]);
  return <div className="min-h-screen bg-[#0a0b10] text-slate-100">
      <div className="mx-auto min-h-screen w-full max-w-[1500px] px-5 pb-12 pt-8 sm:px-8">
        <div className="mx-auto max-w-[1440px]">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
            <div>
              <div className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.22em] text-cyan-400">
                <Database size={14} /><span>Knowledge system</span>
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-white">Knowledge &amp; Memory Hub</h1>
              <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">Your local context, indexed and ready for retrieval. Keep Horizon close to the work that matters.</p>
            </div>
            <button type="button" onClick={() => {
            setIsIndexing(true);
            window.setTimeout(() => setIsIndexing(false), 1200);
          }} className="flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-[#071017] shadow-lg shadow-cyan-400/10 transition hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-cyan-300 focus:ring-offset-2 focus:ring-offset-[#0a0b10]">
              {isIndexing ? <RefreshCw size={16} className="animate-spin" /> : <FolderPlus size={16} />}
              <span>{isIndexing ? 'Indexing…' : 'Index New Folder / File'}</span>
            </button>
          </div>

          <nav className="mb-6 flex items-center gap-7 border-b border-white/10" aria-label="Knowledge hub sections">
            {(['Local Index', 'Cloud Sync'] as Tab[]).map(tab => <button key={tab} type="button" onClick={() => setActiveTab(tab)} className={`relative pb-3 text-sm font-semibold transition ${activeTab === tab ? 'text-cyan-300' : 'text-slate-500 hover:text-slate-200'}`}>
                <span>{tab}</span>
                {activeTab === tab && <span className="absolute inset-x-0 -bottom-px h-0.5 bg-cyan-400" />}
              </button>)}
          </nav>

          {activeTab === 'Local Index' ? <div className="space-y-6">
              <section className="grid gap-5 lg:grid-cols-[1.45fr_1fr]" aria-label="Memory overview">
                <article className="relative overflow-hidden rounded-xl border border-cyan-400/15 bg-[#11151f] p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400"><Network size={15} className="text-cyan-400" /><span>Memory graph</span></div>
                      <p className="mt-4 text-3xl font-semibold text-white">2.84 <span className="text-base font-normal text-slate-500">GB</span></p>
                      <p className="mt-1 text-sm text-slate-400">of context stored locally</p>
                    </div>
                    <div className="flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-bold text-emerald-300"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300" /><span>Healthy</span></div>
                  </div>
                  <div className="mt-7 h-28 w-full" aria-label="Stored context volume graph" role="img">
                    <svg className="h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                      <defs><linearGradient id="memoryFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#00d1ff" stopOpacity=".32" /><stop offset="1" stopColor="#00d1ff" stopOpacity="0" /></linearGradient></defs>
                      <path d="M 0 88 C 10 82, 14 78, 22 79 S 33 54, 41 63 S 53 38, 61 43 S 72 49, 81 29 S 92 21, 100 12 L 100 100 L 0 100 Z" fill="url(#memoryFill)" />
                      <path d="M 0 88 C 10 82, 14 78, 22 79 S 33 54, 41 63 S 53 38, 61 43 S 72 49, 81 29 S 92 21, 100 12" fill="none" stroke="#20d6ff" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                      {GRAPH_POINTS.map(point => <circle key={point.label} cx={point.x} cy={point.y} r="1.7" fill="#0a0b10" stroke="#7be8ff" strokeWidth="1" vectorEffect="non-scaling-stroke" />)}
                    </svg>
                  </div>
                  <div className="mt-2 flex justify-between text-[11px] text-slate-600"><span>01 Jun</span><span>08 Jun</span><span>15 Jun</span><span>Today</span></div>
                </article>
                <article className="rounded-xl border border-white/10 bg-[#11151f] p-6">
                  <div className="flex items-center justify-between"><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400"><BarChart3 size={15} className="text-cyan-400" /><span>Index health</span></div><button type="button" aria-label="Index health options" className="text-slate-600 hover:text-white"><MoreHorizontal size={18} /></button></div>
                  <div className="mt-6 flex items-center gap-5"><div className="relative flex h-24 w-24 items-center justify-center rounded-full" style={{
                  background: 'conic-gradient(#00d1ff 0 82%, #263244 82% 100%)'
                }}><div className="flex h-[78px] w-[78px] items-center justify-center rounded-full bg-[#11151f] text-xl font-semibold text-white">82%</div></div><div><p className="text-sm font-semibold text-white">Fully indexed</p><p className="mt-1 text-xs leading-5 text-slate-500">1,248 files across<br />6 active projects</p></div></div>
                  <div className="mt-6 grid grid-cols-2 gap-3 border-t border-white/10 pt-4"><div><p className="text-lg font-semibold text-white">18.4k</p><p className="text-xs text-slate-500">Stored chunks</p></div><div><p className="text-lg font-semibold text-white">42 ms</p><p className="text-xs text-slate-500">Avg. retrieval</p></div></div>
                </article>
              </section>

              <section className="rounded-xl border border-white/10 bg-[#11151f]" aria-labelledby="indexed-documents-heading">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 p-5"><div><h2 id="indexed-documents-heading" className="text-base font-semibold text-white">Indexed documents</h2><p className="mt-1 text-xs text-slate-500">The local sources available to your context engine.</p></div><div className="flex items-center gap-2"><div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" /><input value={query} onChange={event => setQuery(event.target.value)} aria-label="Search internal knowledge base" placeholder="Search internal knowledge base" className="w-64 rounded-lg border border-white/10 bg-white/[0.03] py-2 pl-9 pr-3 text-xs text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/30" /></div><button type="button" aria-label="Filter indexed documents" className="rounded-lg border border-white/10 p-2 text-slate-400 hover:border-white/20 hover:text-white"><SlidersHorizontal size={16} /></button></div></div>
                <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left"><thead><tr className="border-b border-white/5 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-600"><th className="px-5 py-3">Filename</th><th className="px-5 py-3">Type</th><th className="px-5 py-3">Project association</th><th className="px-5 py-3">Indexed</th><th className="px-5 py-3 text-right">Size</th><th className="px-5 py-3" /></tr></thead><tbody>{filteredDocuments.map(document => <tr key={document.id} className="border-b border-white/5 transition last:border-0 hover:bg-white/[0.025]"><td className="px-5 py-4"><div className="flex items-center gap-3">{document.icon === 'code' ? <FileCode2 size={17} className="text-cyan-400" /> : document.icon === 'folder' ? <Folder size={17} className="text-amber-300" /> : <FileText size={17} className="text-slate-400" />}<span className="text-sm font-medium text-slate-200">{document.name}</span></div></td><td className="px-5 py-4 text-xs text-slate-400">{document.type}</td><td className="px-5 py-4"><span className="rounded-md bg-white/5 px-2 py-1 text-xs text-slate-300">{document.project}</span></td><td className="px-5 py-4 text-xs text-slate-400">{document.date}</td><td className="px-5 py-4 text-right font-mono text-xs text-slate-500">{document.size}</td><td className="px-5 py-4 text-right"><button type="button" aria-label={`Open ${document.name}`} className="text-slate-600 hover:text-cyan-300"><ArrowUpRight size={16} /></button></td></tr>)}</tbody></table>{filteredDocuments.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No indexed sources match your search.</p>}</div>
              </section>
            </div> : <section className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
              <article className="rounded-xl border border-white/10 bg-[#11151f] p-7"><div className="flex items-start justify-between"><div><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400"><Cloud size={15} className="text-cyan-400" /><span>Planned source</span></div><h2 className="mt-4 text-2xl font-semibold text-white">Google Drive</h2><p className="mt-2 text-sm text-slate-400">Google Drive integration is planned; no account is connected in this prototype.</p></div><div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-lg font-bold text-white">G</div></div><div className="mt-8 flex items-center justify-between border-t border-white/10 pt-5"><div><p className="text-sm font-semibold text-white">Sync preview control</p><p className="mt-1 text-xs text-slate-500">Visual toggle only · no synchronization is running</p></div><button type="button" role="switch" aria-checked={isSyncEnabled} onClick={() => setIsSyncEnabled(!isSyncEnabled)} className={`flex h-7 w-12 items-center rounded-full p-1 transition ${isSyncEnabled ? 'justify-end bg-cyan-400' : 'justify-start bg-slate-700'}`}><span className="h-5 w-5 rounded-full bg-white shadow" /></button></div></article>
              <article className="rounded-xl border border-white/10 bg-[#11151f] p-7"><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400"><HardDrive size={15} className="text-cyan-400" /><span>Sync activity</span></div><div className="mt-7 space-y-5"><div className="flex items-center gap-3"><div className="rounded-full bg-emerald-400/10 p-2 text-emerald-300"><Check size={15} /></div><div><p className="text-sm text-white">Drive connection verified</p><p className="text-xs text-slate-500">Today, 09:38</p></div></div><div className="flex items-center gap-3"><div className="rounded-full bg-cyan-400/10 p-2 text-cyan-300"><Upload size={15} /></div><div><p className="text-sm text-white">24 files added to index</p><p className="text-xs text-slate-500">Today, 09:35</p></div></div></div><button type="button" className="mt-7 flex items-center gap-2 text-xs font-bold text-cyan-300 hover:text-cyan-200"><span>Manage synced folders</span><ChevronDown size={14} /></button></article>
            </section>}
          <div className="mt-6 flex items-center gap-2 text-xs text-slate-600"><Sparkles size={14} className="text-cyan-500/70" /><span>Context engine ready · local-first processing enabled</span></div>
        </div>
      </div>
    </div>;
};