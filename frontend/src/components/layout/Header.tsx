import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  FileText,
  Activity,
  Upload,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { useDocument } from '../../contexts/DocumentContext';
import { useToast } from '../../contexts/ToastContext';
import { loadSampleDocument, getErrorMessage } from '../../services/api';

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  '/dashboard': { title: 'Dashboard', subtitle: 'Platform overview, metrics & recent documents' },
  '/ingestion': { title: 'Document Ingestion', subtitle: 'Parse PDF/DOCX, configure chunking & synthesize knowledge' },
  '/knowledge': { title: 'Knowledge Explorer', subtitle: 'Executive summary, facts matrix & instruction Q&A pairs' },
  '/chunks': { title: 'Chunks Inspector', subtitle: 'Boundary-aware chunk tokens, pages & source mappings' },
  '/quality': { title: 'Quality & Evaluation', subtitle: 'Redundancy rates, grounding audits & duplicate detection' },
  '/search': { title: 'AI Knowledge Search', subtitle: 'Conversational RAG retrieval powered by Sarvam AI' },
  '/exports': { title: 'Export Center', subtitle: 'Download fine-tuning datasets, vector JSON & spreadsheets' },
  '/documents': { title: 'Document Library', subtitle: 'Browse, manage & reopen stored knowledge graphs' },
  '/settings': { title: 'Settings', subtitle: 'API diagnostics, engine configuration & system health' },
};

export const Header: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentResult, setResult, healthCheck, clearCurrentDocument } = useDocument();
  const { showToast } = useToast();
  const [loadingSample, setLoadingSample] = useState(false);

  const currentRoute = routeTitles[location.pathname] || {
    title: 'Knowledge Platform',
    subtitle: 'AI Knowledge Engineering Suite',
  };

  const handleLoadSample = async () => {
    try {
      setLoadingSample(true);
      showToast('Running Sarvam Map-Reduce synthesis on sample paper...', 'info');
      const res = await loadSampleDocument({ model: 'sarvam-105b', num_facts: 3, num_qa_pairs: 3 });
      setResult(res);
      showToast('Sample document synthesized successfully!', 'success');
      navigate('/knowledge');
    } catch (err) {
      showToast(`Failed to load sample: ${getErrorMessage(err)}`, 'error');
    } finally {
      setLoadingSample(false);
    }
  };

  const isHealthy = healthCheck?.status === 'ok';

  return (
    <header className="h-16 bg-[#090d16]/80 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Route Title & Breadcrumb */}
      <div>
        <h1 className="text-sm font-semibold text-white tracking-tight">{currentRoute.title}</h1>
        <p className="text-[11px] text-slate-400 font-medium">{currentRoute.subtitle}</p>
      </div>

      {/* Center / Right controls */}
      <div className="flex items-center gap-3">
        {/* Active Document Indicator */}
        {currentResult ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-950/40 border border-purple-800/40 text-xs">
            <FileText className="w-3.5 h-3.5 text-purple-400" />
            <span className="font-medium text-purple-200 max-w-[160px] truncate" title={currentResult.document_name}>
              {currentResult.document_name}
            </span>
            <button
              onClick={clearCurrentDocument}
              className="p-1 text-slate-400 hover:text-rose-400 transition"
              title="Unload current document"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-500">
            <span>No document loaded</span>
          </div>
        )}

        {/* System Health Badge */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-[11px] font-mono ${
            isHealthy
              ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
              : 'bg-amber-950/30 border-amber-800/40 text-amber-300'
          }`}
          title={isHealthy ? 'Backend storage & Sarvam API online' : 'System checks pending'}
        >
          {isHealthy ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          )}
          <span className="hidden md:inline">Storage WAL</span>
        </div>

        {/* Action: Quick Sample Document */}
        <button
          onClick={handleLoadSample}
          disabled={loadingSample}
          className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition disabled:opacity-50"
          title="Load pre-packaged technical paper"
        >
          {loadingSample ? (
            <Activity className="w-3.5 h-3.5 text-purple-400 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 text-purple-400" />
          )}
          <span className="hidden sm:inline">Load Sample</span>
        </button>

        {/* Action: Ingest New */}
        <button
          onClick={() => navigate('/ingestion')}
          className="px-3.5 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-md shadow-purple-600/20 transition"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Ingest</span>
        </button>
      </div>
    </header>
  );
};
