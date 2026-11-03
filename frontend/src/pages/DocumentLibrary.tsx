import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderArchive,
  FileText,
  Search,
  Trash2,
  ExternalLink,
  Layers,
  Clock,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';
import { EmptyState } from '../components/common/EmptyState';
import { ConfirmModal } from '../components/common/EmptyState';

export const DocumentLibrary: React.FC = () => {
  const navigate = useNavigate();
  const { documents, loadDocument, deleteDocument, refreshDocuments, activeDocId } = useDocument();
  const { showToast } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [docToDelete, setDocToDelete] = useState<{ id: string; name: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Filter documents
  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenDoc = async (id: string) => {
    const loaded = await loadDocument(id);
    if (loaded) {
      navigate('/knowledge');
    }
  };

  const handleConfirmDelete = async () => {
    if (!docToDelete) return;
    try {
      setIsDeleting(true);
      await deleteDocument(docToDelete.id);
      setDocToDelete(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await refreshDocuments();
    setIsRefreshing(false);
    showToast('Document library refreshed', 'info');
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">Document Library</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-950/60 text-purple-300 border border-purple-800/40">
              {documents.length} Stored in SQLite
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Browse, manage, and reopen previously synthesized knowledge graphs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh documents"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-purple-400' : ''}`} />
          </button>
          <button
            onClick={() => navigate('/ingestion')}
            className="px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-purple-600/20 transition"
          >
            <span>Ingest New Document</span>
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter documents by filename..."
          className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 transition"
        />
      </div>

      {/* Documents Table / Grid */}
      {documents.length === 0 ? (
        <EmptyState
          icon={FolderArchive}
          title="No Processed Documents Found"
          description="You haven't processed any documents yet. Ingest your first PDF/DOCX or load the sample paper to create persistent knowledge records."
          actionText="Ingest First Document"
          onAction={() => navigate('/ingestion')}
        />
      ) : filteredDocs.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-2xl border border-slate-800 text-xs text-slate-500">
          No documents match &quot;{searchQuery}&quot;.
        </div>
      ) : (
        <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-medium">
                  <th className="py-3.5 pl-5">Document Name</th>
                  <th className="py-3.5 px-3">Size</th>
                  <th className="py-3.5 px-3">Pages</th>
                  <th className="py-3.5 px-3">Chunks</th>
                  <th className="py-3.5 px-3">Model</th>
                  <th className="py-3.5 px-3">Processed Date</th>
                  <th className="py-3.5 pr-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredDocs.map((doc) => {
                  const isActive = activeDocId === doc.id;
                  const dateStr = doc.upload_timestamp
                    ? new Date(doc.upload_timestamp).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : 'Unknown';

                  return (
                    <tr
                      key={doc.id}
                      className={`hover:bg-slate-900/40 transition group ${
                        isActive ? 'bg-purple-950/20' : ''
                      }`}
                    >
                      <td className="py-4 pl-5">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-purple-600/15 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                            <FileText className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-200 line-clamp-1" title={doc.filename}>
                              {doc.filename}
                            </p>
                            {isActive && (
                              <span className="text-[10px] font-mono text-emerald-400">
                                Currently Active
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-3 font-mono text-slate-400">
                        {doc.size_bytes ? `${(doc.size_bytes / 1024).toFixed(1)} KB` : '--'}
                      </td>

                      <td className="py-4 px-3 text-slate-300 font-mono">{doc.page_count}</td>

                      <td className="py-4 px-3 text-slate-300 font-mono font-semibold text-blue-400">
                        {doc.chunk_count}
                      </td>

                      <td className="py-4 px-3">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                          {doc.model_used || 'sarvam-105b'}
                        </span>
                      </td>

                      <td className="py-4 px-3 text-slate-500 text-[11px] whitespace-nowrap">
                        {dateStr}
                      </td>

                      <td className="py-4 pr-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenDoc(doc.id)}
                            className="px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-xs font-medium transition flex items-center gap-1"
                          >
                            <span>Open</span>
                            <ExternalLink className="w-3 h-3" />
                          </button>

                          <button
                            onClick={() => setDocToDelete({ id: doc.id, name: doc.filename })}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 transition"
                            title="Delete document"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={!!docToDelete}
        title="Delete Stored Document?"
        message={`Are you sure you want to permanently delete "${docToDelete?.name}"? This will remove all associated chunks, generated knowledge, and evaluation logs from SQLite storage.`}
        confirmText={isDeleting ? 'Deleting...' : 'Delete Permanently'}
        danger
        onCancel={() => setDocToDelete(null)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
};
