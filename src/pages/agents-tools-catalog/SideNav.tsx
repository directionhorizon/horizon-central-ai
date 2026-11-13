import React from 'react';
import { LayoutDashboard, Cpu, Network, Database, Activity, MessageSquare, ChevronRight, UserCircle } from 'lucide-react';
interface NavItemProps {
  icon: React.ElementType;
  label: string;
  isActive?: boolean;
}
const NavItem: React.FC<NavItemProps> = ({
  icon: Icon,
  label,
  isActive
}) => <button type="button" aria-current={isActive ? 'page' : undefined} className={`w-full flex items-center px-4 py-3 gap-3 transition-all duration-200 group ${isActive ? 'text-cyan-400 bg-cyan-400/10 border-r-2 border-cyan-400' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><Icon size={19} /><span className="font-medium text-sm">{label}</span></button>;
export const SideNav: React.FC<{
  activeLabel?: string;
}> = ({
  activeLabel = 'Workbench'
}) => <aside className="w-64 h-screen bg-[#0A0B10] border-r border-white/5 flex flex-col fixed left-0 top-0 z-50">
 <div className="p-6 flex items-center gap-3"><div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20"><div className="w-4 h-4 bg-white rounded-sm rotate-45" /></div><span className="font-bold text-lg tracking-tight text-white uppercase">Horizon</span></div>
 <nav className="flex-1 mt-3"><div className="px-4 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Workspace</div>
 <NavItem icon={LayoutDashboard} label="Main Workbench" isActive={activeLabel === 'Workbench'} />
 <NavItem icon={MessageSquare} label="AI Control Center" isActive={activeLabel === 'AI Control Center'} />
 <NavItem icon={Cpu} label="Model Manager" isActive={activeLabel === 'Model Manager'} />
 <NavItem icon={Network} label="Environment Manager" isActive={activeLabel === 'Environment Manager'} />
 <NavItem icon={Database} label="Knowledge & Memory" isActive={activeLabel === 'Knowledge Hub'} />
 <div className="px-4 mt-8 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">System</div>
 <NavItem icon={Activity} label="System Monitor" isActive={activeLabel === 'System Monitor'} />
 </nav>
 <div className="p-4 border-t border-white/5"><div className="flex items-center gap-3 p-2 rounded-xl"><UserCircle size={30} className="text-slate-400" /><div className="flex-1 overflow-hidden"><p className="text-sm font-semibold text-white truncate">HORIZON</p><p className="text-[11px] text-slate-500 truncate">Workspace</p></div><ChevronRight size={16} className="text-slate-600" /></div></div>
</aside>;