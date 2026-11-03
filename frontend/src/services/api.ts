import axios, { AxiosError } from 'axios';
import {
  ServerStatus,
  HealthCheck,
  PipelineResult,
  DocumentMetadata,
  RAGResponse,
  Chunk,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Accept': 'application/json',
  },
  timeout: 180000, // 3 minutes timeout for heavy LLM operations
});

// Format API error messages
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<{ error?: string; detail?: string; message?: string }>;
    if (axiosErr.response?.data) {
      const data = axiosErr.response.data;
      return data.error || data.detail || data.message || `Request failed (${axiosErr.response.status})`;
    }
    if (axiosErr.code === 'ECONNABORTED') {
      return 'Request timed out while waiting for Sarvam AI to synthesize the document.';
    }
    return axiosErr.message || 'Network error connecting to backend.';
  }
  return error instanceof Error ? error.message : 'An unknown error occurred';
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export async function fetchServerStatus(): Promise<ServerStatus> {
  const res = await api.get<ServerStatus>('/api/status');
  return res.data;
}

export async function fetchHealthCheck(): Promise<HealthCheck> {
  const res = await api.get<HealthCheck>('/api/health');
  return res.data;
}

export async function loadSampleDocument(params?: {
  model?: string;
  num_facts?: number;
  num_qa_pairs?: number;
  api_key?: string;
}): Promise<PipelineResult> {
  const res = await api.post<PipelineResult>('/api/sample', {
    model: params?.model || 'sarvam-105b',
    num_facts: params?.num_facts ?? 3,
    num_qa_pairs: params?.num_qa_pairs ?? 3,
    ...(params?.api_key ? { api_key: params.api_key } : {}),
  });
  return res.data;
}

export async function processDocumentUpload(formData: FormData): Promise<PipelineResult> {
  const res = await api.post<PipelineResult>('/api/process', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
}

export async function previewDocumentChunks(
  text: string,
  chunkSize: number = 600,
  overlap: number = 100
): Promise<{ chunks: Chunk[]; total_chunks: number }> {
  const res = await api.post<{ chunks: Chunk[]; total_chunks: number }>('/api/chunk-preview', {
    text: text.slice(0, 50000),
    chunk_size: chunkSize,
    overlap,
  });
  return res.data;
}

export async function queryRAG(params: {
  query: string;
  chunks: PipelineResult['chunks'];
  model?: string;
  api_key?: string;
}): Promise<RAGResponse> {
  const res = await api.post<RAGResponse>('/api/rag', {
    query: params.query,
    chunks: params.chunks,
    model: params.model || 'sarvam-105b',
    ...(params.api_key ? { api_key: params.api_key } : {}),
  });
  return res.data;
}

export async function fetchDocumentList(): Promise<DocumentMetadata[]> {
  const res = await api.get<{ documents?: DocumentMetadata[]; total?: number } | DocumentMetadata[]>('/api/documents');
  if (res.data && typeof res.data === 'object' && 'documents' in res.data && Array.isArray(res.data.documents)) {
    return res.data.documents;
  }
  return Array.isArray(res.data) ? res.data : [];
}

export async function fetchDocumentById(docId: string): Promise<PipelineResult> {
  const res = await api.get<PipelineResult>(`/api/documents/${docId}`);
  return res.data;
}

export async function deleteDocumentById(docId: string): Promise<{ deleted: boolean; doc_id: string }> {
  const res = await api.delete<{ deleted: boolean; doc_id: string }>(`/api/documents/${docId}`);
  return res.data;
}

export async function downloadExportFile(format: string, data: PipelineResult): Promise<Blob> {
  const res = await api.post(`/api/export/${format}`, data, {
    responseType: 'blob',
  });
  return res.data;
}
