import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Search,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  FileText,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';
import { EmptyState } from '../components/common/EmptyState';

export const ChunkInspector: React.FC = () => {
  const navigate = useNavigate();
  const { currentResult } = useDocument();
  const { showToast } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedAll, setExpandedAll] = useState(false);
  const [expandedChunks, setExpandedChunks] = useState<Record<string, boolean>>({});

  if (!currentResult || !currentResult.chunks.length) {
    return (
      <EmptyState
        title="No Chunks to Inspect"
        description="Please upload a document or load the sample paper to inspect boundary-aware segmented chunks with exact token and page attributions."
        actionText="Go to Ingestion"
        onAction={() => navigate('/ingestion')}
      />
    );
  }

  const chunks = currentResult.chunks;
  const pageSize = 8;

  // Filter chunks
  const filteredChunks = chunks.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.id.toLowerCase().includes(q) ||
      `page ${c.page}`.toLowerCase().includes(q) ||
      c.text.toLowerCase().includes(q)
    );
  });

  const totalPages = Math.ceil(filteredChunks.length / pageSize);
  const paginatedChunks = filteredChunks.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    showToast(`Chunk ${id} copied to clipboard`, 'success');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleExpand = (id: string) => {
    setExpandedChunks((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleToggleExpandAll = () => {
    const nextState = !expandedAll;
    setExpandedAll(nextState);
    const newExpanded: Record<string, boolean> = {};
    paginatedChunks.forEach((c) => {
      newExpanded[c.id] = nextState;
    });
    setExpandedChunks(newExpanded);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">Boundary-Aware Chunks Inspector</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-950/60 text-blue-300 border border-blue-800/40">
              {chunks.length} Total Chunks
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Origin: <strong className="text-slate-200">{currentResult.document_name}</strong> • Whole-sentence boundary
            segmentation with immutable page attribution.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleExpandAll}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition"
          >
            {expandedAll ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            <span>{expandedAll ? 'Collapse Page' : 'Expand Page'}</span>
          </button>
        </div>
      </div>

      {/* Search & Stats Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by text, chunk ID (e.g. CHK-001) or page..."
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 transition"
          />
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
          <span>Showing {paginatedChunks.length} of {filteredChunks.length} chunks</span>
        </div>
      </div>

      {/* Chunks Grid */}
      {paginatedChunks.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {paginatedChunks.map((chunk, idx) => {
            const isExpanded = expandedChunks[chunk.id] ?? expandedAll;
            const globalIndex = (currentPage - 1) * pageSize + idx + 1;

            return (
              <div
                key={chunk.id}
                className="glass-card p-5 rounded-2xl border border-slate-800/80 space-y-3 hover:border-blue-500/30 transition flex flex-col justify-between"
              >
                <div className="space-y-3">
                  {/* Top Bar */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-blue-400 bg-blue-950/80 px-2 py-0.5 rounded-lg border border-blue-800/50">
                        {chunk.id}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">#{globalIndex}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopy(chunk.id, chunk.text)}
                        className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition"
                        title="Copy chunk text"
                      >
                        {copiedId === chunk.id ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Metadata Pills */}
                  <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-400">
                    <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800 flex items-center gap-1">
                      <FileText className="w-3 h-3 text-slate-500" /> Page {chunk.page}
                    </span>
                    <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">
                      ~{chunk.approx_tokens} tokens
                    </span>
                    <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">
                      {chunk.char_count} chars
                    </span>
                  </div>

                  {/* Text Content */}
                  <div className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-900 font-mono text-xs text-slate-300 leading-relaxed">
                    <p className={isExpanded ? '' : 'line-clamp-4'}>{chunk.text}</p>
                  </div>
                </div>

                {/* Footer Action */}
                <div className="pt-2 flex items-center justify-between text-[11px] border-t border-slate-800/40">
                  <button
                    onClick={() => toggleExpand(chunk.id)}
                    className="text-purple-400 hover:text-purple-300 font-medium transition"
                  >
                    {isExpanded ? 'Show Less' : 'Show Full Text'}
                  </button>
                  <span className="text-slate-500 font-mono text-[10px]">Indexed for RAG</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-12 glass-card rounded-2xl border border-slate-800 text-xs text-slate-500">
          No chunks match your search query.
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-800 text-xs">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 disabled:opacity-30 transition flex items-center gap-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <span className="font-mono text-slate-400">
            Page {currentPage} of {totalPages}
          </span>

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 disabled:opacity-30 transition flex items-center gap-1"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

