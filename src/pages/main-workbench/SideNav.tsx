import React from 'react';
import { LayoutDashboard, Cpu, Users, Database, Settings, ChevronRight, UserCircle } from 'lucide-react';
interface NavItemProps {
  icon: React.ElementType;
  label: string;
  isActive?: boolean;
  onClick?: () => void;
}
const NavItem: React.FC<NavItemProps> = ({
  icon: Icon,
  label,
  isActive,
  onClick
}) => <button onClick={onClick} className={`w-full flex items-center px-4 py-3 gap-3 transition-all duration-200 group ${isActive ? 'text-cyan-400 bg-cyan-400/10 border-r-2 border-cyan-400' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
    <Icon size={20} className={isActive ? 'text-cyan-400' : 'group-hover:text-cyan-300'} />
    <span className="font-medium text-sm">{label}</span>
  </button>;
export const SideNav: React.FC = () => {
  return <div className="w-64 h-screen bg-[#0A0B10] border-r border-white/5 flex flex-col fixed left-0 top-0 z-50">
      {/* Brand */}
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <div className="w-4 h-4 bg-white rounded-sm rotate-45" />
        </div>
        <span className="font-bold text-lg tracking-tight text-white uppercase">Horizon</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 mt-4">
        <div className="px-4 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
          Main
        </div>
        <NavItem icon={LayoutDashboard} label="Workbench" isActive />
        <NavItem icon={Cpu} label="Model Manager" />
        <NavItem icon={Users} label="Agents & Tools" />
        <NavItem icon={Database} label="Knowledge Hub" />
        
        <div className="px-4 mt-8 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
          System
        </div>
        <NavItem icon={Settings} label="Global Settings" />
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 cursor-pointer transition-colors group">
          <div className="relative">
            <UserCircle size={32} className="text-slate-400 group-hover:text-cyan-400 transition-colors" />
            <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-[#0A0B10] rounded-full" />
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-semibold text-white truncate">Dev Operator</p>
            <p className="text-[11px] text-slate-500 truncate">Pro Tier</p>
          </div>
          <ChevronRight size={16} className="text-slate-600 group-hover:text-white transition-colors" />
        </div>
      </div>
    </div>;
};