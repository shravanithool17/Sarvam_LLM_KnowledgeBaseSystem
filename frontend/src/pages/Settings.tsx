import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Server,
  Shield,
  HardDrive,
  Cpu,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';

export const Settings: React.FC = () => {
  const { serverStatus, healthCheck, refreshStatus } = useDocument();
  const { showToast } = useToast();

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sessionAutoSave, setSessionAutoSave] = useState(true);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [defaultTopK, setDefaultTopK] = useState(2);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refreshStatus();
    setIsRefreshing(false);
    showToast('Backend diagnostics refreshed', 'info');
  };

  const hasKey = serverStatus?.has_key ?? false;

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">System & Engine Settings</h2>
          <p className="text-xs text-slate-400 mt-1">
            Engine diagnostics, Sarvam AI model configurations, storage parameters, and client preferences.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-purple-400' : ''}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* 1. Sarvam AI Diagnostics Card */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-600/20 text-purple-400 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-200">Sarvam AI LLM Engine</h3>
              <p className="text-[11px] text-slate-500">Authentication & model endpoints</p>
            </div>
          </div>

          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-mono ${
              hasKey
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/40'
                : 'bg-amber-950/60 text-amber-300 border-amber-800/40'
            }`}
          >
            {hasKey ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            <span>{hasKey ? 'API Key Authenticated' : 'Key Missing / Simulated'}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/70 space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
              Default Inference Model
            </span>
            <p className="font-mono text-purple-300 font-bold">
              {serverStatus?.default_model || 'sarvam-105b'}
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/70 space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
              Supported Models
            </span>
            <p className="font-mono text-slate-300">
              {serverStatus?.valid_models?.join(', ') || 'sarvam-105b, sarvam-105b-conversations'}
            </p>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/30 border border-slate-800/50 text-[11px] text-slate-400 flex items-start gap-2">
          <Shield className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
          <span>
            API Key security policy enforced: Subscription credentials are kept in server environment variables and
            never returned in API responses or stored in browser local storage.
          </span>
        </div>
      </div>

      {/* 2. Backend Infrastructure & Storage Card */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center">
            <Server className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-200">Backend Infrastructure</h3>
            <p className="text-[11px] text-slate-500">FastAPI backend & local storage parameters</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/70 space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
              <HardDrive className="w-3 h-3 text-emerald-400" /> Storage Engine
            </span>
            <p className="font-mono text-slate-200 font-semibold">SQLite (WAL Mode)</p>
            <p className="text-[10px] text-slate-500">Transactional atomic rename</p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/70 space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
              <Cpu className="w-3 h-3 text-blue-400" /> Runtime Environment
            </span>
            <p className="font-mono text-slate-200 font-semibold">
              Python {healthCheck?.checks?.python_version || '3.15.0'}
            </p>
            <p className="text-[10px] text-slate-500">FastAPI + Uvicorn server</p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/70 space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
              Disk Available
            </span>
            <p className="font-mono text-slate-200 font-semibold">
              {healthCheck?.checks?.disk_free_mb
                ? `${(healthCheck.checks.disk_free_mb / 1024).toFixed(1)} GB`
                : 'Available'}
            </p>
            <p className="text-[10px] text-slate-500">Local data directory</p>
          </div>
        </div>
      </div>

      {/* 3. Client Preferences Card */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-600/20 text-emerald-400 flex items-center justify-center">
            <SettingsIcon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-200">Client Preferences</h3>
            <p className="text-[11px] text-slate-500">Customize your local UI dashboard behavior</p>
          </div>
        </div>

        <div className="divide-y divide-slate-800/60 text-xs pt-1">
          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-200">Session Auto-Restore</p>
              <p className="text-[11px] text-slate-500">Persist active document in localStorage across browser tabs</p>
            </div>
            <input
              type="checkbox"
              checked={sessionAutoSave}
              onChange={(e) => {
                setSessionAutoSave(e.target.checked);
                showToast(`Session auto-restore ${e.target.checked ? 'enabled' : 'disabled'}`, 'info');
              }}
              className="accent-purple-600 w-4 h-4 cursor-pointer"
            />
          </div>

          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-200">Smooth Animations</p>
              <p className="text-[11px] text-slate-500">Framer Motion page transitions & toast animations</p>
            </div>
            <input
              type="checkbox"
              checked={animationsEnabled}
              onChange={(e) => {
                setAnimationsEnabled(e.target.checked);
                showToast(`Animations ${e.target.checked ? 'enabled' : 'disabled'}`, 'info');
              }}
              className="accent-purple-600 w-4 h-4 cursor-pointer"
            />
          </div>

          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-200">Default RAG Search Top-K</p>
              <p className="text-[11px] text-slate-500">Number of top relevant chunks retrieved per user question</p>
            </div>
            <select
              value={defaultTopK}
              onChange={(e) => setDefaultTopK(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-purple-300 font-mono focus:outline-none"
            >
              <option value="2">2 Chunks</option>
              <option value="3">3 Chunks</option>
              <option value="5">5 Chunks</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};
