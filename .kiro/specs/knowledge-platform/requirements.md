# Requirements — AI Knowledge Engineering Platform
**Version**: 2.1  
**Status**: Updated — Awaiting Approval  
**Baseline**: Existing LLM Knowledge Pipeline v1.0  
**Revision notes**: Incorporates eight requested changes — hierarchical summarisation, chunking accuracy, persistent storage, Sarvam reliability, security hardening, test suite, frontend upgrades, future extensibility interfaces.

---

## 1. Project Context

The existing system (`server.py` + `pipeline.py` + `templates/index.html`) is a functional but minimal LLM Knowledge Pipeline. It already supports PDF/TXT ingestion, boundary-aware chunking, Sarvam AI synthesis, Jaccard-based deduplication, keyword RAG, three-format export, and a glassmorphic dark-mode dashboard.

The upgrade target is a **production-quality AI Knowledge Engineering Platform** that is robust, extensible, observable, and maintainable — without removing any existing working functionality.

---

## 2. Functional Requirements

### FR-01 · Document Ingestion & Preprocessing
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01-1 | Support PDF and plain text (.txt, .md) upload — existing, must remain intact | Must Have |
| FR-01-2 | Add DOCX (.docx) file support | Should Have |
| FR-01-3 | Enforce a configurable maximum upload size (env: `MAX_UPLOAD_SIZE_MB`, default 20 MB); return HTTP 413 with structured error | Must Have |
| FR-01-4 | Validate MIME type and actual file signature (magic bytes) — not only file extension — against an allowlist (.pdf, .txt, .md, .docx) | Must Have |
| FR-01-5 | Detect encoding errors and surface them as warnings in the processing result rather than silently replacing characters | Should Have |
| FR-01-6 | Return per-page `word_count` alongside existing `char_count` and page metadata | Should Have |
| FR-01-7 | Safely clean up any temporary files after processing completes or fails | Must Have |
| FR-01-8 | Track per-document ingestion status: pages processed, pages skipped (empty/unreadable), extraction errors | Must Have |

### FR-02 · Boundary-Aware Chunking Engine
> **Terminology correction**: The existing implementation is *boundary-aware* chunking (respecting paragraph and sentence delimiters) and must be described as such throughout the codebase and documentation. It must not be labelled "semantic chunking", which implies embedding-based similarity grouping.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-02-1 | Preserve existing paragraph/sentence boundary-aware chunking — no regressions | Must Have |
| FR-02-2 | Fix overlap implementation: overlap must be computed on whole sentences or whole tokens, not on an approximate character fraction (`int(overlap/5)`) | Must Have |
| FR-02-3 | Expose `chunk_size` and `overlap` as first-class, configurable parameters on every relevant API endpoint (not hardcoded) | Must Have |
| FR-02-4 | Add `word_count` field to each chunk object in addition to `approx_tokens` | Should Have |
| FR-02-5 | Enforce a configurable minimum chunk length (env: `MIN_CHUNK_LENGTH`, default 50 chars); silently discard micro-fragments | Should Have |
| FR-02-6 | Provide a `/api/chunk-preview` endpoint that returns chunks for arbitrary text without calling the LLM | Should Have |

