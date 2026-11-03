import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Sparkles,
  HelpCircle,
  Copy,
  Check,
  Search,
  Tag,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';
import { EmptyState } from '../components/common/EmptyState';

export const KnowledgeExplorer: React.FC = () => {
  const navigate = useNavigate();
  const { currentResult } = useDocument();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<'facts' | 'qa'>('facts');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [expandedQA, setExpandedQA] = useState<Record<string, boolean>>({});

  if (!currentResult) {
    return (
      <EmptyState
        title="No Document Knowledge Available"
        description="Please upload a PDF/DOCX or load the sample technical paper to explore extracted knowledge, facts, and synthetic Q&A pairs."
        actionText="Go to Ingestion"
        onAction={() => navigate('/ingestion')}
      />
    );
  }

  const { summary, facts = [], qa_dataset = [], mode, batch_processing_stats } = currentResult.knowledge;

  // Extract unique categories
  const categories = ['all', ...Array.from(new Set(facts.map((f) => f.category || 'Concept')))];

  // Filtered facts
  const filteredFacts = facts.filter((f) => {
    const matchesCat = selectedCategory === 'all' || (f.category || 'Concept') === selectedCategory;
    const matchesQuery =
      searchQuery === '' ||
      f.entity.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.fact.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesQuery;
  });

  // Filtered QA
  const filteredQA = qa_dataset.filter((qa) => {
    return (
      searchQuery === '' ||
      qa.instruction.toLowerCase().includes(searchQuery.toLowerCase()) ||
      qa.response.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  const handleCopySummary = () => {
    navigator.clipboard.writeText(summary);
    setCopiedSummary(true);
    showToast('Executive summary copied to clipboard', 'success');
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  const toggleQA = (id: string) => {
    setExpandedQA((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header Info Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">AI Knowledge Explorer</h2>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                mode === 'live'
                  ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/40'
                  : 'bg-purple-950/60 text-purple-300 border-purple-800/40'
              }`}
            >
              {mode === 'live' ? 'Sarvam Live' : 'Distilled'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Inspecting extracted knowledge for{' '}
            <strong className="text-slate-200">{currentResult.document_name}</strong> •{' '}
            {currentResult.stats.total_chunks} chunks • {facts.length} facts • {qa_dataset.length} Q&A pairs
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/search')}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <span>Ask in RAG</span>
            <ArrowRight className="w-3.5 h-3.5 text-purple-400" />
          </button>
        </div>
      </div>

      {/* Executive Summary Card */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-3 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <FileText className="w-4 h-4 text-purple-400" />
            <span>Executive Knowledge Synthesis</span>
          </div>
          <button
            onClick={handleCopySummary}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs flex items-center gap-1.5 transition"
          >
            {copiedSummary ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedSummary ? 'Copied' : 'Copy Summary'}</span>
          </button>
        </div>

        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans bg-slate-950/50 p-4 rounded-xl border border-slate-900">
          {summary || 'No summary extracted for this document.'}
        </p>

        {batch_processing_stats && (
          <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono pt-1">
            <span>Map-Reduce Batches: {batch_processing_stats.total_batches ?? 1}</span>
            <span>Successful: {batch_processing_stats.successful_batches ?? 1}</span>
            <span>Failed: {batch_processing_stats.failed_batches ?? 0}</span>
          </div>
        )}
      </div>

      {/* View Switcher & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Tab Switcher */}
        <div className="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800 shrink-0">
          <button
            onClick={() => setActiveTab('facts')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === 'facts'
                ? 'bg-purple-600 text-white shadow-sm shadow-purple-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Structured Facts ({facts.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('qa')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === 'qa'
                ? 'bg-purple-600 text-white shadow-sm shadow-purple-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Instruction Q&A ({qa_dataset.length})</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Filter ${activeTab === 'facts' ? 'facts & entities' : 'questions & answers'}...`}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 transition"
          />
        </div>
      </div>

      {/* VIEW 1: Structured Facts */}
      {activeTab === 'facts' && (
        <div className="space-y-4">
          {/* Category Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-[11px] text-slate-500 font-medium shrink-0">Category:</span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-full text-[11px] font-medium border capitalize shrink-0 transition ${
                  selectedCategory === cat
                    ? 'bg-purple-950/80 text-purple-300 border-purple-600/60'
                    : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {filteredFacts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredFacts.map((fact, idx) => (
                <div
                  key={idx}
                  className="glass-card p-5 rounded-2xl border border-slate-800/80 space-y-3 hover:border-purple-500/30 transition group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-0.5">
                      <h4 className="font-semibold text-sm text-slate-100 group-hover:text-purple-300 transition">
                        {fact.entity}
                      </h4>
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono text-purple-400 bg-purple-950/50 px-2 py-0.5 rounded border border-purple-800/30">
                        <Tag className="w-2.5 h-2.5" />
                        {fact.category || 'Concept'}
                      </span>
                    </div>

                    <button
                      onClick={() => navigate('/chunks')}
                      className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-950/50 hover:bg-emerald-950 px-2.5 py-1 rounded-lg border border-emerald-800/40 transition shrink-0"
                      title="Inspect source chunk"
                    >
                      <span>{fact.citation}</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{fact.fact}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 glass-card rounded-2xl border border-slate-800 text-xs text-slate-500">
              No facts match the selected query or category.
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: Instruction Q&A Dataset */}
      {activeTab === 'qa' && (
        <div className="space-y-4">
          {filteredQA.length > 0 ? (
            <div className="space-y-3">
              {filteredQA.map((qa, idx) => {
                const isExpanded = expandedQA[qa.id || idx] ?? true;
                return (
                  <div
                    key={qa.id || idx}
                    className="glass-card rounded-2xl border border-slate-800/80 overflow-hidden transition"
                  >
                    <div
                      onClick={() => toggleQA(qa.id || String(idx))}
                      className="p-4 sm:p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-slate-900/40 transition"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs font-bold text-purple-400 bg-purple-950/80 px-2.5 py-1 rounded-lg border border-purple-800/50 shrink-0">
                          {qa.id || `QA-${idx + 1}`}
                        </span>
                        <h4 className="text-xs sm:text-sm font-semibold text-slate-200 line-clamp-1">
                          {qa.instruction}
                        </h4>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                          {qa.citation}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-slate-500" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-500" />
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="px-5 pb-5 pt-1 border-t border-slate-800/60 bg-slate-950/40 space-y-3">
                        <div>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
                            Instruction Prompt:
                          </span>
                          <p className="text-xs text-slate-200 mt-0.5 font-medium">{qa.instruction}</p>
                        </div>

                        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-1">
                          <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400 flex items-center justify-between">
                            <span>Target Grounded Response:</span>
                            {qa.confidence && (
                              <span className="text-[9px] font-mono text-slate-400">
                                Confidence: {qa.confidence}
                              </span>
                            )}
                          </span>
                          <p className="text-xs text-slate-300 leading-relaxed">{qa.response}</p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 glass-card rounded-2xl border border-slate-800 text-xs text-slate-500">
              No Q&A pairs match your search query.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
