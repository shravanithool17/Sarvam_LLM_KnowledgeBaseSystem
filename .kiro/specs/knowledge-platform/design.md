# Design — AI Knowledge Engineering Platform
**Version**: 2.1  
**Status**: Updated — Awaiting Approval  
**Baseline**: Existing LLM Knowledge Pipeline v1.0  
**Revision notes**: Hierarchical summarisation, corrected chunking terminology, persistent storage layer, Sarvam reliability, security hardening, extensibility interfaces.

---

## 1. Architecture Overview

The upgrade follows a **layered, backward-compatible refactoring** strategy. No existing public API contracts change. New functionality is introduced as additive modules, new endpoints, or optional parameters with safe defaults.

```
┌──────────────────────────────────────────────────────────────────┐
│                      Browser  (index.html)                       │
│   Tailwind CDN · Lucide Icons · Vanilla JS · localStorage        │
└──────────────────────────┬───────────────────────────────────────┘
                           │  HTTP / JSON
┌──────────────────────────▼───────────────────────────────────────┐
│                    FastAPI  (server.py)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │/api/     │ │/api/     │ │/api/     │ │/api/             │    │
│  │status    │ │process   │ │rag       │ │documents/{id}    │    │
│  │health    │ │sample    │ │          │ │export/{fmt}      │    │
│  └──────────┘ └────┬─────┘ └────┬─────┘ │chunk-preview     │    │
│                    │             │       └──────────────────┘    │
│  ┌─────────────────▼─────────────▼────────────────────────────┐  │
│  │                   config.py  (central settings)            │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                   logger.py  (structured JSON logs)        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    pipeline.py  (backward-compatible facade)     │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │ ingest.py  │  │chunking.py │  │      knowledge.py        │   │
│  │            │  │            │  │  (map-reduce synthesis)  │   │
│  └────────────┘  └────────────┘  └──────────────────────────┘   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │ quality.py │  │  rag.py    │  │       export.py          │   │
│  └────────────┘  └────────────┘  └──────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              storage/                                      │  │
│  │  backend.py (StorageBackend ABC) · sqlite_store.py         │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              interfaces/                                   │  │
│  │  retrieval.py · synthesis.py · evaluation.py              │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              extensions/  (stubs only)                     │  │
│  │  vector_retrieval.py · hybrid_retrieval.py                 │  │
│  │  multi_document.py · knowledge_graph.py                    │  │
│  │  advanced_eval.py · human_review.py                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────┘
                           │  HTTPS / Subscription key
┌──────────────────────────▼───────────────────────────────────────┐
│                    Sarvam AI API                                  │
│   POST /v1/chat/completions                                       │
│   Models: verified against official Sarvam AI documentation      │
└──────────────────────────────────────────────────────────────────┘
```

**Key principle**: `pipeline.py` remains the single importable entry point. All sub-modules are imported by `pipeline.py` and re-exported under the existing function names. Nothing that currently imports `pipeline` needs to change.

---

## 2. Module Breakdown

### 2.1 `config.py` — Centralised Configuration

Loaded once at startup. All values come from environment variables via `python-dotenv`. Safe defaults ensure zero-configuration startup.

```python
# Illustrative field list — not final code
class Settings:
    # Sarvam AI
    sarvam_api_key: str           # SARVAM_API_KEY
    sarvam_model: str             # SARVAM_MODEL, default "sarvam-105b"
    sarvam_api_url: str           # SARVAM_API_URL
    sarvam_timeout: int           # SARVAM_TIMEOUT, default 90
    sarvam_max_retries: int       # SARVAM_MAX_RETRIES, default 2

    # Processing
    max_upload_size_mb: int       # MAX_UPLOAD_SIZE_MB, default 20
    default_chunk_size: int       # DEFAULT_CHUNK_SIZE, default 600
    default_overlap: int          # DEFAULT_OVERLAP, default 100
    min_chunk_length: int         # MIN_CHUNK_LENGTH, default 50
    synthesis_batch_size: int     # SYNTHESIS_BATCH_SIZE, default 3
    default_num_facts: int        # DEFAULT_NUM_FACTS, default 3
    default_num_qa_pairs: int     # DEFAULT_NUM_QA_PAIRS, default 3

    # RAG
    default_top_k: int            # DEFAULT_TOP_K, default 2
    rag_min_score: float          # RAG_MIN_SCORE, default 0.0

    # Quality
    similarity_threshold: float   # SIMILARITY_THRESHOLD, default 0.45

    # Storage
    storage_dir: str              # STORAGE_DIR, default "./data/"

    # Server
    allowed_origins: list[str]    # ALLOWED_ORIGINS; wildcard only if ENVIRONMENT=development
    environment: str              # ENVIRONMENT, default "development"
    log_level: str                # LOG_LEVEL, default "INFO"
```