### FR-03 · Hierarchical Knowledge Synthesis (Sarvam AI)
> **Critical fix**: The existing implementation sends only the first three chunks to the LLM, silently ignoring the remainder of the document. This must be replaced with a full-document strategy that never omits content.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-03-1 | Preserve the existing `synthesize_knowledge` public interface — callers must not break | Must Have |
| FR-03-2 | Implement a **map-reduce hierarchical summarisation** strategy: (a) Map — synthesise each batch of chunks independently; (b) Reduce — merge all per-batch results into a unified summary, fact list, and QA dataset | Must Have |
| FR-03-3 | Make batch size configurable (env: `SYNTHESIS_BATCH_SIZE`, default 3 chunks); never hardcode to 3 | Must Have |
| FR-03-4 | Track per-batch processing status: processed, skipped, failed. Return this tracking data in the pipeline response | Must Have |
| FR-03-5 | Preserve source chunk citations through all summarisation stages — every fact and QA pair must trace back to an original chunk ID | Must Have |
| FR-03-6 | Never silently omit document content: if a batch fails after retries, mark it as failed and continue processing remaining batches | Must Have |
| FR-03-7 | Add configurable `num_facts` and `num_qa_pairs` per batch (default 3 each, max 15) | Should Have |
| FR-03-8 | Add structured retry logic (max 2 retries, exponential back-off: 2 s, 4 s) for transient Sarvam API errors | Must Have |
| FR-03-9 | Expose API timeout as a configurable environment variable (env: `SARVAM_TIMEOUT`, default 90 s) | Should Have |
| FR-03-10 | Validate the Sarvam JSON response against the expected schema before accepting it; on schema mismatch fall back to partial extraction rather than crashing | Must Have |
| FR-03-11 | Log raw LLM responses (prompt + completion) to a per-session debug log file when `LOG_LEVEL=DEBUG` | Nice to Have |
| FR-03-12 | Simulated mode (no API key) must remain clearly distinguishable from real API execution: tag all simulated results with `"mode": "simulated"` in the response | Must Have |

### FR-04 · Sarvam API Configuration & Reliability
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-04-1 | Centralise all Sarvam API configuration (URL, headers, model identifiers, timeout) in `config.py` | Must Have |
| FR-04-2 | Verify supported authentication header(s) and valid model identifiers against the official Sarvam AI API documentation before hard-coding them | Must Have |
| FR-04-3 | Handle HTTP 429 (rate limit) responses by honouring `Retry-After` header if present, otherwise applying exponential back-off | Must Have |
| FR-04-4 | Handle malformed or non-JSON API responses gracefully — log the raw response and fall back to simulated mode | Must Have |
| FR-04-5 | Never include API key values in log output — mask as `***` | Must Have |
| FR-04-6 | Never return API key values in any response payload | Must Have |

### FR-05 · Quality Assessment & Deduplication
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-05-1 | Preserve existing Jaccard deduplication and grounding score — must not regress | Must Have |
| FR-05-2 | Add cosine similarity (TF-IDF vectors using numpy) as a complementary metric alongside Jaccard | Should Have |
| FR-05-3 | Make the similarity threshold configurable (env: `SIMILARITY_THRESHOLD`, default 0.45) | Must Have |
| FR-05-4 | Return per-QA grounding status (`grounded` / `ungrounded`) in addition to the aggregate grounding score | Should Have |
| FR-05-5 | Add a `quality_flags` array to the evaluation result listing specific detected issues (e.g. `low_grounding`, `high_redundancy`, `failed_batches`) | Should Have |

### FR-06 · RAG Retrieval
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-06-1 | Preserve existing keyword-based retrieval — must not regress | Must Have |
| FR-06-2 | Add TF-IDF based scoring as an improved retrieval option | Should Have |
| FR-06-3 | Expose `top_k` as a configurable API parameter (default 2, max 10) | Must Have |
| FR-06-4 | Add a minimum relevance score threshold filter (env: `RAG_MIN_SCORE`, default 0.0) | Should Have |
| FR-06-5 | Surface chunk relevance scores in all RAG responses | Must Have |

