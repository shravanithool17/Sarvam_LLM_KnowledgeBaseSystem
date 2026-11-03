import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Layers,
  Sparkles,
  HelpCircle,
  ShieldCheck,
  Server,
  ArrowRight,
  UploadCloud,
  MessageSquare,
  Download,
  Clock,
  HardDrive,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { useDocument } from '../contexts/DocumentContext';
import { MetricCard } from '../components/common/MetricCard';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { currentResult, documents, healthCheck, serverStatus, loadDocument } = useDocument();

  // Compute metrics from real state
  const totalDocs = documents.length;
  const totalChunksStored = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const activeFactsCount = currentResult?.knowledge.facts.length ?? 0;
  const activeQACount = currentResult?.knowledge.qa_dataset.length ?? 0;
  const activeQualityScore = currentResult?.evaluation.overall_health_score ?? null;

  // Chart data: Documents vs Chunk count (real data)
  const docChartData = documents.slice(0, 6).map((doc) => ({
    name: doc.filename.length > 15 ? doc.filename.substring(0, 15) + '...' : doc.filename,
    chunks: doc.chunk_count,
    pages: doc.page_count,
  }));

  // Chart data: Facts by Category in active document
  const categoryCounts = (currentResult?.knowledge.facts || []).reduce<Record<string, number>>((acc, f) => {
    const cat = f.category || 'Concept';
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {});

  const categoryChartData = Object.entries(categoryCounts).map(([cat, count]) => ({
    category: cat,
    count,
  }));

  const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ec4899'];

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="glass-card p-6 sm:p-8 rounded-3xl border border-slate-800 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-800/40 text-[11px] text-purple-300 font-mono">
              <Sparkles className="w-3 h-3 text-purple-400" />
              <span>Platform v2.0 • Sarvam-105B Engine</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              AI Knowledge Engineering Suite
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Transform unstructured technical documents into high-grade, hallucination-resistant knowledge
              datasets, instruction fine-tuning pairs, and verified RAG vector indices.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={() => navigate('/ingestion')}
              className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-purple-600/25 transition"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Ingest Document</span>
            </button>
            <button
              onClick={() => navigate('/search')}
              className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-2 transition"
            >
              <MessageSquare className="w-4 h-4 text-purple-400" />
              <span>Ask Document</span>
            </button>
          </div>
        </div>
      </div>

      {/* Real Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Stored Documents"
          value={totalDocs}
          subtitle="Persisted in SQLite"
          icon={FileText}
          color="purple"
          badge="SQLite WAL"
        />
        <MetricCard
          title="Total Chunks"
          value={totalChunksStored}
          subtitle="Boundary-aware segmented"
          icon={Layers}
          color="blue"
        />
        <MetricCard
          title="Extracted Facts"
          value={activeFactsCount}
          subtitle={currentResult ? 'Active document' : 'No active doc'}
          icon={Sparkles}
          color="emerald"
        />
        <MetricCard
          title="Instruction Q&A"
          value={activeQACount}
          subtitle="Fine-tuning pairs"
          icon={HelpCircle}
          color="amber"
        />
        <MetricCard
          title="Avg Quality Score"
          value={activeQualityScore !== null ? `${activeQualityScore}%` : '--'}
          subtitle={activeQualityScore !== null ? 'Grounded & validated' : 'Process to evaluate'}
          icon={ShieldCheck}
          color="emerald"
        />
      </div>

      {/* Visual Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document Chunk Distribution Chart */}
        <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-sm text-slate-200">Document Volume & Chunks</h3>
              <p className="text-[11px] text-slate-500">Stored chunk segmentation count by document</p>
            </div>
            <span className="text-[11px] font-mono text-purple-400 bg-purple-950/40 px-2 py-0.5 rounded border border-purple-800/40">
              {documents.length} Records
            </span>
          </div>

          {docChartData.length > 0 ? (
            <div className="h-64 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={docChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="chunks" fill="#8b5cf6" radius={[6, 6, 0, 0]}>
                    {docChartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-slate-500 text-xs">
              <Layers className="w-8 h-8 mb-2 opacity-40" />
              <span>No documents processed yet. Click &quot;Ingest Document&quot; to begin.</span>
            </div>
          )}
        </div>

        {/* System Diagnostics & Health Card */}
        <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
              <Server className="w-4 h-4 text-purple-400" />
              System Diagnostics
            </h3>
            <p className="text-[11px] text-slate-500">FastAPI backend & Sarvam AI connectivity</p>
          </div>

          <div className="space-y-3">
            {/* Sarvam AI Status */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/70 flex items-center justify-between text-xs">
              <span className="text-slate-400">Sarvam AI API</span>
              <span
                className={`font-mono text-[11px] px-2 py-0.5 rounded ${
                  serverStatus?.has_key
                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40'
                    : 'bg-amber-950/60 text-amber-300 border border-amber-800/40'
                }`}
              >
                {serverStatus?.has_key ? 'Connected (Key OK)' : 'Simulated'}
              </span>
            </div>

            {/* Model Target */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/70 flex items-center justify-between text-xs">
              <span className="text-slate-400">Target Model</span>
              <span className="font-mono text-[11px] text-purple-300">
                {serverStatus?.default_model || 'sarvam-105b'}
              </span>
            </div>

            {/* Storage Engine */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/70 flex items-center justify-between text-xs">
              <span className="text-slate-400">Storage Backend</span>
              <span className="font-mono text-[11px] text-emerald-300 flex items-center gap-1">
                <HardDrive className="w-3 h-3" /> SQLite WAL
              </span>
            </div>

            {/* Uptime */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/70 flex items-center justify-between text-xs">
              <span className="text-slate-400">Server Uptime</span>
              <span className="font-mono text-[11px] text-slate-300 flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                {healthCheck?.uptime_seconds ? `${healthCheck.uptime_seconds}s` : 'Active'}
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate('/settings')}
            className="w-full py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium flex items-center justify-center gap-1.5 transition"
          >
            <span>View Full Diagnostics</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Active Knowledge Fact Categories (if document active) */}
      {categoryChartData.length > 0 && (
        <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-sm text-slate-200">
                Active Document Knowledge Categories ({currentResult?.document_name})
              </h3>
              <p className="text-[11px] text-slate-500">Distribution of structured facts by category</p>
            </div>
            <button
              onClick={() => navigate('/knowledge')}
              className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
            >
              <span>Explore Knowledge</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {categoryChartData.map((item, i) => (
              <div
                key={item.category}
                className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/50 flex items-center justify-between"
              >
                <div>
                  <p className="text-[11px] text-slate-400 font-medium">{item.category}</p>
                  <p className="text-lg font-bold text-white mt-0.5">{item.count}</p>
                </div>
                <div
                  className="w-2.5 h-8 rounded-full"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Processing Activity Table */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm text-slate-200">Recent Documents Library</h3>
            <p className="text-[11px] text-slate-500">Persisted documents ready for RAG inspection & export</p>
          </div>
          <button
            onClick={() => navigate('/documents')}
            className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 font-medium"
          >
            <span>View All ({documents.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {documents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 font-medium">
                  <th className="pb-3 pl-1">Document Name</th>
                  <th className="pb-3">Pages</th>
                  <th className="pb-3">Chunks</th>
                  <th className="pb-3">Model</th>
                  <th className="pb-3">Processed</th>
                  <th className="pb-3 text-right pr-1">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {documents.slice(0, 5).map((doc) => (
                  <tr key={doc.id} className="group hover:bg-slate-900/40 transition">
                    <td className="py-3 pl-1 font-medium text-slate-200 flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                      <span className="truncate max-w-[200px]" title={doc.filename}>
                        {doc.filename}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400">{doc.page_count}</td>
                    <td className="py-3 text-slate-400 font-mono">{doc.chunk_count}</td>
                    <td className="py-3">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                        {doc.model_used || 'sarvam-105b'}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500">
                      {new Date(doc.upload_timestamp).toLocaleDateString()}
                    </td>
                    <td className="py-3 text-right pr-1">
                      <button
                        onClick={async () => {
                          await loadDocument(doc.id);
                          navigate('/knowledge');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 font-medium transition"
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 text-xs">
            No documents processed yet. Click &quot;Ingest Document&quot; above to process your first file.
          </div>
        )}
      </div>

      {/* Quick Actions Footer Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          onClick={() => navigate('/ingestion')}
          className="glass-card p-5 rounded-2xl border border-slate-800 hover:border-purple-500/40 cursor-pointer transition group"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center shrink-0 group-hover:scale-110 transition">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-xs text-white">Ingest New File</h4>
              <p className="text-[11px] text-slate-400">PDF, DOCX or TXT with boundary chunking</p>
            </div>
          </div>
        </div>

        <div
          onClick={() => navigate('/search')}
          className="glass-card p-5 rounded-2xl border border-slate-800 hover:border-blue-500/40 cursor-pointer transition group"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center shrink-0 group-hover:scale-110 transition">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-xs text-white">Conversational RAG</h4>
              <p className="text-[11px] text-slate-400">Ask questions with grounded chunk citations</p>
            </div>
          </div>
        </div>

        <div
          onClick={() => navigate('/exports')}
          className="glass-card p-5 rounded-2xl border border-slate-800 hover:border-emerald-500/40 cursor-pointer transition group"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center shrink-0 group-hover:scale-110 transition">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-xs text-white">Export Dataset</h4>
              <p className="text-[11px] text-slate-400">Download JSONL, JSON, CSV or Markdown</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