**Note on Sarvam authentication**: Before implementation, the correct authentication header(s) and valid model identifiers must be verified against the official Sarvam AI API documentation. The current code uses both `api-subscription-key` and `Authorization: Bearer` simultaneously. The implementation must use only the documented mechanism. Model identifiers (`sarvam-105b`, etc.) must be validated against the official model list; `system.md` currently references `sarvam-30b` and `sarvam-2b` which may not be valid — these must be removed or corrected.

### 2.2 `logger.py` — Structured Logging

Uses Python's standard `logging` library with a JSON formatter. No new dependencies.

```python
def get_logger(name: str) -> logging.Logger: ...
```

Every log record includes: `timestamp`, `level`, `module`, `stage`, `elapsed_ms`, `status`. API keys are masked as `***` before any log write. Raw LLM responses are logged only when `LOG_LEVEL=DEBUG`.

### 2.3 `ingest.py` — Document Extraction

| Function | Status | Change |
|----------|--------|--------|
| `extract_text_from_pdf(pdf_stream)` | Existing → moved | Add `word_count`, track skipped/failed pages |
| `extract_text_from_txt(txt_bytes)` | Existing → moved | Improve encoding error reporting |
| `extract_text_from_docx(docx_bytes)` | **New** | python-docx support |
| `validate_upload(filename, size_bytes, content_bytes)` | **New** | Magic-byte MIME check, size guard, filename sanitisation |
| `cleanup_temp_file(path)` | **New** | Safe temp-file deletion on success and error paths |

**Magic-byte validation**: PDF files start with `%PDF`; DOCX files are ZIP archives starting with `PK\x03\x04`. Extension matching alone is not sufficient and will be rejected by `validate_upload`.

Page output schema (additive — all existing fields preserved):
```json
{
  "page": 1,
  "text": "...",
  "char_count": 1234,
  "word_count": 210,
  "status": "ok | skipped | error",
  "error_detail": null
}
```

Ingestion summary (returned alongside pages):
```json
{
  "pages_processed": 10,
  "pages_skipped": 1,
  "pages_failed": 0,
  "encoding_warnings": []
}
```

### 2.4 `chunking.py` — Boundary-Aware Chunking

**Terminology**: This module implements *boundary-aware* chunking. The term "semantic chunking" (embedding-based) must not be used in code comments, docstrings, or UI labels.

**Overlap fix**: The current implementation computes overlap as `int(overlap/5)` words, which is an inaccurate fraction of the character-based overlap parameter. The corrected implementation:
1. Split the current chunk into sentences (split on `. `, `! `, `? ` boundaries).
2. Take whole sentences from the tail of the current chunk until the accumulated character count reaches `overlap` characters (or the sentence list is exhausted).
3. Prepend those sentences to the next chunk.

This ensures overlap is always composed of whole sentences, preserving readability and context.

| Function | Status | Change |
|----------|--------|--------|
| `create_chunks(pages, chunk_size, overlap, min_chunk_length)` | Existing → moved | Fixed overlap; min_chunk_length filter; word_count field |

Chunk output schema (additive):
```json
{
  "id": "CHK-001",
  "page": 1,
  "text": "...",
  "char_count": 450,
  "approx_tokens": 90,
  "word_count": 88
}
```

