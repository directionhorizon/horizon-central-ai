import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Info, Target, Clock, ExternalLink, Layers, Zap } from 'lucide-react';
export const ContextPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true);
  return <div className={`fixed right-0 top-16 h-[calc(100vh-64px)] bg-[#141721] border-l border-white/5 transition-all duration-300 z-30 ${isOpen ? 'w-80' : 'w-0'}`}>
      {/* Toggle Button */}
      <button onClick={() => setIsOpen(!isOpen)} className="absolute -left-8 top-4 w-8 h-10 bg-[#141721] border-y border-l border-white/5 rounded-l-lg flex items-center justify-center text-slate-400 hover:text-white transition-colors">
        {isOpen ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>

      {isOpen && <div className="h-full overflow-y-auto scrollbar-hide p-6">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Context Engine</h2>
            <div className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 text-[10px] font-bold">LIVE</div>
          </div>

          {/* Project Section */}
          <section className="mb-8">
            <div className="flex items-center gap-2 mb-4 text-white font-semibold text-sm">
              <Layers size={16} className="text-cyan-400" />
              <span>Project Metadata</span>
            </div>
            <div className="space-y-3">
              <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">Active Space</p>
                <p className="text-sm text-slate-200">Horizon Architecture v2</p>
              </div>
              <div className="bg-white/5 p-3 rounded-lg border border-white/5">
                <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">Primary Directive</p>
                <p className="text-sm text-slate-200 italic">"Orchestrate local LLM infrastructure for scalable RAG pipelines."</p>
              </div>
            </div>
          </section>

          {/* Missions Section */}
          <section className="mb-8">
            <div className="flex items-center gap-2 mb-4 text-white font-semibold text-sm">
              <Target size={16} className="text-orange-400" />
              <span>Active Missions</span>
            </div>
            <div className="space-y-2">
              {[{
            id: 1,
            name: 'Indexing Local Data',
            status: '82%',
            icon: Clock
          }, {
            id: 2,
            name: 'Agent: Coder-01 Refactoring',
            status: 'Pending',
            icon: Zap
          }].map(mission => <div key={mission.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                  <div className="flex items-center gap-3">
                    <mission.icon size={14} className="text-slate-500 group-hover:text-cyan-400" />
                    <span className="text-xs text-slate-300">{mission.name}</span>
                  </div>
                  <span className="text-[10px] font-mono text-cyan-400">{mission.status}</span>
                </div>)}
            </div>
          </section>

          {/* Quick Actions */}
          <section>
            <div className="flex items-center gap-2 mb-4 text-white font-semibold text-sm">
              <Info size={16} className="text-slate-400" />
              <span>System Insights</span>
            </div>
            <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-transparent border border-cyan-500/10">
              <p className="text-[11px] text-slate-300 leading-relaxed">
                Horizon is currently utilizing <span className="text-cyan-400 font-bold">Llama-3-70B-Instruct</span> for complex reasoning tasks via local inference.
              </p>
              <button className="mt-3 flex items-center gap-1.5 text-[10px] text-cyan-400 font-bold uppercase hover:underline">
                View Performance Graph <ExternalLink size={10} />
              </button>
            </div>
          </section>
        </div>}
    </div>;
};