### FR-07 · Persistent Storage
> **New requirement group.** All data is persisted locally using SQLite for metadata and JSON/JSONL files for payloads. The schema is designed to allow migration to PostgreSQL and a dedicated vector database without redesigning the application layer.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-07-1 | Persist uploaded document metadata: filename, size, upload timestamp, page count, chunk count, processing status | Must Have |
| FR-07-2 | Persist full processing results (chunks, knowledge, evaluation) as JSON files, keyed by a `document_id` (UUID) | Must Have |
| FR-07-3 | Persist generated summaries, extracted facts, and QA datasets individually so they can be queried without loading the full result | Should Have |
| FR-07-4 | Persist chunk metadata (id, page, char_count, approx_tokens, word_count) in a lightweight SQLite table | Should Have |
| FR-07-5 | Persist evaluation history: each evaluation run is stored with its timestamp and scores | Should Have |
| FR-07-6 | Provide a `GET /api/documents` endpoint listing all persisted documents with metadata | Should Have |
| FR-07-7 | Provide a `GET /api/documents/{document_id}` endpoint returning the full stored result for a document | Should Have |
| FR-07-8 | Provide a `DELETE /api/documents/{document_id}` endpoint removing stored results | Should Have |
| FR-07-9 | All storage operations must be atomic where possible; failures must not corrupt existing records | Must Have |
| FR-07-10 | Storage location must be configurable (env: `STORAGE_DIR`, default `./data/`) | Should Have |
| FR-07-11 | The storage abstraction must expose an interface (`StorageBackend`) that can be swapped for a PostgreSQL or vector DB implementation in a future version | Must Have |

### FR-08 · Export Hub
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-08-1 | Preserve existing client-side JSONL, JSON, CSV exports — must not regress | Must Have |
| FR-08-2 | Add server-side `/api/export/{format}` endpoint (jsonl, json, csv, md) so exports work without holding state in the browser | Should Have |
| FR-08-3 | JSONL export must use the standard Alpaca schema; include a dataset statistics header comment | Should Have |
| FR-08-4 | Markdown export: summary + facts + QA pairs in readable format | Nice to Have |
| FR-08-5 | Exports must include `batch_processing_stats` when hierarchical summarisation was used | Should Have |

### FR-09 · Configuration & API
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-09-1 | Centralise all configurable values in `config.py`, loaded from `.env` via `python-dotenv` | Must Have |
| FR-09-2 | Expand `/api/status` to include version, active model, and configuration summary (no secret values) | Should Have |
| FR-09-3 | Add `/api/health` with deep health check (Sarvam API reachability, storage availability, Python version, uptime) | Should Have |
| FR-09-4 | Return structured error responses `{ "error": "...", "code": "...", "detail": "..." }` consistently from all endpoints | Must Have |
| FR-09-5 | All new endpoints must include OpenAPI docstrings and Pydantic response models | Should Have |

### FR-10 · Security
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10-1 | Validate upload MIME type against magic bytes (not only extension) | Must Have |
| FR-10-2 | Enforce configurable maximum upload size | Must Have |
| FR-10-3 | Restrict CORS to environment-controlled allowlist; wildcard `*` permitted only when `ENVIRONMENT=development` | Must Have |
| FR-10-4 | Add `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` security headers to HTML responses | Should Have |
| FR-10-5 | Sanitise filenames before any disk operations (strip path traversal sequences) | Must Have |
| FR-10-6 | Never echo API key values in logs, responses, or debug output | Must Have |
| FR-10-7 | Clean up all temporary files after processing, including on error paths | Must Have |
| FR-10-8 | Rate-limit `/api/process` and `/api/rag` endpoints | Should Have |

### FR-11 · Frontend Dashboard
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-11-1 | Preserve existing six-tab layout, dark-mode glassmorphic design, and stepper header | Must Have |
| FR-11-2 | Replace all `alert()` calls with a non-blocking toast notification system (pure JS) | Must Have |
| FR-11-3 | Show animated loading skeletons on all tabs during pipeline processing | Should Have |
| FR-11-4 | Persist the processed dataset in `localStorage` and offer a "Restore last session" banner on reload | Should Have |
| FR-11-5 | Add chunk size and overlap sliders in an "Advanced Options" section of the upload panel | Should Have |
| FR-11-6 | Add `num_facts` and `num_qa_pairs` inputs to the config modal | Should Have |
| FR-11-7 | Display a document info bar (filename, pages, chunks, timestamp, model) after processing | Should Have |
| FR-11-8 | Show per-batch processing progress during hierarchical summarisation | Should Have |
| FR-11-9 | Display batch processing stats (processed / skipped / failed) in the Quality & Dedup tab | Should Have |
| FR-11-10 | `Enter` key in RAG input triggers the query | Nice to Have |