### 2.5 `knowledge.py` — Hierarchical Map-Reduce Synthesis

**Critical change**: Replace the hardcoded "first 3 chunks" approach with a full-document map-reduce strategy.

#### Map Phase
Each batch of `synthesis_batch_size` chunks (default 3) is processed independently by `_synthesise_batch(batch, ...)`. Returns a partial result: `{ summary, facts, qa_dataset }`.

#### Reduce Phase
All partial results are merged by `_reduce_results(partial_results, ...)` into a unified result. The reduce step calls the LLM once more to synthesise partial summaries into an executive summary. Facts and QA pairs are concatenated and deduplicated by citation.

#### Batch Tracking
Every batch is tracked:
```json
{
  "batch_id": "BATCH-001",
  "chunks": ["CHK-001", "CHK-002", "CHK-003"],
  "status": "processed | skipped | failed",
  "error": null
}
```

A failed batch after exhausted retries is marked `failed` and processing continues with the next batch. The final response includes:
```json
{
  "batch_processing_stats": {
    "total_batches": 4,
    "processed": 4,
    "skipped": 0,
    "failed": 0
  }
}
```

#### Citation Preservation
Every fact and QA pair produced in the map phase carries the chunk ID of its source. The reduce phase must not strip or generalise citations — each item in the final output traces back to an original `CHK-XXX` ID.

| Function | Status | Change |
|----------|--------|--------|
| `call_sarvam_chat(prompt, system_prompt, ...)` | Existing → moved | Retry with back-off; rate-limit handling; key masking in logs; timeout from config |
| `synthesize_knowledge(chunks, api_key, model, ...)` | Existing → replaced internals | Map-reduce strategy; batch tracking; configurable params; backward-compatible signature |
| `_synthesise_batch(batch, ...)` | **New** | Processes one batch; returns partial knowledge dict |
| `_reduce_results(partials, api_key, model)` | **New** | Merges partials; final executive summary via LLM |
| `_validate_knowledge_schema(raw_dict)` | **New** | Schema validation; raises ValueError on critical missing fields |
| `get_simulated_knowledge(chunks)` | Existing | Add `"mode": "simulated"` tag to output |

**Simulated mode**: All results produced without a valid API key must include `"mode": "simulated"` at the top level of the knowledge dict. This makes the distinction unambiguous for callers and in the UI.

### 2.6 `quality.py` — Deduplication & Grounding

| Function | Status | Change |
|----------|--------|--------|
| `compute_jaccard_similarity(s1, s2)` | Existing → moved | Unchanged |
| `compute_tfidf_cosine(s1, s2)` | **New** | TF-IDF vectors using numpy; returns float 0–1 |
| `evaluate_dataset_quality(chunks, qa_dataset, threshold)` | Existing → updated | Per-QA grounding; quality_flags; configurable threshold |

Output schema (additive):
```json
{
  "overall_health_score": 82,
  "grounding_score": 90.0,
  "redundancy_rate": 5.2,
  "duplicate_pairs": [...],
  "total_chunks_evaluated": 12,
  "total_qa_evaluated": 3,
  "per_qa_grounding": [
    { "id": "QA-001", "grounded": true, "citation_valid": true }
  ],
  "quality_flags": ["failed_batches"]
}
```

### 2.7 `rag.py` — Retrieval Engine

| Function | Status | Change |
|----------|--------|--------|
| `search_chunks(query, chunks, top_k, min_score)` | Existing → updated | min_score filter; TF-IDF option |
| `answer_rag_query(query, retrieved_chunks, ...)` | Existing → moved | Unchanged interface |

### 2.8 `export.py` — Server-Side Export Formatters

```python
def to_jsonl(pipeline_data: dict) -> str: ...   # Alpaca format + stats header
def to_json(pipeline_data: dict) -> str: ...    # Full schema
def to_csv(pipeline_data: dict) -> str: ...     # QA pairs table
def to_markdown(pipeline_data: dict) -> str:... # Summary + facts
```

