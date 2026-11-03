import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  Sliders,
  Play,
  Eye,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useDocument } from '../contexts/DocumentContext';
import { useToast } from '../contexts/ToastContext';
import {
  processDocumentUpload,
  previewDocumentChunks,
  loadSampleDocument,
  getErrorMessage,
} from '../services/api';
import { Chunk } from '../types';

export const Ingestion: React.FC = () => {
  const navigate = useNavigate();
  const { setResult, refreshDocuments, serverStatus } = useDocument();
  const { showToast } = useToast();

  // File state
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Configuration Sliders
  const [chunkSize, setChunkSize] = useState<number>(600);
  const [overlap, setOverlap] = useState<number>(100);
  const [numFacts, setNumFacts] = useState<number>(3);
  const [numQAPairs, setNumQAPairs] = useState<number>(3);
  const [selectedModel, setSelectedModel] = useState<string>('sarvam-105b');
  const [showAdvanced, setShowAdvanced] = useState<boolean>(true);

  // Processing state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingStage, setProcessingStage] = useState<string>('');
  const [previewChunks, setPreviewChunks] = useState<Chunk[]>([]);
  const [isPreviewing, setIsPreviewing] = useState<boolean>(false);

  const allowedExtensions = ['.pdf', '.docx', '.txt', '.md'];

  const validateFile = (selectedFile: File): boolean => {
    const ext = '.' + selectedFile.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      showToast(`Invalid file type "${ext}". Please upload PDF, DOCX or TXT.`, 'error');
      return false;
    }
    // 20 MB size limit
    if (selectedFile.size > 20 * 1024 * 1024) {
      showToast('File exceeds 20MB maximum size limit.', 'error');
      return false;
    }
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (validateFile(selected)) {
        setFile(selected);
        setPreviewChunks([]);
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      if (validateFile(selected)) {
        setFile(selected);
        setPreviewChunks([]);
      }
    }
  };

  // 1. Preview Chunks before running Sarvam
  const handlePreviewChunks = async () => {
    if (!file) {
      showToast('Select a document first to preview chunks', 'warning');
      return;
    }

    const isTextFile = file.name.endsWith('.txt') || file.name.endsWith('.md');
    if (!isTextFile) {
      showToast(
        'Instant client preview is available for TXT/MD files. For PDF/DOCX, click "Process Pipeline" below!',
        'info'
      );
      return;
    }

    try {
      setIsPreviewing(true);
      showToast('Segmenting text into boundary-aware chunks...', 'info');
      const text = await file.text();
      const res = await previewDocumentChunks(text, chunkSize, overlap);
      setPreviewChunks(res.chunks);
      showToast(`Preview ready: ${res.total_chunks} chunks generated`, 'success');
    } catch (err) {
      showToast(`Preview failed: ${getErrorMessage(err)}`, 'error');
    } finally {
      setIsPreviewing(false);
    }
  };

  // 2. Process Full Pipeline
  const handleProcessPipeline = async () => {
    if (!file) {
      showToast('Please select or upload a document first', 'warning');
      return;
    }

    try {
      setIsProcessing(true);
      setProcessingStage('1/3 Extracting & Boundary-Aware Chunking...');

      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', selectedModel);
      formData.append('chunk_size', String(chunkSize));
      formData.append('overlap', String(overlap));
      formData.append('num_facts', String(numFacts));
      formData.append('num_qa_pairs', String(numQAPairs));

      // Stage 2 update after a short delay
      setTimeout(() => {
        setProcessingStage('2/3 Sarvam AI Map-Reduce Distillation...');
      }, 1500);

      const result = await processDocumentUpload(formData);

      setProcessingStage('3/3 Quality Benchmarking & Persisting to SQLite...');
      setResult(result);
      await refreshDocuments();

      showToast(`Document "${result.document_name}" successfully processed!`, 'success');
      navigate('/knowledge');
    } catch (err) {
      showToast(`Processing failed: ${getErrorMessage(err)}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
    }
  };

  // 3. Load Sample Document
  const handleLoadSample = async () => {
    try {
      setIsProcessing(true);
      setProcessingStage('Synthesizing sample technical paper via Sarvam AI...');
      const result = await loadSampleDocument({
        model: selectedModel,
        num_facts: numFacts,
        num_qa_pairs: numQAPairs,
      });
      setResult(result);
      await refreshDocuments();
      showToast('Sample document loaded & synthesized!', 'success');
      navigate('/knowledge');
    } catch (err) {
      showToast(`Failed loading sample: ${getErrorMessage(err)}`, 'error');
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Document Ingestion & Synthesis</h2>
          <p className="text-xs text-slate-400 mt-1">
            Upload technical documents, adjust boundary-aware segmentation parameters, and run knowledge synthesis.
          </p>
        </div>
        <button
          onClick={handleLoadSample}
          disabled={isProcessing}
          className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50 shrink-0"
        >
          <Sparkles className="w-4 h-4 text-purple-400" />
          <span>Load Sample Document</span>
        </button>
      </div>

      {/* Upload Dropzone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`glass-card p-8 sm:p-12 rounded-3xl border-2 border-dashed transition-all duration-300 cursor-pointer flex flex-col items-center justify-center text-center ${
          isDragging
            ? 'border-purple-500 bg-purple-950/20 scale-[1.01]'
            : file
            ? 'border-purple-500/40 bg-purple-950/10'
            : 'border-slate-800 hover:border-slate-700 bg-slate-950/40'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="w-16 h-16 rounded-2xl bg-purple-600/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mb-4 transition-transform hover:scale-105">
          <UploadCloud className="w-8 h-8" />
        </div>

        {file ? (
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/80 border border-purple-800/50 text-xs font-medium text-purple-300">
              <FileText className="w-3.5 h-3.5 text-purple-400" />
              <span>{file.name}</span>
            </div>
            <p className="text-[11px] text-slate-400">
              {(file.size / 1024).toFixed(1)} KB • Click or drag another file to replace
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-slate-200">
              Drag & drop your document here, or <span className="text-purple-400">browse</span>
            </p>
            <p className="text-[11px] text-slate-500">
              Supports <strong className="text-slate-400">PDF, DOCX, TXT, MD</strong> up to 20MB
            </p>
          </div>
        )}
      </div>

      {/* Advanced Chunking & Knowledge Generation Controls */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <div
          onClick={() => setShowAdvanced((prev) => !prev)}
          className="p-4 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between cursor-pointer hover:bg-slate-900 transition"
        >
          <div className="flex items-center gap-2.5">
            <Sliders className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-semibold text-slate-200">
              Segmentation & Knowledge Synthesis Parameters
            </span>
          </div>
          <button className="text-slate-400 hover:text-white">
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {showAdvanced && (
          <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Chunk Size Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <label className="font-medium text-slate-300">Target Chunk Size</label>
                <span className="font-mono text-purple-400 font-bold">{chunkSize} chars</span>
              </div>
              <input
                type="range"
                min="200"
                max="1000"
                step="50"
                value={chunkSize}
                onChange={(e) => setChunkSize(Number(e.target.value))}
                className="w-full accent-purple-600 bg-slate-800 h-1.5 rounded-lg cursor-pointer"
              />
              <p className="text-[11px] text-slate-500">Recommended 500-700 for technical documents.</p>
            </div>

            {/* Overlap Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <label className="font-medium text-slate-300">Sentence Overlap</label>
                <span className="font-mono text-blue-400 font-bold">{overlap} chars</span>
              </div>
              <input
                type="range"
                min="0"
                max="200"
                step="20"
                value={overlap}
                onChange={(e) => setOverlap(Number(e.target.value))}
                className="w-full accent-blue-600 bg-slate-800 h-1.5 rounded-lg cursor-pointer"
              />
              <p className="text-[11px] text-slate-500">Preserves complete sentence context between boundaries.</p>
            </div>

            {/* Num Facts */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <label className="font-medium text-slate-300">Facts Target Count</label>
                <span className="font-mono text-emerald-400 font-bold">{numFacts} facts</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                step="1"
                value={numFacts}
                onChange={(e) => setNumFacts(Number(e.target.value))}
                className="w-full accent-emerald-600 bg-slate-800 h-1.5 rounded-lg cursor-pointer"
              />
              <p className="text-[11px] text-slate-500">Number of structured concept facts to extract per batch.</p>
            </div>

            {/* Num QA Pairs */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <label className="font-medium text-slate-300">Synthetic Q&A Pairs</label>
                <span className="font-mono text-amber-400 font-bold">{numQAPairs} pairs</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                step="1"
                value={numQAPairs}
                onChange={(e) => setNumQAPairs(Number(e.target.value))}
                className="w-full accent-amber-600 bg-slate-800 h-1.5 rounded-lg cursor-pointer"
              />
              <p className="text-[11px] text-slate-500">Number of instruction fine-tuning pairs to generate.</p>
            </div>

            {/* Model Selector */}
            <div className="space-y-2 sm:col-span-2 pt-2 border-t border-slate-800/80">
              <label className="block text-xs font-medium text-slate-300">Target Sarvam AI Model</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div
                  onClick={() => setSelectedModel('sarvam-105b')}
                  className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                    selectedModel === 'sarvam-105b'
                      ? 'border-purple-500 bg-purple-950/30'
                      : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <p className="text-xs font-semibold text-white">sarvam-105b</p>
                    <p className="text-[10px] text-slate-400">High-capacity reasoning & knowledge synthesis</p>
                  </div>
                  {selectedModel === 'sarvam-105b' && <CheckCircle2 className="w-4 h-4 text-purple-400" />}
                </div>

                <div
                  onClick={() => setSelectedModel('sarvam-105b-conversations')}
                  className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                    selectedModel === 'sarvam-105b-conversations'
                      ? 'border-purple-500 bg-purple-950/30'
                      : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <p className="text-xs font-semibold text-white">sarvam-105b-conversations</p>
                    <p className="text-[10px] text-slate-400">Optimized for dialogue & conversational Q&A</p>
                  </div>
                  {selectedModel === 'sarvam-105b-conversations' && (
                    <CheckCircle2 className="w-4 h-4 text-purple-400" />
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <button
          onClick={handlePreviewChunks}
          disabled={!file || isPreviewing || isProcessing}
          className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold flex items-center justify-center gap-2 transition disabled:opacity-40"
        >
          <Eye className="w-4 h-4 text-blue-400" />
          <span>{isPreviewing ? 'Segmenting...' : 'Preview Chunks (0 Credits)'}</span>
        </button>

        <button
          onClick={handleProcessPipeline}
          disabled={!file || isProcessing}
          className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-purple-600/25 transition disabled:opacity-50"
        >
          <Play className="w-4 h-4" />
          <span>{isProcessing ? 'Processing Pipeline...' : 'Process Pipeline with Sarvam AI'}</span>
        </button>
      </div>

      {/* Live Processing Stepper Status */}
      {isProcessing && (
        <div className="glass-card p-6 rounded-2xl border border-purple-500/40 bg-purple-950/20 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-purple-300 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
              {processingStage}
            </span>
            <span className="font-mono text-purple-400 text-[11px]">Sarvam 105B Active</span>
          </div>
          <div className="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
            <div className="bg-gradient-to-r from-purple-500 to-indigo-500 h-full w-2/3 animate-pulse" />
          </div>
        </div>
      )}

      {/* Chunks Preview Section (if generated) */}
      {previewChunks.length > 0 && (
        <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-400" />
                Segmentation Preview ({previewChunks.length} Chunks)
              </h3>
              <p className="text-[11px] text-slate-500">
                Generated locally using boundary-aware sentence segmentation without invoking LLM tokens.
              </p>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
              Ready to Process
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
            {previewChunks.slice(0, 6).map((c) => (
              <div key={c.id} className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 space-y-2">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-mono font-bold text-blue-400">{c.id}</span>
                  <div className="flex gap-2 text-slate-500 font-mono">
                    <span>Page {c.page}</span>
                    <span>~{c.approx_tokens} tokens</span>
                  </div>
                </div>
                <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed font-mono bg-slate-950/60 p-2 rounded border border-slate-900">
                  {c.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
