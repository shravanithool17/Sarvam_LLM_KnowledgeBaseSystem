import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Database,
  Check,
  Eye,
  ExternalLink,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';
import { downloadExportFile, getErrorMessage } from '../services/api';
import { EmptyState } from '../components/common/EmptyState';

export const ExportCenter: React.FC = () => {
  const navigate = useNavigate();
  const { currentResult } = useDocument();
  const { showToast } = useToast();

  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [previewFormat, setPreviewFormat] = useState<'jsonl' | 'json' | 'csv' | 'markdown' | null>(null);

  if (!currentResult) {
    return (
      <EmptyState
        title="No Document to Export"
        description="Please ingest or load a document first to export fine-tuning datasets, structured vector indices, or CSV spreadsheets."
        actionText="Go to Ingestion"
        onAction={() => navigate('/ingestion')}
      />
    );
  }

  const exportFormats = [
    {
      id: 'jsonl',
      name: 'Hugging Face / Alpaca JSONL',
      ext: '.jsonl',
      icon: Database,
      color: 'purple',
      description:
        'Standard instruction-tuning format with instruction, response, and grounded citations for Unsloth, LLaMA-Factory, or OpenAI fine-tuning.',
      recommended: true,
    },
    {
      id: 'json',
      name: 'Unified Knowledge Graph JSON',
      ext: '.json',
      icon: FileCode,
      color: 'indigo',
      description:
        'Hierarchical JSON containing all chunks, metadata, extracted entity facts, summary, and quality benchmarks for vector DB ingestion.',
    },
    {
      id: 'csv',
      name: 'Tabular Q&A Spreadsheet CSV',
      ext: '.csv',
      icon: FileSpreadsheet,
      color: 'emerald',
      description:
        'Formatted CSV spreadsheet for human annotation, regulatory auditing, and team review.',
    },
    {
      id: 'markdown',
      name: 'Knowledge Brief Markdown',
      ext: '.md',
      icon: FileText,
      color: 'blue',
      description:
        'Comprehensive technical report containing executive summary, categorized facts table, and Q&A catalog formatted in clean GitHub Markdown.',
    },
  ];

  const handleDownload = async (formatId: string) => {
    try {
      setDownloadingFormat(formatId);
      showToast(`Generating ${formatId.toUpperCase()} export...`, 'info');

      // Call backend export endpoint
      const blob = await downloadExportFile(formatId, currentResult);

      // Trigger browser download
      const filename = `${currentResult.document_name.replace(/\.[^/.]+$/, '')}_knowledge.${formatId === 'markdown' ? 'md' : formatId}`;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      showToast(`Downloaded ${filename} successfully!`, 'success');
    } catch (err) {
      showToast(`Export failed: ${getErrorMessage(err)}`, 'error');
    } finally {
      setDownloadingFormat(null);
    }
  };

  const getPreviewContent = (format: string): string => {
    if (format === 'jsonl') {
      return (currentResult.knowledge.qa_dataset || [])
        .map((qa) =>
          JSON.stringify({
            instruction: qa.instruction,
            response: qa.response,
            citation: qa.citation,
            source_document: currentResult.document_name,
          })
        )
        .join('\n');
    }
    if (format === 'json') {
      return JSON.stringify(currentResult, null, 2);
    }
    if (format === 'csv') {
      const rows = ['ID,Instruction,Response,Citation'];
      (currentResult.knowledge.qa_dataset || []).forEach((qa) => {
        rows.push(
          `${qa.id || ''},"${(qa.instruction || '').replace(/"/g, '""')}","${(qa.response || '').replace(
            /"/g,
            '""'
          )}",${qa.citation || ''}`
        );
      });
      return rows.join('\n');
    }
    if (format === 'markdown') {
      return `# Knowledge Brief: ${currentResult.document_name}

## Executive Summary
${currentResult.knowledge.summary}

## Extracted Facts
${(currentResult.knowledge.facts || [])
  .map((f) => `- **${f.entity}** (${f.category}): ${f.fact} [${f.citation}]`)
  .join('\n')}

## Instruction Q&A Dataset
${(currentResult.knowledge.qa_dataset || [])
  .map((qa) => `### ${qa.instruction}\n> ${qa.response}\n*Citation: ${qa.citation}*\n`)
  .join('\n')}`;
    }
    return '';
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Structured Knowledge Export Center</h2>
          <p className="text-xs text-slate-400 mt-1">
            Export structured datasets for <strong className="text-slate-200">{currentResult.document_name}</strong>{' '}
            into AI-ready instruction tuning, vector database, or spreadsheet formats.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-purple-400 bg-purple-950/60 px-2.5 py-1 rounded-lg border border-purple-800/40">
            {currentResult.knowledge.qa_dataset.length} QA • {currentResult.chunks.length} Chunks
          </span>
        </div>
      </div>

      {/* Format Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {exportFormats.map((fmt) => {
          const Icon = fmt.icon;
          const isDownloading = downloadingFormat === fmt.id;

          return (
            <div
              key={fmt.id}
              className="glass-card p-6 rounded-2xl border border-slate-800/80 space-y-4 flex flex-col justify-between hover:border-purple-500/30 transition group"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-600/15 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-sm text-slate-100">{fmt.name}</h4>
                      <span className="text-[10px] font-mono text-slate-500">{fmt.ext} file</span>
                    </div>
                  </div>

                  {fmt.recommended && (
                    <span className="text-[9px] font-mono uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800/60 shrink-0">
                      Recommended
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">{fmt.description}</p>
              </div>

              <div className="pt-2 flex items-center gap-2">
                <button
                  onClick={() => setPreviewFormat(previewFormat === fmt.id ? null : (fmt.id as any))}
                  className="px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>{previewFormat === fmt.id ? 'Close' : 'Preview'}</span>
                </button>

                <button
                  onClick={() => handleDownload(fmt.id)}
                  disabled={isDownloading}
                  className="flex-1 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-md shadow-purple-600/20 transition disabled:opacity-50"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>{isDownloading ? 'Generating...' : `Download ${fmt.ext}`}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Preview Modal / Card */}
      {previewFormat && (
        <div className="glass-card p-6 rounded-2xl border border-purple-500/40 bg-purple-950/10 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-purple-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5" />
              {previewFormat.toUpperCase()} Format Preview
            </span>
            <button
              onClick={() => setPreviewFormat(null)}
              className="text-xs text-slate-400 hover:text-white"
            >
              Close Preview
            </button>
          </div>

          <pre className="p-4 rounded-xl bg-slate-950/80 border border-slate-900 font-mono text-[11px] text-slate-300 max-h-72 overflow-y-auto whitespace-pre-wrap leading-relaxed">
            {getPreviewContent(previewFormat)}
          </pre>
        </div>
      )}
    </div>
  );
};