All formats include `batch_processing_stats` when present in the input data.

### 2.9 `storage/` — Persistent Storage Layer

#### `storage/backend.py` — Abstract Interface
```python
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    def save_document(self, doc_id: str, metadata: dict) -> None: ...
    @abstractmethod
    def save_result(self, doc_id: str, result: dict) -> None: ...
    @abstractmethod
    def load_result(self, doc_id: str) -> dict: ...
    @abstractmethod
    def list_documents(self) -> list[dict]: ...
    @abstractmethod
    def delete_document(self, doc_id: str) -> None: ...
```

This interface is the single migration point. Swapping `SQLiteStore` for a PostgreSQL or vector-DB backend requires only a new concrete class, not changes to any caller.

#### `storage/sqlite_store.py` — Default Implementation

- **Metadata table** (`documents`): `doc_id`, `filename`, `size_bytes`, `upload_timestamp`, `page_count`, `chunk_count`, `status`, `model_used`
- **Chunks table** (`chunks`): `doc_id`, `chunk_id`, `page`, `char_count`, `approx_tokens`, `word_count`
- **Evaluations table** (`evaluations`): `doc_id`, `eval_timestamp`, `overall_health_score`, `grounding_score`, `redundancy_rate`
- **Result files**: Full JSON results stored as `{storage_dir}/{doc_id}/result.json` — avoids large BLOBs in SQLite

The SQLite file lives at `{storage_dir}/knowledge_platform.db`.

### 2.10 `interfaces/` — Extensibility Abstractions

Four abstract base classes defining the contracts for future implementations. Only default implementations are wired up in v2.

| File | Interface | Default implementation |
|------|-----------|----------------------|
| `interfaces/retrieval.py` | `RetrievalBackend` | keyword + TF-IDF scorer in `rag.py` |
| `interfaces/synthesis.py` | `SynthesisBackend` | map-reduce Sarvam pipeline in `knowledge.py` |
| `interfaces/evaluation.py` | `EvaluationBackend` | Jaccard/grounding engine in `quality.py` |
| `interfaces/storage.py` | `StorageBackend` | SQLite store in `storage/sqlite_store.py` |

### 2.11 `extensions/` — Future Capability Stubs

Each file contains only a module docstring and a `NotImplementedError`-raising placeholder class. No logic.

```
extensions/
  __init__.py
  vector_retrieval.py      # Future: Chroma / Pinecone / Weaviate
  hybrid_retrieval.py      # Future: keyword + vector hybrid
  multi_document.py        # Future: cross-document knowledge synthesis
  knowledge_graph.py       # Future: entity-relationship graph generation
  advanced_eval.py         # Future: LLM-as-judge, BLEU, ROUGE scoring
  human_review.py          # Future: annotation and feedback loop
```

---

## 3. API Design

### Preserved Endpoints (contracts unchanged)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve `index.html` |
| GET | `/api/status` | Key check + model + version |
| POST | `/api/sample` | Demo pipeline run |
| POST | `/api/process` | Full document pipeline |
| POST | `/api/rag` | RAG query + grounded answer |

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Deep health check |
| POST | `/api/chunk-preview` | Chunks without LLM call |
| POST | `/api/export/{format}` | Server-side file download |
| GET | `/api/documents` | List stored documents |
| GET | `/api/documents/{doc_id}` | Retrieve stored result |
| DELETE | `/api/documents/{doc_id}` | Remove stored result |

#### `GET /api/health`
```json
{
  "status": "ok",
  "version": "2.0.0",
  "uptime_seconds": 3620,
  "checks": {
    "sarvam_api": "reachable | unreachable | not_configured",
    "storage": "ok | error",
    "disk_free_mb": 4096,
    "python_version": "3.12.0"
  }
}
```

#### `POST /api/chunk-preview`
Request:
```json
{ "text": "...", "chunk_size": 600, "overlap": 100 }
```
Response: `{ "chunks": [...] }` — same chunk schema as `/api/process`.

