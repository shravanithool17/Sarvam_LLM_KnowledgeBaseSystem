export interface Chunk {
  id: string;
  page: number;
  text: string;
  char_count: number;
  approx_tokens: number;
  word_count?: number;
}

export interface Fact {
  entity: string;
  category: string;
  fact: string;
  citation: string;
}

export interface QAPair {
  id: string;
  instruction: string;
  response: string;
  citation: string;
  confidence?: string;
}

export interface BatchProcessingStats {
  total_batches?: number;
  successful_batches?: number;
  failed_batches?: number;
  batch_count?: number;
}

export interface Knowledge {
  summary: string;
  facts: Fact[];
  qa_dataset: QAPair[];
  batch_processing_stats?: BatchProcessingStats;
  mode?: string;
}

export interface DuplicatePair {
  chunk_a: string;
  chunk_b: string;
  similarity: number;
  preview?: string;
}

export interface PerQAGrounding {
  qa_id: string;
  citation: string;
  valid: boolean;
  overlap_count: number;
}

export interface Evaluation {
  overall_health_score: number;
  grounding_score: number;
  redundancy_rate: number;
  duplicate_pairs: DuplicatePair[];
  quality_flags?: string[];
  per_qa_grounding?: PerQAGrounding[];
  total_chunks_evaluated?: number;
  total_qa_evaluated?: number;
}

export interface PipelineStats {
  total_pages: number;
  total_chars: number;
  total_chunks: number;
  word_count?: number;
}

export interface PipelineResult {
  document_id?: string;
  document_name: string;
  stats: PipelineStats;
  chunks: Chunk[];
  knowledge: Knowledge;
  evaluation: Evaluation;
  created_at?: string;
}

export interface DocumentMetadata {
  id: string;
  filename: string;
  size_bytes: number;
  upload_timestamp: string;
  page_count: number;
  chunk_count: number;
  status: string;
  model_used: string;
}

export interface ServerStatus {
  status: string;
  has_key: boolean;
  default_model: string;
  version?: string;
  valid_models?: string[];
  environment?: string;
}

export interface HealthCheck {
  status: string;
  version: string;
  uptime_seconds: number;
  checks: {
    sarvam_api: string;
    storage: string;
    disk_free_mb: number;
    python_version: string;
  };
}

export interface RAGRetrievedChunk extends Chunk {
  relevance_score: number;
}

export interface RAGResponse {
  query: string;
  retrieved_chunks: RAGRetrievedChunk[];
  answer: string;
  citations: string[];
}

export interface ChunkPreviewResponse {
  document_name: string;
  total_pages: number;
  total_chunks: number;
  chunks: Chunk[];
}