### FR-12 · Observability
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-12-1 | Add structured JSON logging for every pipeline stage with elapsed timings | Must Have |
| FR-12-2 | Log all Sarvam API calls: model, prompt token estimate, elapsed ms, status (key masked) | Must Have |
| FR-12-3 | Surface batch processing stats in the API response | Must Have |

### FR-13 · Future Extensibility Interfaces (Design Only — Not Implemented in v2)
> These requirements define *interfaces* (abstract base classes or protocol stubs) that must be present in the codebase to enable future implementation without redesigning existing modules. No concrete implementations beyond the defaults are required in v2.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-13-1 | `StorageBackend` abstract interface: methods for save, load, list, delete documents — default impl uses SQLite + JSON files | Must Have (interface only) |
| FR-13-2 | `RetrievalBackend` abstract interface: methods for index_chunks, search — default impl is the existing keyword scorer | Must Have (interface only) |
| FR-13-3 | `SynthesisBackend` abstract interface: methods for synthesise, reduce — default impl is the Sarvam map-reduce pipeline | Must Have (interface only) |
| FR-13-4 | `EvaluationBackend` abstract interface: methods for evaluate, score — default impl is the existing Jaccard/grounding engine | Must Have (interface only) |
| FR-13-5 | Stub module `extensions/` with placeholder files for: vector_retrieval, hybrid_retrieval, multi_document, knowledge_graph, advanced_eval, human_review | Nice to Have |

---

## 3. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | API response time for `/api/process` excluding LLM call | < 2 s |
| NFR-02 | Maximum supported document size | Configurable, default 20 MB |
| NFR-03 | Memory footprint for a 100-chunk document | < 200 MB RSS |
| NFR-04 | Sarvam API timeout per request | Configurable, default 90 s |
| NFR-05 | Test coverage on all new/refactored Python modules | ≥ 80 % |
| NFR-06 | All Sarvam API calls must use mocked responses in the test suite | Mandatory |
| NFR-07 | Application must run on Python 3.10+ | — |
| NFR-08 | Zero hardcoded API credentials, URLs, or thresholds | Mandatory |

---

## 4. Backward Compatibility Constraints

These existing behaviours must be preserved without change:

1. `GET /` serves `templates/index.html`.
2. `GET /api/status` response shape: `{ status, has_key, default_model }` — new fields additive only.
3. `POST /api/sample` response shape: `{ document_name, stats, chunks, knowledge, evaluation }`.
4. `POST /api/process` response shape: identical to `/api/sample` — new fields additive only.
5. `POST /api/rag` response shape: `{ query, retrieved_chunks, answer, citations }`.
6. Chunk object schema: `{ id, page, text, char_count, approx_tokens }` — new fields additive only.
7. Knowledge object schema: `{ summary, facts, qa_dataset }` — new fields additive only.
8. Evaluation object schema: `{ overall_health_score, grounding_score, redundancy_rate, duplicate_pairs, total_chunks_evaluated, total_qa_evaluated }` — new fields additive only.
9. Simulated mode must continue to return valid, non-empty mock data.
10. The Tailwind CDN + Lucide Icons frontend approach is preserved.

---

## 5. Out of Scope (v2.0 — deferred to v3+)

- Concrete vector database integration (Chroma, Pinecone, Weaviate) — interface stub provided
- Multi-user authentication / session management
- Real-time streaming of LLM responses
- DOCX export format
- Batch multi-file upload in one request
- Knowledge graph generation (interface stub provided)
- Human-in-the-loop review workflow (interface stub provided)
- Hybrid retrieval implementation (interface stub provided)
