import React, { useState } from "react";
import { useChatSession } from "../../shared/ChatSessionContext";
import { Bot, Send, Paperclip, Plus, Sparkles, ChevronDown, Command, BrainCircuit, Activity, ShieldCheck, PanelRight, Clock3 } from "lucide-react";
export const AIControlCenter = () => {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("Automatic routing");
  const { messages, sendMessage, createSession, resetSession, status, errorMessage, clearError, execution, warnings, sessionId } = useChatSession();
  const [showContext, setShowContext] = useState(true);
  const busy = status === "loading";
  const send = () => {
    const value = prompt.trim();
    if (!value || busy) return;
    void sendMessage(value);
    setPrompt("");
  };
  return <div className="min-h-screen bg-[#090c13] text-slate-100">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-[1500px] grid-cols-1 lg:grid-cols-[minmax(0,1fr)_290px]">
        <main className="flex min-h-[calc(100vh-5rem)] min-w-0 flex-col">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-6 py-4">
            <div><p className="text-xs text-slate-500">WORKSPACE / NEW SESSION</p><h1 className="mt-1 text-lg font-semibold">How can I help you today?</h1></div>
            <button onClick={() => void createSession()} disabled={busy} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"><Plus size={14} /> New session</button>
          </div>
          {errorMessage && <div role="alert" className="mx-6 mt-4 flex items-start justify-between gap-3 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-xs leading-5 text-rose-200"><span>{errorMessage}</span><button type="button" onClick={clearError} className="shrink-0 rounded-md border border-rose-300/30 px-2 py-1 text-[11px] hover:bg-rose-400/10">Fermer</button></div>}
          {warnings.length > 0 && <ul className="mx-6 mt-3 list-disc space-y-1 pl-5 text-[11px] text-amber-200/80">{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
          <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 py-8 sm:px-7">
            {messages.length === 0 && <div className="mb-8 mt-5"><div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200"><Sparkles size={23} /></div><h2 className="text-2xl font-semibold tracking-tight">Your work starts here.</h2><p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">One place to think, plan and coordinate. HORIZON will use the configured model and connected environments once the backend is integrated.</p></div>}
            <div className="flex-1 space-y-5">
              {messages.map((message, index) => <div key={index} className={message.role === "user" ? "ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-cyan-400/10 px-4 py-3 text-sm leading-6 text-slate-100" : "flex max-w-[90%] gap-3"}>
                {message.role !== "user" && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cyan-300/20 bg-cyan-300/10 text-cyan-200"><Bot size={16} /></div>}
                {message.role !== "user" && <div className="rounded-2xl rounded-bl-sm border border-white/[0.08] bg-white/[0.035] px-4 py-3 text-sm leading-6 text-slate-300">{message.content}</div>}
                {message.role === "user" && message.content}
              </div>)}
            </div>
            <div className="mt-8 rounded-2xl border border-white/10 bg-[#111722] p-3 shadow-2xl shadow-black/20 focus-within:border-cyan-300/40">
              <textarea value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }} rows={3} placeholder="Describe what you want to accomplish…" className="w-full resize-none bg-transparent px-2 py-2 text-sm text-white outline-none placeholder:text-slate-600" />
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.07] pt-3">
                <div className="flex items-center gap-2"><button type="button" title="Attachments (not connected)" className="rounded-lg p-2 text-slate-500 hover:bg-white/5"><Paperclip size={16} /></button><div className="relative"><select value={mode} onChange={e => setMode(e.target.value)} className="appearance-none rounded-lg border border-white/10 bg-white/[0.03] py-2 pl-3 pr-8 text-[11px] text-slate-300 outline-none"><option>Automatic routing</option><option>Manual model selection</option><option>Planning only</option></select><ChevronDown className="pointer-events-none absolute right-2 top-2.5 text-slate-500" size={12} /></div></div>
                <button onClick={send} disabled={!prompt.trim() || busy} className="inline-flex items-center gap-2 rounded-lg bg-cyan-300 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-40"><Send size={14} /> Send</button>
              </div>
            </div>
            <p className="mt-3 text-center text-[10px] text-slate-600">{busy ? 'Synchronisation avec le backend local…' : 'Messages are persisted by the local FastAPI backend · no AI model connected (accepted_no_model).'}</p>
          </section>
        </main>
        <aside className="border-t border-white/[0.07] bg-white/[0.015] p-5 lg:border-l lg:border-t-0">
          <div className="mb-5 flex items-center justify-between"><h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Session context</h2><button onClick={() => setShowContext(!showContext)} className="rounded p-1 text-slate-500 hover:bg-white/5" aria-label="Toggle context"><PanelRight size={15} /></button></div>
          {showContext && <div className="space-y-3">
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center gap-2 text-xs font-medium text-slate-200"><Activity size={15} className="text-amber-300" /> Runtime status</div><p className="mt-2 text-xs leading-5 text-slate-500">{status === 'error' ? 'Backend unreachable. Messages cannot be persisted right now.' : sessionId ? <>Session persisted server-side.<br />Execution status: <span className="text-slate-300">{execution ? execution.status : 'aucun message envoyé'}</span></> : 'Initialising session…'}</p></div>
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center gap-2 text-xs font-medium text-slate-200"><ShieldCheck size={15} className="text-cyan-300" /> Access & permissions</div><p className="mt-2 text-xs leading-5 text-slate-500">No external tools or agents have been invoked by this prototype.</p></div>
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center gap-2 text-xs font-medium text-slate-200"><Clock3 size={15} className="text-slate-400" /> Recent activity</div><p className="mt-2 text-xs leading-5 text-slate-500">{messages.length === 0 ? 'No activity recorded.' : `${messages.length} message(s) enregistré(s) côté backend.`}</p><button type="button" onClick={() => void resetSession()} disabled={busy} className="mt-3 w-full rounded-lg border border-white/10 px-3 py-2 text-[11px] text-slate-300 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40">Reset session (clears server messages)</button></div>
            <div className="rounded-xl border border-dashed border-white/10 p-4"><div className="flex items-center gap-2 text-xs text-slate-400"><Command size={14} /> Routing mode</div><p className="mt-2 text-sm text-slate-200">{mode}</p><p className="mt-1 text-[11px] leading-5 text-slate-600">Selection is visual only until the LLM Manager API is connected.</p></div>
          </div>}
        </aside>
      </div>
    </div>;
};