import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  CopyCheck,
  Target,
  Layers,
  ArrowRight,
  Info,
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
import { EmptyState } from '../components/common/EmptyState';
import { MetricCard } from '../components/common/MetricCard';

export const Quality: React.FC = () => {
  const navigate = useNavigate();
  const { currentResult } = useDocument();

  if (!currentResult) {
    return (
      <EmptyState
        title="No Quality Evaluation Data"
        description="Please process or load a document to view real-time automated quality benchmarking, grounding audit scores, and duplicate detection."
        actionText="Go to Ingestion"
        onAction={() => navigate('/ingestion')}
      />
    );
  }

  const { evaluation } = currentResult;
  const {
    overall_health_score = 0,
    grounding_score = 0,
    redundancy_rate = 0,
    duplicate_pairs = [],
    quality_flags = [],
    per_qa_grounding = [],
    total_chunks_evaluated = currentResult.chunks.length,
    total_qa_evaluated = currentResult.knowledge.qa_dataset.length,
  } = evaluation;

  // Real data for Quality breakdown chart
  const qualityChartData = [
    { metric: 'Overall Health', score: overall_health_score, fill: '#10b981' },
    { metric: 'Citation Grounding', score: grounding_score, fill: '#8b5cf6' },
    { metric: 'Uniqueness (100 - Redundancy)', score: Math.max(0, 100 - redundancy_rate), fill: '#3b82f6' },
  ];

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">Quality & Evaluation Benchmark</h2>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                overall_health_score >= 80
                  ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/40'
                  : 'bg-amber-950/60 text-amber-300 border-amber-800/40'
              }`}
            >
              Health: {overall_health_score}%
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Grounded citation verification and TF-IDF / Jaccard redundancy benchmarking for{' '}
            <strong className="text-slate-200">{currentResult.document_name}</strong>.
          </p>
        </div>

        <button
          onClick={() => navigate('/exports')}
          className="px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-purple-600/20 transition self-start sm:self-auto"
        >
          <span>Export Certified Dataset</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Overall Knowledge Health"
          value={`${overall_health_score}%`}
          subtitle="Weighted groundability & uniqueness"
          icon={ShieldCheck}
          color="emerald"
          badge={overall_health_score >= 75 ? 'Production Grade' : 'Review Needed'}
        />
        <MetricCard
          title="Citation Grounding Score"
          value={`${grounding_score}%`}
          subtitle="Verified against origin chunks"
          icon={Target}
          color="purple"
          badge={`${total_qa_evaluated} QA evaluated`}
        />
        <MetricCard
          title="Redundancy / Duplicate Rate"
          value={`${redundancy_rate}%`}
          subtitle="Pairwise Jaccard > 45%"
          icon={CopyCheck}
          color={redundancy_rate > 15 ? 'amber' : 'blue'}
          badge={`${total_chunks_evaluated} chunks evaluated`}
        />
      </div>

      {/* Quality Score Breakdown Chart */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm text-slate-200">Evaluation Component Breakdown</h3>
            <p className="text-[11px] text-slate-500">Real performance scores measured against source documents</p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">Scale: 0 - 100%</span>
        </div>

        <div className="h-56 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={qualityChartData} layout="vertical" margin={{ top: 10, right: 30, left: 60, bottom: 10 }}>
              <XAxis type="number" domain={[0, 100]} stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis type="category" dataKey="metric" stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '12px',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="score" radius={[0, 6, 6, 0]}>
                {qualityChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quality Flags & Warnings */}
      {quality_flags && quality_flags.length > 0 && (
        <div className="glass-card p-5 rounded-2xl border border-amber-800/40 bg-amber-950/20 space-y-2">
          <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Active Quality Flags Detected</span>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {quality_flags.map((flag, idx) => (
              <span
                key={idx}
                className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-amber-900/40 text-amber-200 border border-amber-700/50"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Duplicate Pairs Section */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <CopyCheck className="w-4 h-4 text-amber-400" />
            <span>Duplicate & Redundant Chunk Pairs</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {duplicate_pairs.length} Flagged Pairs
          </span>
        </div>

        {duplicate_pairs.length > 0 ? (
          <div className="space-y-3">
            {duplicate_pairs.map((dup, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-amber-900/40 bg-amber-950/15 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-amber-300">
                      {dup.chunk_a} ↔ {dup.chunk_b}
                    </span>
                    <span className="text-[10px] font-mono text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-800/50">
                      {dup.similarity}% similarity
                    </span>
                  </div>
                  {dup.preview && (
                    <p className="text-xs text-slate-400 line-clamp-1 font-mono">
                      {dup.preview}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => navigate('/chunks')}
                  className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium self-start sm:self-auto transition shrink-0"
                >
                  Inspect in Chunks
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-emerald-800/40 bg-emerald-950/20 text-xs text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Clean dataset! Zero redundant or overlapping chunk pairs detected above threshold (45%).</span>
          </div>
        )}
      </div>

      {/* Per-QA Grounding Traceability Audit */}
      {per_qa_grounding && per_qa_grounding.length > 0 && (
        <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Target className="w-4 h-4 text-purple-400" />
              <span>Grounding Audit Traceability Log</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {per_qa_grounding.filter((p) => p.valid).length} / {per_qa_grounding.length} Grounded
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 font-medium">
                  <th className="pb-3 pl-1">QA ID</th>
                  <th className="pb-3">Referenced Citation</th>
                  <th className="pb-3">Token Overlap</th>
                  <th className="pb-3 text-right pr-1">Grounding Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {per_qa_grounding.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/30 transition">
                    <td className="py-2.5 pl-1 font-mono font-bold text-purple-400">{item.qa_id}</td>
                    <td className="py-2.5 font-mono text-slate-300">{item.citation}</td>
                    <td className="py-2.5 font-mono text-slate-400">{item.overlap_count} token matches</td>
                    <td className="py-2.5 text-right pr-1">
                      {item.valid ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-300 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Grounded
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
                          <AlertTriangle className="w-3 h-3 text-amber-400" /> Unverified
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

