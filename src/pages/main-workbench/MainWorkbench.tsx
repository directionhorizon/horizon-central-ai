import { useRef, useState } from 'react';
import { ArrowUp, Bot, CheckCircle2, FileCode2, FileText, Paperclip, Plus, Sparkles, User } from 'lucide-react';
import { useChatSession } from '../../shared/ChatSessionContext';
import { AskHero } from '../../components/AskHero';
type Upload = {
  name: string;
  size: string;
};
const SUGGESTIONS = [{
  id: 'rerank',
  label: 'Draft a reranking plan'
}, {
  id: 'latency',
  label: 'Analyze latency tradeoffs'
}, {
  id: 'tests',
  label: 'Generate evaluation cases'
}];
const formatSize = (bytes: number) => `${Math.max(1, Math.round(bytes / 1024))} KB`;
export const MainWorkbench = () => {
  const { messages, sendMessage, status, errorMessage, clearError, execution, sessionTitle } = useChatSession();
  const [draft, setDraft] = useState('');
  const [uploads, setUploads] = useState<Upload[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const busy = status === 'loading';
  const submitMessage = () => {
    const value = draft.trim();
    if ((!value && uploads.length === 0) || busy) return;
    const attachment = uploads[0];
    void sendMessage(value, attachment ? {
      name: attachment.name,
      meta: `File · ${attachment.size}`,
      type: 'document'
    } : undefined);
    setDraft('');
    setUploads([]);
  };
  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    setUploads(Array.from(files).map(file => ({
      name: file.name,
      size: formatSize(file.size)
    })));
  };
  return <div className="min-h-screen bg-[#0a0b10] text-slate-100">

      <main className="mx-auto flex min-h-screen w-full max-w-[1500px] flex-col">
        <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-5 pb-8 pt-8 sm:px-8" aria-labelledby="workbench-title">
          <header className="mb-6 flex items-end justify-between gap-6">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-400">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_12px_#00d1ff]" />
                <span>HORIZON CENTRAL AI · échange local</span>
              </div>
              <h2 className="text-base font-semibold tracking-tight text-white">Espace de travail</h2>
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-400 md:flex">
              <CheckCircle2 size={14} className={status === 'error' ? 'text-rose-400' : 'text-emerald-400'} />
              <span>{busy ? 'Traitement…' : sessionTitle ?? 'Session locale'}</span>
            </div>
          </header>

          {messages.length === 0 && <AskHero active={busy} modelReady={execution?.provider_id ? true : false} />}

          {errorMessage && <div role="alert" className="mb-4 flex items-start justify-between gap-3 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-xs leading-5 text-rose-200"><span>{errorMessage}</span><button type="button" onClick={clearError} className="shrink-0 rounded-md border border-rose-300/30 px-2 py-1 text-[11px] hover:bg-rose-400/10">Fermer</button></div>}
          {execution && <p className="mb-4 text-[11px] text-slate-500">Dernier enregistrement serveur : <span className="text-slate-300">{execution.status}</span>{execution.provider_id ? ` · ${execution.provider_id}` : ' · aucun fournisseur configuré'}</p>}

          <div className="flex-1 space-y-6 overflow-y-auto pr-2 scrollbar-hide" aria-label="Conversation history">
            {messages.length === 0 && !busy && <p className="rounded-2xl border border-dashed border-white/10 px-5 py-8 text-center text-sm text-slate-500">Aucun message dans cette session. Envoyez un premier message pour l'enregistrer côté backend.</p>}
            {messages.map(message => <article key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'assistant' && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300"><Bot size={16} /></div>}
                <div className={`max-w-2xl ${message.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                  <div className={`mb-1.5 flex items-center gap-2 text-[11px] text-slate-500 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <span className="font-semibold uppercase tracking-wider">{message.role === 'user' ? 'You' : 'Horizon AI'}</span>
                    <span>{message.time}</span>
                  </div>
                  <div className={`rounded-2xl border px-5 py-4 text-sm leading-7 shadow-xl ${message.role === 'user' ? 'rounded-tr-md border-cyan-400/20 bg-cyan-400/[0.09] text-slate-100' : 'rounded-tl-md border-white/[0.09] bg-white/[0.045] text-slate-300 backdrop-blur-xl'}`}>
                    <p>{message.content}</p>
                    {message.role === 'assistant' && message.id === 'response' && <p className="mt-3 border-l-2 border-cyan-400/70 pl-3 text-slate-400"><strong className="font-medium text-cyan-300">Suggested next step:</strong> benchmark the reranker against the 50-question evaluation set before wiring it into production retrieval.</p>}
                    {message.attachment && <div className="mt-4 flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2.5"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 text-slate-300">{message.attachment.type === 'code' ? <FileCode2 size={16} /> : <FileText size={16} />}</div><div className="min-w-0"><p className="truncate text-xs font-medium text-slate-200">{message.attachment.name}</p><p className="text-[11px] text-slate-500">{message.attachment.meta}</p></div></div>}
                  </div>
                </div>
                {message.role === 'user' && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/10 text-slate-300"><User size={16} /></div>}
              </article>)}
          </div>

          <div className="mt-8">
            <div className="mb-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map(suggestion => <button key={suggestion.id} type="button" onClick={() => setDraft(suggestion.label)} className="rounded-full border border-white/10 bg-white/[0.025] px-3 py-1.5 text-xs text-slate-400 transition hover:border-cyan-400/30 hover:text-cyan-300"><span>{suggestion.label}</span></button>)}
            </div>
            {uploads.length > 0 && <div className="mb-2 flex flex-wrap gap-2">{uploads.map(upload => <div key={upload.name} className="flex items-center gap-2 rounded-lg border border-cyan-400/20 bg-cyan-400/10 px-3 py-2 text-xs text-cyan-200"><Paperclip size={13} /><span>{upload.name}</span><span className="text-cyan-400/60">{upload.size}</span><button type="button" aria-label={`Remove ${upload.name}`} onClick={() => setUploads(current => current.filter(item => item.name !== upload.name))}>×</button></div>)}</div>}
            <div className="rounded-2xl border border-white/10 bg-[#141721]/90 p-2 shadow-2xl shadow-black/20 backdrop-blur-xl focus-within:border-cyan-400/40">
              <textarea value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                submitMessage();
              }
            }} rows={2} placeholder="Ask HORIZON anything about this project..." aria-label="Message HORIZON" className="w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 text-white outline-none placeholder:text-slate-600" />
              <div className="flex items-center justify-between border-t border-white/[0.07] px-2 pt-2">
                <div className="flex items-center gap-1"><input ref={fileInputRef} type="file" multiple className="hidden" onChange={event => handleFiles(event.target.files)} /><button type="button" aria-label="Attach files" onClick={() => fileInputRef.current?.click()} className="rounded-lg p-2 text-slate-500 transition hover:bg-white/10 hover:text-cyan-300"><Paperclip size={17} /></button><button type="button" aria-label="Start new thread" onClick={() => {
                  setDraft('');
                  setUploads([]);
                }} className="rounded-lg p-2 text-slate-500 transition hover:bg-white/10 hover:text-slate-200"><Plus size={17} /></button><span className="ml-2 hidden text-[11px] text-slate-600 sm:inline">Enter to send · Shift + Enter for line break</span></div>
                <button type="button" onClick={submitMessage} aria-label="Send message" className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-400 text-[#071016] shadow-lg shadow-cyan-400/20 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40" disabled={(!draft.trim() && uploads.length === 0) || busy}><ArrowUp size={17} strokeWidth={2.5} /></button>
              </div>
            </div>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-[11px] text-slate-600"><Sparkles size={12} /> HORIZON can make mistakes. Verify critical decisions against your local sources.</p>
          </div>
        </section>
      </main>
    </div>;
};
export default MainWorkbench;