import React from 'react';
import { Shield, Cloud, HardDrive, Bell, Search, Command } from 'lucide-react';
import { LLMSelector } from './LLMSelector';
export const SystemHeader: React.FC = () => {
  return <header className="h-16 border-b border-white/5 bg-[#0A0B10]/80 backdrop-blur-md fixed top-0 right-0 left-64 z-40 flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        {/* Search Bar */}
        <div className="relative group">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
          <input type="text" placeholder="Search resources..." className="bg-white/5 border border-white/10 rounded-full pl-10 pr-4 py-1.5 text-sm w-64 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder:text-slate-600" />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-50">
            <Command size={12} />
            <span className="text-[10px] font-bold">K</span>
          </div>
        </div>

        {/* Connectivity Status */}
        <div className="flex items-center gap-4 border-l border-white/10 pl-6">
          <div className="flex items-center gap-2 group cursor-help">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <HardDrive size={16} className="text-slate-400" />
            <span className="text-xs font-medium text-slate-300">Local: 127.0.0.1</span>
          </div>
          <div className="flex items-center gap-2 group cursor-help">
            <Cloud size={16} className="text-cyan-400" />
            <span className="text-xs font-medium text-slate-300">Cloud Sync: Active</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Global LLM Switcher */}
        <LLMSelector />

        {/* Action Icons */}
        <div className="flex items-center gap-2 border-l border-white/10 pl-4">
          <button className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors relative">
            <Bell size={20} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-cyan-500 rounded-full border-2 border-[#0A0B10]" />
          </button>
          <button className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
            <Shield size={20} />
          </button>
        </div>
      </div>
    </header>;
};