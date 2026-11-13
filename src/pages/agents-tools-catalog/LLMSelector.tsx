import React, { useState } from 'react';
import { Sparkles, ChevronDown, Monitor, Cpu } from 'lucide-react';
type ModelMode = 'Automatic' | 'Manual';
interface Model {
  id: string;
  name: string;
  provider: 'Local' | 'Cloud';
  size?: string;
}
const MODELS: Model[] = [{
  id: 'llama3',
  name: 'Llama 3 70B',
  provider: 'Local',
  size: '39.8 GB'
}, {
  id: 'mistral',
  name: 'Mistral 7B v0.2',
  provider: 'Local',
  size: '4.1 GB'
}, {
  id: 'gpt4',
  name: 'GPT-4o',
  provider: 'Cloud'
}, {
  id: 'claude3',
  name: 'Claude 3.5 Sonnet',
  provider: 'Cloud'
}];
export const LLMSelector: React.FC = () => {
  const [mode, setMode] = useState<ModelMode>('Automatic');
  const [selectedModel, setSelectedModel] = useState<Model>(MODELS[0]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  return <div className="flex items-center gap-2">
      {/* Mode Toggle */}
      <div className="flex bg-white/5 p-1 rounded-lg border border-white/5">
        <button onClick={() => setMode('Automatic')} className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-bold transition-all ${mode === 'Automatic' ? 'bg-cyan-500 text-[#0A0B10] shadow-lg shadow-cyan-500/20' : 'text-slate-400 hover:text-white'}`}>
          <Sparkles size={12} />
          AUTO
        </button>
        <button onClick={() => setMode('Manual')} className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-bold transition-all ${mode === 'Manual' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
          <Monitor size={12} />
          MANUAL
        </button>
      </div>

      {/* Model Dropdown */}
      <div className="relative">
        <button onClick={() => setIsDropdownOpen(!isDropdownOpen)} disabled={mode === 'Automatic'} className={`flex items-center gap-3 px-3 py-2 rounded-lg border transition-all ${mode === 'Automatic' ? 'bg-white/5 border-white/5 opacity-50 cursor-not-allowed' : 'bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10'}`}>
          <div className="flex items-center gap-2">
            <Cpu size={14} className={mode === 'Automatic' ? 'text-slate-600' : 'text-cyan-400'} />
            <div className="text-left">
              <p className="text-[10px] text-slate-500 font-bold uppercase leading-none mb-0.5">
                {mode === 'Automatic' ? 'System Optimized' : 'Active Model'}
              </p>
              <p className="text-xs text-white font-semibold leading-none">
                {mode === 'Automatic' ? 'Dynamic Orchestration' : selectedModel.name}
              </p>
            </div>
          </div>
          <ChevronDown size={14} className={`text-slate-500 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
        </button>

        {isDropdownOpen && mode === 'Manual' && <div className="absolute top-full mt-2 right-0 w-64 bg-[#141721] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden py-2 backdrop-blur-xl">
            <div className="px-3 py-1 mb-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase">Select Provider</span>
            </div>
            {MODELS.map(model => <button key={model.id} onClick={() => {
          setSelectedModel(model);
          setIsDropdownOpen(false);
        }} className={`w-full flex items-center justify-between px-4 py-2 hover:bg-white/5 transition-colors ${selectedModel.id === model.id ? 'bg-cyan-500/5 text-cyan-400' : 'text-slate-300'}`}>
                <div className="flex flex-col items-start">
                  <span className="text-sm font-medium">{model.name}</span>
                  <span className="text-[10px] text-slate-500">{model.provider} {model.size ? `• ${model.size}` : ''}</span>
                </div>
                {selectedModel.id === model.id && <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" />}
              </button>)}
          </div>}
      </div>
    </div>;
};