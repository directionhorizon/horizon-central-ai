import { useState, type FormEvent } from 'react';
import { Activity, ArrowUpRight, Check, ChevronDown, CircleAlert, Cloud, Cpu, Gauge, Globe2, HardDrive, KeyRound, Layers3, Plus, RefreshCw, Server, SlidersHorizontal, Sparkles, Zap } from 'lucide-react';
type ProviderStatus = 'Not verified';
type Provider = {
  id: string;
  name: string;
  description: string;
  status: ProviderStatus;
  model: string;
  latency: string;
  icon: typeof Server;
  accent: string;
};
type Endpoint = {
  id: string;
  name: string;
  url: string;
};
const PROVIDERS: Provider[] = [{
  id: 'local',
  name: 'Local Runtime',
  description: 'On-device inference via Ollama',
  status: 'Not verified',
  model: 'Llama 3 70B Instruct',
  latency: '42 ms',
  icon: Cpu,
  accent: 'cyan'
}, {
  id: 'openai',
  name: 'OpenAI',
  description: 'Production cloud endpoint',
  status: 'Not verified',
  model: 'GPT-4o',
  latency: '318 ms',
  icon: Cloud,
  accent: 'emerald'
}, {
  id: 'anthropic',
  name: 'Anthropic',
  description: 'Reasoning and long-context models',
  status: 'Not verified',
  model: 'Claude 3.5 Sonnet',
  latency: '—',
  icon: Sparkles,
  accent: 'violet'
}];
const USAGE_POINTS = [{
  label: '10:00',
  value: 38
}, {
  label: '10:10',
  value: 52
}, {
  label: '10:20',
  value: 45
}, {
  label: '10:30',
  value: 70
}, {
  label: '10:40',
  value: 61
}, {
  label: '10:50',
  value: 84
}, {
  label: '11:00',
  value: 76
}, {
  label: '11:10',
  value: 91
}];
const RESOURCE_STATS = [{
  label: 'CPU load',
  value: '34%',
  detail: '8 / 24 cores',
  icon: Cpu,
  color: 'text-cyan-300',
  bar: '34%'
}, {
  label: 'GPU memory',
  value: '71%',
  detail: '22.7 / 32 GB',
  icon: Gauge,
  color: 'text-violet-300',
  bar: '71%'
}, {
  label: 'Active context',
  value: '12.4k',
  detail: 'tokens in flight',
  icon: Layers3,
  color: 'text-emerald-300',
  bar: '52%'
}];
export const ModelManager = () => {
  const [mode, setMode] = useState<'Automatic' | 'Manual'>('Automatic');
  const [selectedProvider, setSelectedProvider] = useState('local');
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointName, setEndpointName] = useState('');
  const [endpointUrl, setEndpointUrl] = useState('');
  const [showForm, setShowForm] = useState(false);
  function addEndpoint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!endpointName.trim() || !endpointUrl.trim()) return;
    setEndpoints(current => [...current, {
      id: `${endpointName}-${endpointUrl}`,
      name: endpointName,
      url: endpointUrl
    }]);
    setEndpointName('');
    setEndpointUrl('');
    setShowForm(false);
  }
  return <div className="min-h-screen bg-[#0a0b10] text-slate-100">
      <div className="mx-auto min-h-screen w-full max-w-[1500px] px-5 pb-12 pt-8 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-[1440px]">
          <header className="mb-8 flex flex-col justify-between gap-5 border-b border-white/[0.07] pb-7 xl:flex-row xl:items-end">
            <div>
              <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-400">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_12px_#00d1ff]" />
                <span>Infrastructure / Runtime</span>
              </div>
              <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">Model Manager</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Configure your intelligence layer, monitor inference health, and keep every model path ready for work.</p>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-3 py-2 text-emerald-300"><Activity size={13} /> <span>Connections not verified</span></span>
              <button className="rounded-lg border border-white/10 p-2.5 text-slate-400 transition hover:border-cyan-400/40 hover:text-cyan-300" aria-label="Refresh metrics"><RefreshCw size={15} /></button>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(430px,0.92fr)]">
            <section aria-labelledby="providers-heading" className="glass-effect rounded-2xl p-5 sm:p-6">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">01 / Routing layer</p>
                  <h2 id="providers-heading" className="text-xl font-semibold tracking-tight text-white">Model Providers</h2>
                  <p className="mt-1 text-sm text-slate-400">Example providers · endpoints are not connected</p>
                </div>
                <button onClick={() => setShowForm(current => !current)} className="flex items-center gap-2 rounded-lg bg-cyan-400 px-3 py-2.5 text-xs font-bold text-[#071017] shadow-lg shadow-cyan-400/10 transition hover:bg-cyan-300"><Plus size={15} /> <span>Add endpoint</span></button>
              </div>

              <div className="mb-5 rounded-xl border border-white/[0.07] bg-black/10 p-1.5">
                <div className="flex items-center justify-between px-3 py-2">
                  <div className="flex items-center gap-2"><SlidersHorizontal size={15} className="text-cyan-400" /><span className="text-sm font-medium text-slate-200">Model selection</span></div>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500">Routing policy</span>
                </div>
                <div className="grid grid-cols-2 gap-1">
                  <button onClick={() => setMode('Automatic')} className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold transition ${mode === 'Automatic' ? 'bg-cyan-400 text-[#071017]' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}><Sparkles size={14} /> <span>Automatic</span></button>
                  <button onClick={() => setMode('Manual')} className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold transition ${mode === 'Manual' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}><SlidersHorizontal size={14} /> <span>Manual overrides</span></button>
                </div>
              </div>

              <div className="space-y-2">
                {PROVIDERS.map(provider => {
                const Icon = provider.icon;
                const isSelected = selectedProvider === provider.id;
                return <button key={provider.id} onClick={() => setSelectedProvider(provider.id)} className={`group flex w-full items-center gap-4 rounded-xl border p-4 text-left transition ${isSelected && mode === 'Manual' ? 'border-cyan-400/50 bg-cyan-400/[0.07]' : 'border-white/[0.06] bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]'}`}>
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${provider.accent === 'cyan' ? 'border-cyan-400/20 bg-cyan-400/10 text-cyan-300' : provider.accent === 'emerald' ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300' : 'border-violet-400/20 bg-violet-400/10 text-violet-300'}`}><Icon size={19} /></span>
                    <span className="min-w-0 flex-1"><span className="flex items-center gap-2"><strong className="text-sm font-semibold text-slate-100">{provider.name}</strong><span className={`h-1.5 w-1.5 rounded-full ${provider.status === 'Not verified' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-slate-600'}`} /><span className={`text-[10px] font-semibold uppercase tracking-wider ${provider.status === 'Not verified' ? 'text-emerald-300' : 'text-slate-500'}`}>{provider.status}</span></span><span className="mt-1 block truncate text-xs text-slate-500">{provider.description}</span></span>
                    <span className="hidden text-right sm:block"><span className="block text-xs font-medium text-slate-300">{provider.model}</span><span className="mt-1 block text-[10px] text-slate-500">{provider.latency} latency</span></span>
                    {isSelected && mode === 'Manual' ? <Check size={16} className="text-cyan-300" /> : <ArrowUpRight size={15} className="text-slate-600 transition group-hover:text-cyan-300" />}
                  </button>;
              })}
                {endpoints.map(endpoint => <div key={endpoint.id} className="flex items-center gap-4 rounded-xl border border-dashed border-cyan-400/30 bg-cyan-400/[0.04] p-4"><span className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300"><Globe2 size={18} /></span><span className="min-w-0 flex-1"><strong className="block text-sm font-semibold text-slate-100">{endpoint.name}</strong><span className="mt-1 block truncate text-xs text-slate-500">{endpoint.url}</span></span><span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300">Configured</span></div>)}
              </div>

              {showForm && <form onSubmit={addEndpoint} className="mt-5 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.04] p-4"><div className="mb-4 flex items-center justify-between"><div><h3 className="text-sm font-semibold text-white">Add API-compatible endpoint</h3><p className="mt-1 text-xs text-slate-500">Connect an OpenAI-compatible gateway or local runtime.</p></div><KeyRound size={17} className="text-cyan-300" /></div><div className="grid gap-3 sm:grid-cols-2"><label className="text-xs text-slate-400"><span className="mb-1.5 block">Endpoint name</span><input value={endpointName} onChange={event => setEndpointName(event.target.value)} placeholder="e.g. Team Gateway" className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white placeholder:text-slate-600 outline-none transition focus:border-cyan-400/60" /></label><label className="text-xs text-slate-400"><span className="mb-1.5 block">Base URL</span><input value={endpointUrl} onChange={event => setEndpointUrl(event.target.value)} placeholder="https://api.example.com/v1" className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white placeholder:text-slate-600 outline-none transition focus:border-cyan-400/60" /></label></div><div className="mt-4 flex justify-end gap-2"><button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-2 text-xs font-semibold text-slate-400 hover:text-white">Cancel</button><button type="submit" className="rounded-lg bg-cyan-400 px-4 py-2 text-xs font-bold text-[#071017] hover:bg-cyan-300">Save endpoint</button></div></form>}
            </section>

            <section aria-labelledby="performance-heading" className="space-y-6">
              <div className="glass-effect rounded-2xl p-5 sm:p-6">
                <div className="mb-6 flex items-start justify-between"><div><p className="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">02 / Example telemetry</p><h2 id="performance-heading" className="text-xl font-semibold tracking-tight text-white">Performance Monitor</h2><p className="mt-1 text-sm text-slate-400">Illustrative sample · no live metrics connected</p></div><span className="flex items-center gap-1.5 rounded-md border border-cyan-400/15 bg-cyan-400/[0.06] px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-cyan-300"><Zap size={11} /> Sample</span></div>
                <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4"><div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"><span className="block text-[10px] uppercase tracking-wider text-slate-500">Tokens / min</span><strong className="mt-1 block text-lg text-white">8,420</strong><span className="text-[10px] text-emerald-300">↑ 12.4%</span></div><div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"><span className="block text-[10px] uppercase tracking-wider text-slate-500">Avg latency</span><strong className="mt-1 block text-lg text-white">184<span className="text-xs text-slate-500">ms</span></strong><span className="text-[10px] text-emerald-300">↓ 8.1%</span></div><div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"><span className="block text-[10px] uppercase tracking-wider text-slate-500">Requests</span><strong className="mt-1 block text-lg text-white">1,284</strong><span className="text-[10px] text-slate-500">this hour</span></div><div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"><span className="block text-[10px] uppercase tracking-wider text-slate-500">Error rate</span><strong className="mt-1 block text-lg text-white">0.08<span className="text-xs text-slate-500">%</span></strong><span className="text-[10px] text-emerald-300">Healthy</span></div></div>
                <div className="rounded-xl border border-white/[0.06] bg-black/10 p-4"><div className="mb-4 flex items-center justify-between"><span className="text-xs font-medium text-slate-300">Token throughput</span><span className="text-[10px] text-slate-500">tokens / min</span></div><div className="flex h-32 items-end gap-2 border-b border-white/[0.07] px-1">{USAGE_POINTS.map(point => <div key={point.label} className="group flex h-full flex-1 flex-col justify-end gap-2"><div className="relative w-full rounded-t-sm bg-cyan-400/70 transition hover:bg-cyan-300" style={{
                      height: `${point.value}%`
                    }}><span className="pointer-events-none absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] text-cyan-200 opacity-0 transition group-hover:opacity-100">{point.value * 100}</span></div></div>)}</div><div className="mt-2 flex justify-between text-[10px] text-slate-600"><span>10:00</span><span>10:20</span><span>10:40</span><span>11:10</span></div></div>
              </div>

              <div className="glass-effect rounded-2xl p-5 sm:p-6"><div className="mb-5 flex items-center justify-between"><div><h3 className="text-sm font-semibold text-white">Local resource consumption</h3><p className="mt-1 text-xs text-slate-500">Runtime node · horizon-node-01</p></div><HardDrive size={17} className="text-slate-500" /></div><div className="space-y-5">{RESOURCE_STATS.map(stat => {
                  const Icon = stat.icon;
                  return <div key={stat.label} className="grid grid-cols-[minmax(120px,0.7fr)_1fr_auto] items-center gap-4"><div className="flex items-center gap-2.5"><Icon size={15} className={stat.color} /><span className="text-xs text-slate-300">{stat.label}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/[0.08]"><div className={`h-full rounded-full ${stat.color.replace('text-', 'bg-')}`} style={{
                        width: stat.bar
                      }} /></div><div className="text-right"><strong className="block text-xs text-white">{stat.value}</strong><span className="block text-[10px] text-slate-600">{stat.detail}</span></div></div>;
                })}</div><div className="mt-6 flex items-center gap-2 border-t border-white/[0.06] pt-4 text-[11px] text-slate-500"><CircleAlert size={13} className="text-slate-600" /><span>GPU headroom is healthy for one additional 13B model.</span></div></div>
            </section>
          </div>
        </div>
      </div>
    </div>;
};