#### `POST /api/process` — Extended Parameters (all optional, additive)
```
file          : <binary upload>
model         : str  (default from config)
api_key       : str  (optional override)
chunk_size    : int  (default from config)
overlap       : int  (default from config)
num_facts     : int  (default from config)
num_qa_pairs  : int  (default from config)
top_k         : int  (default from config)
```

Response additions (all new fields, existing fields unchanged):
```json
{
  "document_id": "uuid-v4",
  "mode": "live | simulated",
  "batch_processing_stats": {
    "total_batches": 4, "processed": 4, "skipped": 0, "failed": 0
  },
  "ingestion_summary": {
    "pages_processed": 10, "pages_skipped": 0, "pages_failed": 0
  }
}
```

### Consistent Error Schema
All 4xx/5xx responses:
```json
{
  "error": "Human-readable message",
  "code": "UPLOAD_TOO_LARGE | INVALID_FILE_TYPE | SARVAM_TIMEOUT | SCHEMA_VALIDATION_FAILED | ...",
  "detail": "Optional technical context"
}
```

---

## 4. Hierarchical Synthesis Data Flow

```
create_chunks(pages)
       │
       ▼
  [ CHK-001, CHK-002, ..., CHK-N ]
       │
       │  partition into batches of synthesis_batch_size
       ▼
  [ BATCH-001: CHK-001..003 ]  ──► _synthesise_batch() ──► partial_1
  [ BATCH-002: CHK-004..006 ]  ──► _synthesise_batch() ──► partial_2
  [ BATCH-003: CHK-007..009 ]  ──► _synthesise_batch() ──► partial_3
       │                                 ▲
       │              on failure: mark batch "failed", continue
       ▼
  _reduce_results([partial_1, partial_2, partial_3])
       │
       ├── executive_summary  (LLM merge of partial summaries)
       ├── facts              (concatenated, citation preserved)
       └── qa_dataset         (concatenated, citation preserved)
```

---

## 5. Security Design

| Concern | Mitigation |
|---------|-----------|
| API key exposure in logs | Masked as `***` before any log write |
| API key in responses | Audited out of all response payloads |
| Unrestricted uploads | Magic-byte MIME check + extension allowlist + configurable size cap |
| Malicious filenames | `pathlib.Path(filename).name` stripping + disallow `..` |
| Temp file leakage | `try/finally` cleanup in all upload handlers |
| CORS wildcard | `ALLOWED_ORIGINS` env var; wildcard only in development mode |
| Content-Security-Policy | CSP + X-Content-Type-Options + X-Frame-Options + Referrer-Policy headers via FastAPI middleware |
| XSS in rendered results | `escapeHtml()` already present; server never injects raw LLM output into HTML |
| Path traversal in storage | Document IDs are UUIDs; storage paths are constructed programmatically |

---

## 6. Frontend Design

### Preserved
- Full six-tab layout, glassmorphic dark-mode design, stepper header.
- All existing JS rendering logic (`renderPipelineResults`, `askRAG`, `downloadDataset`).
- Client-side export (preserved; server-side export is additive).

### Additions

**Toast Notification System** (replaces all `alert()`)
- Pure JS, ~50 lines, no library dependency.
- Types: `success` (green), `error` (red), `info` (blue), `warning` (amber).
- Stacks in top-right corner, auto-dismisses after 4 s.

**Advanced Options Panel** (collapsible, below file input)
- Chunk Size slider: 200–1000, step 50, default 550, with value label.
- Overlap slider: 0–200, step 10, default 80, with value label.
- Values sent as form fields to `/api/process`.

**Config Modal Extensions**
- `num_facts` number input (1–15, default 3).
- `num_qa_pairs` number input (1–15, default 3).

**localStorage Persistence**
- `renderPipelineResults()` writes `currentPipelineData` to `localStorage['kp_last_run']`.
- On `DOMContentLoaded`: if valid data exists in `localStorage`, show a slim restore banner.
- "Restore" re-calls `renderPipelineResults()`. "Dismiss" hides the banner.
- Validation before restore: must have `chunks` and `knowledge` keys.

