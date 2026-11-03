import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  BrainCircuit,
  Split,
  ShieldCheck,
  MessageSquare,
  Download,
  FolderArchive,
  Settings,
  ChevronLeft,
  ChevronRight,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useDocument } from '../../contexts/DocumentContext';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const { currentResult, serverStatus } = useDocument();

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/ingestion', label: 'Ingestion', icon: UploadCloud },
    { to: '/knowledge', label: 'Knowledge Explorer', icon: BrainCircuit },
    { to: '/chunks', label: 'Chunks Inspector', icon: Split },
    { to: '/quality', label: 'Quality & Evaluation', icon: ShieldCheck },
    { to: '/search', label: 'AI Search (RAG)', icon: MessageSquare },
    { to: '/exports', label: 'Export Center', icon: Download },
    { to: '/documents', label: 'Document Library', icon: FolderArchive },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  const hasKey = serverStatus?.has_key ?? false;

  return (
    <aside
      className={`relative flex flex-col bg-[#090d16] border-r border-slate-800/80 transition-all duration-300 z-30 shrink-0 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-600/20 shrink-0">
            <Layers className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight bg-gradient-to-r from-white via-slate-200 to-purple-300 bg-clip-text text-transparent truncate">
                Knowledge 2.0
              </span>
              <span className="text-[10px] text-purple-400 font-mono flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> Sarvam AI Powered
              </span>
            </div>
          )}
        </div>

        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav List */}
      <nav className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-purple-600/15 text-purple-300 border border-purple-500/30 shadow-sm shadow-purple-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent'
                }`
              }
              title={collapsed ? item.label : undefined}
            >
              <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Info Bar */}
      <div className="p-3 border-t border-slate-800/80 space-y-2">
        {/* Active Document Mini Badge */}
        {!collapsed && currentResult && (
          <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-[11px] space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="uppercase tracking-wider text-[9px] font-semibold text-purple-400">Active Doc</span>
              <span className="text-[10px] font-mono text-slate-400">{currentResult.stats.total_chunks} chunks</span>
            </div>
            <p className="font-medium text-slate-200 truncate" title={currentResult.document_name}>
              {currentResult.document_name}
            </p>
          </div>
        )}

        {/* Sarvam Status Pill */}
        <div
          className={`flex items-center gap-2 p-2 rounded-xl bg-slate-900/60 border border-slate-800/70 text-xs ${
            collapsed ? 'justify-center' : ''
          }`}
          title={hasKey ? 'Sarvam AI Authenticated' : 'Key Missing / Simulated'}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              hasKey ? 'bg-emerald-400 ring-2 ring-emerald-400/20' : 'bg-amber-400 ring-2 ring-amber-400/20'
            }`}
          />
          {!collapsed && (
            <span className="text-[11px] font-medium text-slate-300 truncate">
              {hasKey ? 'Sarvam-105b Ready' : 'Simulated Mode'}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
};
