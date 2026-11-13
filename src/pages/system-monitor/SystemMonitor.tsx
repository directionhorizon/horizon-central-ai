import React, { useMemo, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, CircleHelp, Cloud, Cpu, HardDrive, Laptop, Network, RefreshCw, Server, Shield, Wifi, XCircle } from "lucide-react";
type NodeStatus = "Online" | "Offline" | "Attention";
const initialNodes = [{
  id: "pc-main",
  name: "HORIZON Main PC",
  role: "Primary Windows workstation",
  status: "Offline" as NodeStatus,
  detail: "No heartbeat received",
  address: "Local agent · not connected",
  icon: Laptop,
  last: "Awaiting connection"
}, {
  id: "cloud",
  name: "Cloud services",
  role: "Remote infrastructure",
  status: "Attention" as NodeStatus,
  detail: "Connection not verified",
  address: "Provider connectors pending",
  icon: Cloud,
  last: "Not checked"
}, {
  id: "api",
  name: "HORIZON API",
  role: "Central application backend",
  status: "Offline" as NodeStatus,
  detail: "Backend not deployed",
  address: "FastAPI · PostgreSQL",
  icon: Server,
  last: "Not deployed"
}];
export const SystemMonitor = () => {
  const [nodes, setNodes] = useState(initialNodes);
  const [filter, setFilter] = useState("All");
  const [expanded, setExpanded] = useState("pc-main");
  const visible = useMemo(() => filter === "All" ? nodes : nodes.filter(n => n.status === filter), [nodes, filter]);
  const refresh = () => setNodes(current => current.map(n => ({
    ...n,
    detail: n.status === "Offline" ? "Still awaiting a live heartbeat" : n.status === "Attention" ? "Verification required" : "Status unchanged"
  })));
  const counts = {
    online: nodes.filter(n => n.status === "Online").length,
    attention: nodes.filter(n => n.status === "Attention").length,
    offline: nodes.filter(n => n.status === "Offline").length
  };
  return <div className="min-h-screen bg-[#090c13] text-slate-100">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-6 py-5">
      <div><p className="text-[11px] font-semibold uppercase tracking-[.18em] text-cyan-300">HORIZON / OPERATIONS</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">System Monitor</h1><p className="mt-1 text-sm text-slate-500">Infrastructure, devices and service connectivity</p></div>
      <button onClick={refresh} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5"><RefreshCw size={14} /> Refresh status</button>
    </header>
    <main className="mx-auto max-w-[1400px] space-y-6 p-5 sm:p-7">
      <div className="flex items-start gap-3 rounded-xl border border-amber-300/20 bg-amber-300/[0.06] p-4"><AlertTriangle className="mt-0.5 shrink-0 text-amber-300" size={18} /><div><p className="text-sm font-medium text-amber-100">Monitoring is not connected yet</p><p className="mt-1 text-xs leading-5 text-slate-400">These are initial configuration states, not live measurements. Device agents, health checks and backend telemetry must be connected before this page can report real status.</p></div></div>
      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center justify-between text-xs text-slate-400"><span>Online</span><CheckCircle2 size={16} className="text-emerald-300" /></div><p className="mt-3 text-3xl font-semibold tabular-nums">{counts.online}</p><p className="mt-1 text-[11px] text-slate-600">Connected nodes</p></div>
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center justify-between text-xs text-slate-400"><span>Attention</span><AlertTriangle size={16} className="text-amber-300" /></div><p className="mt-3 text-3xl font-semibold tabular-nums">{counts.attention}</p><p className="mt-1 text-[11px] text-slate-600">Require verification</p></div>
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center justify-between text-xs text-slate-400"><span>Offline</span><XCircle size={16} className="text-rose-300" /></div><p className="mt-3 text-3xl font-semibold tabular-nums">{counts.offline}</p><p className="mt-1 text-[11px] text-slate-600">No active heartbeat</p></div>
      </section>
      <section className="rounded-xl border border-white/[0.08] bg-white/[0.02]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] p-4"><div><h2 className="text-sm font-semibold">Infrastructure nodes</h2><p className="mt-1 text-xs text-slate-500">Registered systems and their connection state</p></div><div className="flex gap-1 rounded-lg border border-white/10 bg-black/20 p-1">{["All", "Online", "Attention", "Offline"].map(f => <button key={f} onClick={() => setFilter(f)} className={filter === f ? "rounded-md bg-white/10 px-3 py-1.5 text-[11px] text-white" : "rounded-md px-3 py-1.5 text-[11px] text-slate-500 hover:text-slate-200"}>{f}</button>)}</div></div>
        <div className="divide-y divide-white/[0.06]">{visible.map(node => {
            const Icon = node.icon;
            return <div key={node.id} className="p-4">
          <button onClick={() => setExpanded(expanded === node.id ? "" : node.id)} className="flex w-full flex-wrap items-center gap-3 text-left">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-slate-300"><Icon size={18} /></div>
            <div className="min-w-0 flex-1"><p className="text-sm font-medium text-slate-100">{node.name}</p><p className="mt-1 text-xs text-slate-500">{node.role}</p></div>
            <span className={"rounded-full px-2.5 py-1 text-[10px] font-semibold " + (node.status === "Online" ? "bg-emerald-300/10 text-emerald-300" : node.status === "Attention" ? "bg-amber-300/10 text-amber-300" : "bg-rose-300/10 text-rose-300")}>{node.status}</span>
          </button>
          {expanded === node.id && <div className="ml-13 mt-4 grid gap-3 rounded-lg bg-black/20 p-3 sm:grid-cols-3"><div><p className="text-[10px] uppercase tracking-wider text-slate-600">Connection</p><p className="mt-1 text-xs text-slate-300">{node.address}</p></div><div><p className="text-[10px] uppercase tracking-wider text-slate-600">Last heartbeat</p><p className="mt-1 text-xs text-slate-300">{node.last}</p></div><div><p className="text-[10px] uppercase tracking-wider text-slate-600">Diagnostic</p><p className="mt-1 text-xs text-slate-300">{node.detail}</p></div></div>}
        </div>;
          })}{visible.length === 0 && <p className="p-8 text-center text-xs text-slate-500">No nodes match this filter.</p>}</div>
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5"><div className="flex items-center gap-2"><Network size={16} className="text-cyan-300" /><h2 className="text-sm font-semibold">Connectivity checks</h2></div><div className="mt-4 space-y-3">{[{
              name: "Device heartbeat service",
              desc: "Local agent → central API",
              icon: Wifi
            }, {
              name: "API health endpoint",
              desc: "Application readiness and liveness",
              icon: Activity
            }, {
              name: "Storage and database",
              desc: "PostgreSQL and memory services",
              icon: HardDrive
            }].map(item => <div key={item.name} className="flex items-center gap-3 rounded-lg bg-white/[0.025] p-3"><item.icon size={15} className="text-slate-500" /><div className="min-w-0 flex-1"><p className="text-xs text-slate-200">{item.name}</p><p className="mt-1 text-[10px] text-slate-600">{item.desc}</p></div><span className="text-[10px] text-slate-600">Not configured</span></div>)}</div></section>
        <section className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5"><div className="flex items-center gap-2"><Shield size={16} className="text-cyan-300" /><h2 className="text-sm font-semibold">Monitoring prerequisites</h2></div><ul className="mt-4 space-y-3 text-xs leading-5 text-slate-400"><li className="flex gap-2"><CircleHelp size={14} className="mt-0.5 shrink-0 text-slate-600" />Install and authorize a lightweight local device agent.</li><li className="flex gap-2"><CircleHelp size={14} className="mt-0.5 shrink-0 text-slate-600" />Expose authenticated health endpoints for the API and services.</li><li className="flex gap-2"><CircleHelp size={14} className="mt-0.5 shrink-0 text-slate-600" />Send timestamped heartbeats and metrics to the central backend.</li><li className="flex gap-2"><CircleHelp size={14} className="mt-0.5 shrink-0 text-slate-600" />Apply explicit permissions and retention rules to telemetry.</li></ul></section>
      </div>
      <p className="text-center text-[10px] text-slate-600">Prototype state only · No devices are contacted and no system metrics are fabricated.</p>
    </main>
  </div>;
};