**Document Info Bar**
- Appears after successful processing: filename · pages · chunks · timestamp · model · mode (live/simulated).
- Dismissible via ×.

**Loading Skeletons**
- All tab content areas show animated grey skeleton lines during `showProgress()`.
- Replaced by real content on `renderPipelineResults()`.

**Batch Progress Display**
- During hierarchical processing, progress text updates per batch: "Processing batch 2 of 4..."
- After completion, Quality tab shows batch processing stats card.

**RAG UX**
- `Enter` key in `#ragQueryInput` triggers `askRAG()`.
- Empty input shows error toast (no network call).
- Auto-scroll to results area after completion.

---

## 7. Dependency Plan

| Package | Version | Role | Change |
|---------|---------|------|--------|
| fastapi | 0.162.0 | Web framework | No change |
| uvicorn | 0.54.0 | ASGI server | No change |
| pypdf | 6.21.4 | PDF extraction | No change |
| python-dotenv | 1.2.4 | Env config | No change |
| requests | 2.34.2 | HTTP client | No change |
| numpy | 2.5.4 | TF-IDF cosine | No change (already installed) |
| python-multipart | 0.0.33 | File uploads | No change |
| pydantic | 2.14.2 | Data validation | No change |
| python-docx | ≥1.1.0 | DOCX support | **Add to requirements.txt** |
| pytest | ≥8.0 | Test runner | **Add to requirements-dev.txt** |
| httpx | ≥0.27 | FastAPI test client | **Add to requirements-dev.txt** |
| pytest-asyncio | ≥0.23 | Async test support | **Add to requirements-dev.txt** |

All versions pinned to minimum compatible versions. No open-range (`*`) specifiers.

---

## 8. Target File Structure

```
LLM KN/
├── .env
├── .env.example               (updated — all new vars documented)
├── config.py                  (NEW)
├── logger.py                  (NEW)
├── pipeline.py                (preserved facade — re-exports from sub-modules)
├── server.py                  (extended — new endpoints, security middleware)
├── ingest.py                  (NEW — extracted from pipeline.py)
├── chunking.py                (NEW — extracted, overlap fix, boundary-aware)
├── knowledge.py               (NEW — map-reduce synthesis)
├── quality.py                 (NEW — extracted, cosine added)
├── rag.py                     (NEW — extracted)
├── export.py                  (NEW)
├── storage/
│   ├── __init__.py
│   ├── backend.py             (StorageBackend ABC)
│   └── sqlite_store.py        (default SQLite + JSON files implementation)
├── interfaces/
│   ├── __init__.py
│   ├── retrieval.py           (RetrievalBackend ABC)
│   ├── synthesis.py           (SynthesisBackend ABC)
│   └── evaluation.py          (EvaluationBackend ABC)
├── extensions/
│   ├── __init__.py
│   ├── vector_retrieval.py    (stub)
│   ├── hybrid_retrieval.py    (stub)
│   ├── multi_document.py      (stub)
│   ├── knowledge_graph.py     (stub)
│   ├── advanced_eval.py       (stub)
│   └── human_review.py        (stub)
├── data/                      (created at runtime — gitignored)
│   ├── knowledge_platform.db
│   └── {doc_id}/
│       └── result.json
├── requirements.txt           (updated)
├── requirements-dev.txt       (NEW)
├── system.md                  (updated)
├── templates/
│   └── index.html             (extended)
├── tests/
│   ├── __init__.py
│   ├── conftest.py            (fixtures, mock Sarvam client)
│   ├── test_ingest.py
│   ├── test_chunking.py
│   ├── test_knowledge.py
│   ├── test_quality.py
│   ├── test_rag.py
│   ├── test_export.py
│   ├── test_storage.py
│   └── test_server.py
│   └── fixtures/
│       ├── sample.txt
│       └── sample.pdf
└── .kiro/
    └── specs/knowledge-platform/
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

Note: `data/` must be added to `.gitignore` to prevent committing processed documents or the SQLite database.
