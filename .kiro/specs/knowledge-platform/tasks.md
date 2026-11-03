# Tasks — AI Knowledge Engineering Platform v2.0
**Status**: Updated — Awaiting Approval  
**Approach**: Additive, backward-compatible. Each task is independently deliverable and verifiable.  
**Test policy**: All Sarvam API calls in tests use mocked responses — no live API credits consumed.

---

## Phase 0 — Foundation

### Task 0.1 — Create `config.py`
**Files**: `config.py` (new), `.env.example` (update)  
**What**: Implement a `Settings` class using `python-dotenv` that centralises every configurable value: Sarvam API key/URL/model/timeout/retries, upload size limit, chunk size/overlap/min-length, synthesis batch size, num-facts/qa-pairs defaults, similarity threshold, RAG top-k/min-score, storage directory, CORS origins, environment, log level.  
**Sarvam note**: Before coding model identifiers and authentication headers, verify the current list of valid models and the correct auth header(s) from official Sarvam AI API documentation. Document the findings in a comment block in `config.py`.  
**Acceptance**:
- `from config import settings` works with no `.env` file (all defaults apply).
- All existing env vars (`SARVAM_API_KEY`, `SARVAM_MODEL`, `SARVAM_API_URL`) still load correctly.
- New vars are documented with their defaults in `.env.example`.
- `settings.sarvam_api_key` never appears in `repr(settings)` output.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 0.2 — Create `logger.py`
**Files**: `logger.py` (new)  
**What**: Implement a `get_logger(name)` factory returning a Python standard-library logger configured with a JSON formatter. Each record includes: `timestamp`, `level`, `module`, `stage`, `elapsed_ms`, `status`. Add a `mask_key(value)` helper that returns `***` for any non-empty string (used everywhere an API key might be logged).  
**Acceptance**:
- `get_logger("pipeline")` returns a logger.
- Log output is valid JSON on each line.
- `mask_key("sk-abc123")` returns `"***"`.
- `mask_key("")` returns `""`.
**Depends on**: Task 0.1  
**Risk**: Low

---

### Task 0.3 — Set Up Test Infrastructure
**Files**: `tests/__init__.py`, `tests/conftest.py`, `tests/fixtures/sample.txt`, `tests/fixtures/sample.pdf`, `requirements-dev.txt`  
**What**: Create the test directory tree. Add `pytest`, `httpx`, `pytest-asyncio` to `requirements-dev.txt` with pinned minimum versions. Write `conftest.py` with: a `mock_sarvam_response` fixture that patches `requests.post` to return a canned valid knowledge JSON; a `sample_chunks` fixture; a `sample_pipeline_data` fixture. Create `sample.txt` (≥500 chars, 3 paragraphs). Generate a minimal valid single-page `sample.pdf` using `pypdf`.  
**Acceptance**:
- `pytest tests/` completes with 0 errors and 0 test failures (no tests collected yet is acceptable).
- `conftest.py` fixtures are importable.
- Mock fixture intercepts `requests.post` and returns the canned response without any network call.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 0.4 — Add `.gitignore` Entries
**Files**: `.gitignore` (create or update)  
**What**: Add entries for: `data/`, `.env`, `__pycache__/`, `*.pyc`, `.venv/`, `*.db`.  
**Acceptance**: The listed patterns are present in `.gitignore`.  
**Depends on**: Nothing  
**Risk**: Low

---

## Phase 1 — Core Module Extraction

### Task 1.1 — Extract `ingest.py`
**Files**: `ingest.py` (new), `pipeline.py` (update imports)  
**What**: Move `extract_text_from_pdf` and `extract_text_from_txt` into `ingest.py`. Add `word_count` and `status`/`error_detail` fields to page dicts. Implement `validate_upload(filename, size_bytes, content_bytes)` — checks magic bytes for PDF (`%PDF`) and DOCX (`PK\x03\x04`), enforces `settings.max_upload_size_mb`, sanitises filename via `pathlib.Path(filename).name`. Implement `cleanup_temp_file(path)`. Re-export all from `pipeline.py` under existing names.  
**Acceptance**:
- `from pipeline import extract_text_from_pdf` still works.
- Pages include `word_count`, `status`, `error_detail` fields.
- `validate_upload("evil.exe", 100, b"...")` raises `ValueError` with code `INVALID_FILE_TYPE`.
- `validate_upload("ok.pdf", 25_000_000, b"%PDF...")` raises `ValueError` with code `UPLOAD_TOO_LARGE`.
- `validate_upload("ok.pdf", 1_000_000, b"%PDF...")` passes.
- A file named `../../etc/passwd` is sanitised to `passwd`.
**Tests**: `tests/test_ingest.py`  
**Depends on**: Task 0.1, 0.2  
**Risk**: Low

---

### Task 1.2 — Extract `chunking.py` with Overlap Fix
**Files**: `chunking.py` (new), `pipeline.py` (update imports)  
**What**: Move `create_chunks` into `chunking.py`. Rename all references from "semantic chunking" to "boundary-aware chunking" in comments and docstrings. Fix overlap: collect whole sentences from the tail of the current chunk until accumulated chars ≥ `overlap` (or sentence list exhausted), then prepend to next chunk. Add `word_count` field. Add `min_chunk_length` parameter. Re-export from `pipeline.py`.  
**Acceptance**:
- `from pipeline import create_chunks` still works.
- Chunks include `word_count`.
- Chunks shorter than `min_chunk_length` are discarded.
- Overlap region always consists of complete sentences (no mid-sentence cuts).
- With `overlap=0`, no overlap text is prepended.
- Existing fields (`id`, `page`, `text`, `char_count`, `approx_tokens`) all present.
- No use of the phrase "semantic chunking" in code comments or docstrings.
**Tests**: `tests/test_chunking.py`  
**Depends on**: Task 0.1, 0.2  
**Risk**: Medium (overlap logic change — must not regress existing chunk ID/page assignment)

---

### Task 1.3 — Extract `knowledge.py` with Map-Reduce Synthesis
**Files**: `knowledge.py` (new), `pipeline.py` (update imports)  
**What**: Move `call_sarvam_chat` and `get_simulated_knowledge` into `knowledge.py`. Replace the hardcoded "first 3 chunks" logic inside `synthesize_knowledge` with the map-reduce strategy:

1. `_synthesise_batch(batch, api_key, model, num_facts, num_qa_pairs)` — calls LLM for one batch; returns `{ summary, facts, qa_dataset, batch_id, status, error }`.
2. `_reduce_results(partials, api_key, model)` — merges partial summaries via one more LLM call; concatenates facts/QA; preserves original chunk citations.
3. `synthesize_knowledge(chunks, api_key, model, num_chunks_per_batch, num_facts, num_qa_pairs)` — orchestrates map-reduce; returns existing schema fields plus `batch_processing_stats` and `mode`.

Add `_validate_knowledge_schema(raw_dict)`. Add retry logic (max `settings.sarvam_max_retries`, back-off 2 s × 2^attempt) in `call_sarvam_chat`. Handle HTTP 429 by honouring `Retry-After`. Mask API key in all log calls. Tag simulated results with `"mode": "simulated"`.

Re-export `synthesize_knowledge` and `get_simulated_knowledge` from `pipeline.py`.

**Acceptance**:
- `from pipeline import synthesize_knowledge` still works.
- All chunks in a 10-chunk input are processed (not just first 3).
- Each fact and QA pair retains a citation pointing to the originating chunk ID.
- If one batch fails after retries, it is marked `failed`; remaining batches continue.
- `batch_processing_stats` is present in all results.
- Simulated mode result includes `"mode": "simulated"`.
- Real API results include `"mode": "live"`.
- API key never appears in log output (mock Sarvam fixture in tests must verify this).
**Tests**: `tests/test_knowledge.py`  
**Depends on**: Task 0.1, 0.2, 0.3  
**Risk**: High (core logic replacement — must have good test coverage before landing)

---

### Task 1.4 — Extract `quality.py`
**Files**: `quality.py` (new), `pipeline.py` (update imports)  
**What**: Move `compute_jaccard_similarity` and `evaluate_dataset_quality` into `quality.py`. Add `compute_tfidf_cosine(s1, s2)` using numpy. Add `per_qa_grounding` and `quality_flags` to evaluation output. Make threshold a parameter defaulting to `settings.similarity_threshold`. Add `"failed_batches"` flag when `batch_processing_stats.failed > 0` is provided. Re-export from `pipeline.py`.  
**Acceptance**:
- `from pipeline import evaluate_dataset_quality` still works.
- Result includes `per_qa_grounding` and `quality_flags`.
- `compute_tfidf_cosine("hello world", "hello world")` returns 1.0.
- `compute_tfidf_cosine("apple pie", "ocean current")` returns < 0.1.
- Threshold parameter changes which pairs are flagged as duplicates.
**Tests**: `tests/test_quality.py`  
**Depends on**: Task 0.1, 0.2  
**Risk**: Low

---

### Task 1.5 — Extract `rag.py`
**Files**: `rag.py` (new), `pipeline.py` (update imports)  
**What**: Move `search_chunks` and `answer_rag_query` into `rag.py`. Add `min_score` parameter to `search_chunks` (default `settings.rag_min_score`). Re-export from `pipeline.py`.  
**Acceptance**:
- `from pipeline import search_chunks` still works.
- `search_chunks(query, chunks, top_k=2, min_score=50.0)` returns only chunks with `relevance_score ≥ 50`.
- With `min_score=0.0`, behaviour is identical to current.
**Tests**: `tests/test_rag.py`  
**Depends on**: Task 0.1, 0.2  
**Risk**: Low

---

### Task 1.6 — Create `export.py`
**Files**: `export.py` (new)  
**What**: Implement `to_jsonl(data)`, `to_json(data)`, `to_csv(data)`, `to_markdown(data)`. Each accepts the unified pipeline response dict. JSONL includes a `# stats:` header comment. CSV has header row. Markdown has `#` sections. All include `batch_processing_stats` when present.  
**Acceptance**:
- `to_jsonl(data)` output is parseable one-object-per-line.
- `to_csv(data)` header row is `ID,Instruction,Response,Citation`.
- `to_json(data)` is valid JSON.
- `to_markdown(data)` contains `# Executive Summary` and `## Facts` headings.
**Tests**: `tests/test_export.py`  
**Depends on**: Nothing  
**Risk**: Low

---

## Phase 2 — Persistent Storage

### Task 2.1 — `storage/backend.py` — Abstract Interface
**Files**: `storage/__init__.py`, `storage/backend.py` (new)  
**What**: Define `StorageBackend` ABC with methods: `save_document`, `save_result`, `load_result`, `list_documents`, `delete_document`, `save_evaluation`. Include full type hints and docstrings. This is the migration boundary for PostgreSQL/vector DB.  
**Acceptance**:
- ABC importable: `from storage.backend import StorageBackend`.
- Instantiating `StorageBackend()` directly raises `TypeError`.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 2.2 — `storage/sqlite_store.py` — SQLite Implementation
**Files**: `storage/sqlite_store.py` (new)  
**What**: Implement `SQLiteStore(StorageBackend)`. On first use, create `{storage_dir}/knowledge_platform.db` with tables: `documents`, `chunks`, `evaluations`. Store full JSON results as `{storage_dir}/{doc_id}/result.json`. All write operations wrapped in SQLite transactions. Directory created if absent.  
**Acceptance**:
- `save_document(doc_id, metadata)` inserts a row and is idempotent on re-run.
- `save_result(doc_id, result)` writes JSON file and survives a process restart.
- `load_result(doc_id)` returns the same dict after a process restart.
- `list_documents()` returns all stored document metadata rows.
- `delete_document(doc_id)` removes both DB rows and the JSON file.
- `save_evaluation(doc_id, eval_data)` inserts an evaluation row.
- Concurrent writes do not corrupt the DB (SQLite WAL mode enabled).
**Tests**: `tests/test_storage.py`  
**Depends on**: Task 2.1  
**Risk**: Low

---

### Task 2.3 — Wire Storage into `server.py`
**Files**: `server.py` (update)  
**What**: Initialise `SQLiteStore` once at startup. In `/api/process` and `/api/sample`: generate `document_id = str(uuid.uuid4())`, call `storage.save_document(doc_id, metadata)` and `storage.save_result(doc_id, result)` and `storage.save_evaluation(doc_id, evaluation)`. Include `document_id` in the response. Add `GET /api/documents`, `GET /api/documents/{doc_id}`, `DELETE /api/documents/{doc_id}` endpoints.  
**Acceptance**:
- `/api/process` response includes `document_id`.
- `GET /api/documents` returns a list of previously processed documents (survives restart).
- `GET /api/documents/{doc_id}` returns the full stored result.
- `DELETE /api/documents/{doc_id}` removes the record; subsequent GET returns 404.
- Storage failures are logged but do not cause the pipeline response to fail.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 2.2, Task 1.3  
**Risk**: Low

---

## Phase 3 — Security & Robustness

### Task 3.1 — Upload Validation & Temp File Safety
**Files**: `server.py` (update), `ingest.py` (use `validate_upload` and `cleanup_temp_file`)  
**What**: In `/api/process`, call `validate_upload(filename, len(contents), contents[:8])` before any processing. Wrap the entire handler in `try/finally` with `cleanup_temp_file()`. Return structured error JSON on all validation failures.  
**Acceptance**:
- 25 MB file → HTTP 413, `{ "code": "UPLOAD_TOO_LARGE" }`.
- `.exe` file → HTTP 400, `{ "code": "INVALID_FILE_TYPE" }`.
- File with `.pdf` extension but non-PDF magic bytes → HTTP 400, `{ "code": "INVALID_FILE_TYPE" }`.
- Valid 1 MB PDF → processes successfully, no temp files left on disk.
- Exception during processing → temp files still cleaned up.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 1.1  
**Risk**: Low

---

### Task 3.2 — Consistent Error Responses
**Files**: `server.py` (update)  
**What**: Add `api_error(code, message, detail="", status=400)` helper returning `JSONResponse`. Replace all bare `raise HTTPException(...)` with `api_error(...)`. Ensure all handlers return the `{ "error", "code", "detail" }` shape on failures.  
**Acceptance**:
- Every 4xx/5xx response has `error`, `code`, `detail` fields.
- Existing `data.error` checks in the frontend continue to work.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 3.3 — CORS Restriction & Security Headers
**Files**: `server.py` (update), `config.py` (update)  
**What**: Replace `allow_origins=["*"]` with `allow_origins=settings.allowed_origins`. Add `SecurityHeadersMiddleware` that injects `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` into HTML responses.  
**Acceptance**:
- With `ALLOWED_ORIGINS=https://myapp.com`, CORS preflight from another origin is rejected.
- With `ENVIRONMENT=development`, `ALLOWED_ORIGINS` defaults to `["*"]`.
- HTML responses include all four security headers.
- JSON API responses are not affected by the HTML CSP.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 0.1  
**Risk**: Low

---

### Task 3.4 — API Key Security Audit
**Files**: `server.py` (review), `knowledge.py` (review)  
**What**: Audit every code path to confirm: API key never appears in any response body or log line. Use `mask_key()` from `logger.py` before logging any value that could be an API key. Add a `_strip_key(data)` guard that recursively removes `api_key` fields from response dicts before serialisation.  
**Acceptance**:
- `GET /api/status` does not contain the key value.
- `/api/process` and `/api/rag` responses contain no `api_key` field.
- Test with a recognisable dummy key confirms it never appears in log output.
**Tests**: `tests/test_server.py` — key-leak assertions  
**Depends on**: Task 0.2  
**Risk**: Low

---

## Phase 4 — New API Features

### Task 4.1 — `/api/health` Endpoint
**Files**: `server.py` (update)  
**What**: Add `GET /api/health`. Checks: Sarvam API reachability (lightweight HEAD or minimal POST with a timeout of 5 s), storage availability (can read the DB file), disk free space via `shutil.disk_usage`, Python version, server uptime (recorded at startup).  
**Acceptance**:
- Returns HTTP 200 with full `checks` dict.
- If Sarvam is unreachable, `checks.sarvam_api = "unreachable"` but HTTP is still 200.
- If storage is unavailable, `checks.storage = "error"`.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 0.1, 2.2  
**Risk**: Low

---

### Task 4.2 — `/api/chunk-preview` Endpoint
**Files**: `server.py` (update)  
**What**: Add `POST /api/chunk-preview` accepting JSON `{ "text": str, "chunk_size": int, "overlap": int }`. Returns chunks array. No LLM call. Input text capped at 50,000 chars (HTTP 400 otherwise).  
**Acceptance**:
- Returns chunks within 500 ms for a 10,000-char input.
- Text > 50,000 chars returns HTTP 400.
- Chunk schema matches main pipeline schema.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 1.2  
**Risk**: Low

---

### Task 4.3 — `/api/export/{format}` Endpoint
**Files**: `server.py` (update), `export.py` (use)  
**What**: Add `POST /api/export/{format}`. Accepts the full pipeline response JSON in the request body. Returns the formatted file as a download with `Content-Disposition: attachment` and the correct MIME type. Formats: `jsonl`, `json`, `csv`, `md`. Unsupported format → HTTP 400.  
**Acceptance**:
- `POST /api/export/jsonl` → `application/x-jsonlines`, attachment header.
- `POST /api/export/csv` → `text/csv`, attachment header.
- `POST /api/export/md` → `text/markdown`, attachment header.
- `POST /api/export/xyz` → HTTP 400.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 1.6  
**Risk**: Low

---

### Task 4.4 — Extended `/api/process` Parameters
**Files**: `server.py` (update)  
**What**: Add optional form fields: `chunk_size`, `overlap`, `num_facts`, `num_qa_pairs`, `top_k`. Pass through to `create_chunks` and `synthesize_knowledge`. All default to `settings.*` values.  
**Acceptance**:
- Existing calls with no new fields produce identical output.
- `num_qa_pairs=7` returns 7 QA pairs when LLM complies.
- `chunk_size=200` produces smaller chunks.
**Tests**: `tests/test_server.py`  
**Depends on**: Task 1.2, 1.3  
**Risk**: Low

---

### Task 4.5 — DOCX Support
**Files**: `ingest.py` (update), `server.py` (update), `requirements.txt` (add python-docx)  
**What**: Add `extract_text_from_docx(docx_bytes)`. Update `/api/process` to route `.docx` uploads to it. Magic-byte check (`PK\x03\x04`) in `validate_upload` already covers this.  
**Acceptance**:
- Valid `.docx` upload returns a successful pipeline result.
- `.xlsx` upload (also PK header) is rejected by extension check alongside magic-byte check.
- Existing PDF and TXT processing unchanged.
**Tests**: `tests/test_ingest.py`  
**Depends on**: Task 1.1, 3.1  
**Risk**: Low

---

## Phase 5 — Extensibility Interfaces & Stubs

### Task 5.1 — `interfaces/` — ABCs
**Files**: `interfaces/__init__.py`, `interfaces/retrieval.py`, `interfaces/synthesis.py`, `interfaces/evaluation.py` (all new)  
**What**: Define `RetrievalBackend`, `SynthesisBackend`, `EvaluationBackend` ABCs with full method signatures, type hints, and docstrings. Each method raises `NotImplementedError` by default. Existing `rag.py`, `knowledge.py`, `quality.py` modules are updated to note in their docstrings that they are the default implementations of the respective interfaces (but do not formally inherit from the ABCs yet — no forced migration).  
**Acceptance**:
- All three ABCs are importable without error.
- Instantiating any ABC directly raises `TypeError`.
- `StorageBackend` (from Phase 2) is documented as the storage interface.
**Depends on**: Task 2.1  
**Risk**: Low

---

### Task 5.2 — `extensions/` — Stub Modules
**Files**: `extensions/__init__.py`, `extensions/vector_retrieval.py`, `extensions/hybrid_retrieval.py`, `extensions/multi_document.py`, `extensions/knowledge_graph.py`, `extensions/advanced_eval.py`, `extensions/human_review.py` (all new)  
**What**: Each stub module contains: a module docstring explaining what it will provide in v3+, a `NotImplementedError`-raising placeholder class that references the relevant interface, and a `__all__` export list.  
**Acceptance**:
- All stub modules importable without error.
- No implementation logic in any stub.
- Module docstrings describe the future capability.
**Depends on**: Task 5.1  
**Risk**: Low

---

## Phase 6 — Frontend Upgrades

### Task 6.1 — Toast Notification System
**Files**: `templates/index.html` (update)  
**What**: Implement a ~50-line pure-JS toast component. Replace every `alert(...)` call with `showToast(message, type)`. Types: `success` (emerald), `error` (red), `info` (blue), `warning` (amber). Stacks in top-right, auto-dismisses after 4 s, manual close via ×.  
**Acceptance**:
- Zero `alert()` calls remain.
- Successful run → green toast.
- API error → red toast with message.
- Multiple concurrent toasts stack without overlap.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 6.2 — Chunk Size / Overlap Controls
**Files**: `templates/index.html` (update)  
**What**: Add a collapsible "Advanced Options" section below the file input: Chunk Size slider (200–1000, step 50, default 550) with value label; Overlap slider (0–200, step 10, default 80) with value label. Submit both as form fields to `/api/process`.  
**Acceptance**:
- Sliders display current value.
- Custom values are sent in the form data.
- Defaults match server defaults.
**Depends on**: Task 4.4  
**Risk**: Low

---

### Task 6.3 — Config Modal: Num Facts / QA Pairs
**Files**: `templates/index.html` (update)  
**What**: Add `num_facts` (1–15, default 3) and `num_qa_pairs` (1–15, default 3) number inputs to the Sarvam AI Configuration modal. Store in JS state; submit with `/api/process` and `/api/sample` requests.  
**Acceptance**:
- Changing values in the modal and processing sends the correct parameters.
- Existing API key save functionality is unchanged.
**Depends on**: Task 4.4  
**Risk**: Low

---

### Task 6.4 — localStorage Session Persistence
**Files**: `templates/index.html` (update)  
**What**: After `renderPipelineResults()`, serialize `currentPipelineData` to `localStorage['kp_last_run']`. On `DOMContentLoaded`, if valid data exists (must have `chunks` and `knowledge`), show a restore banner. "Restore" → call `renderPipelineResults()`. "Dismiss" → hide for this session.  
**Acceptance**:
- After processing and refreshing, the restore banner appears.
- "Restore" fully re-populates all six tabs.
- "Dismiss" hides the banner and does not restore on next load within the same session.
- Invalid/corrupt stored data is silently discarded and banner is not shown.
**Depends on**: Task 6.1  
**Risk**: Low

---

### Task 6.5 — Document Info Bar
**Files**: `templates/index.html` (update)  
**What**: After processing, show a dismissible info bar: filename · pages · chunks · processed-at (ISO timestamp) · model · mode (LIVE or SIMULATED badge).  
**Acceptance**:
- All six data points displayed after a successful run.
- Dismissible via ×.
- Hidden before first run.
- "SIMULATED" badge shown in amber when `data.mode === "simulated"`.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 6.6 — Loading Skeletons
**Files**: `templates/index.html` (update)  
**What**: During `showProgress()`, replace tab content areas with 3–4 animated grey skeleton lines (CSS `animate-pulse`). `renderPipelineResults()` removes skeletons and renders real content.  
**Acceptance**:
- Skeletons visible on all six tabs during processing.
- Correctly replaced by real content on completion or error.
**Depends on**: Nothing  
**Risk**: Low

---

### Task 6.7 — Batch Progress Display
**Files**: `templates/index.html` (update)  
**What**: Update `showProgress()` to accept an optional batch position string. The server sends progress events as the pipeline runs (or the frontend polls). If polling is not feasible, at minimum display the batch stats returned in the completed response on the Quality tab: a new "Batch Processing" card showing total / processed / skipped / failed.  
**Acceptance**:
- Quality tab displays batch stats card after processing.
- Failed batch count shown in red if > 0.
- Stats card hidden if `batch_processing_stats` is absent.
**Depends on**: Task 1.3  
**Risk**: Low

---

### Task 6.8 — RAG Keyboard Shortcut & UX
**Files**: `templates/index.html` (update)  
**What**: `Enter` key in `#ragQueryInput` triggers `askRAG()`. Empty input shows error toast. Auto-scroll to `#ragResults` after completion.  
**Acceptance**:
- Enter fires the query.
- Empty input shows toast, no network call made.
- Page scrolls to results area after receiving a response.
**Depends on**: Task 6.1  
**Risk**: Low

---

## Phase 7 — Test Suite

All tests use the `mock_sarvam_response` fixture from `conftest.py`. No test makes a live Sarvam API call.

### Task 7.1 — `tests/test_ingest.py`
Tests: PDF extraction (smoke, multi-page), TXT extraction, DOCX extraction, encoding-error warning, `validate_upload` (size limit, MIME allowlist, magic bytes, filename sanitisation), `word_count` field, `cleanup_temp_file`.  
**Target**: ≥ 80% coverage of `ingest.py`  
**Depends on**: Task 1.1, 4.5

---

### Task 7.2 — `tests/test_chunking.py`
Tests: `min_chunk_length` filter, sentence-level overlap (verify no mid-sentence cuts), overlap=0 produces no overlap, chunk ID sequence, `word_count` field, empty input, single paragraph, multi-page input, no "semantic" label in docstrings.  
**Target**: ≥ 80% coverage of `chunking.py`  
**Depends on**: Task 1.2

---

### Task 7.3 — `tests/test_knowledge.py`
Tests (all with mocked Sarvam): map-reduce covers all chunks (not just first 3), citation preservation through reduce step, schema validation (`_validate_knowledge_schema`), simulated mode returns `"mode": "simulated"`, live mode returns `"mode": "live"`, retry on timeout (mock raises `Timeout` twice then succeeds), batch failure handling (one batch fails → others continue, `failed: 1` in stats), rate-limit response (HTTP 429) triggers back-off, malformed JSON response falls back gracefully, API key never appears in log output.  
**Target**: ≥ 80% coverage of `knowledge.py`  
**Depends on**: Task 0.3, 1.3

---

### Task 7.4 — `tests/test_quality.py`
Tests: Jaccard identical/disjoint/partial, `compute_tfidf_cosine` identical/disjoint, `evaluate_dataset_quality` with duplicate chunks, grounding with valid/mismatched/missing citation, `per_qa_grounding` presence, `quality_flags` for high redundancy and low grounding, configurable threshold.  
**Target**: ≥ 80% coverage of `quality.py`  
**Depends on**: Task 1.4

---

### Task 7.5 — `tests/test_rag.py`
Tests: scoring correctness, top_k limiting, `min_score` filter (zero and non-zero), empty chunk list, single chunk, query with no matching words.  
**Target**: ≥ 80% coverage of `rag.py`  
**Depends on**: Task 1.5

---

### Task 7.6 — `tests/test_export.py`
Tests: `to_jsonl` parseable, `to_csv` correct header + rows, `to_json` schema keys, `to_markdown` headings, all formats include `batch_processing_stats` when present, empty QA dataset edge case.  
**Target**: ≥ 80% coverage of `export.py`  
**Depends on**: Task 1.6

---

### Task 7.7 — `tests/test_storage.py`
Tests: save/load round-trip, `list_documents`, `delete_document`, idempotent save, missing doc_id returns None, evaluation save/query, DB survives process restart (tmp dir fixture).  
**Target**: ≥ 80% coverage of `storage/sqlite_store.py`  
**Depends on**: Task 2.2

---

### Task 7.8 — `tests/test_server.py`
Tests: `GET /api/status`, `GET /api/health`, `POST /api/sample` (mocked), `POST /api/process` (TXT fixture, mocked), `POST /api/rag` (mocked), `POST /api/chunk-preview`, `POST /api/export/jsonl`, `POST /api/export/csv`, upload too large, unsupported file type, API key leak checks (key not in response body or logs), CORS header presence, security headers in HTML response, document storage endpoints (list, get, delete).  
**Target**: All endpoint happy paths + major error paths  
**Depends on**: All Phase 0–5 tasks

---

## Phase 8 — Documentation Update

### Task 8.1 — Update `system.md` and `.env.example`
**Files**: `system.md` (update), `.env.example` (update)  
**What**: Update `system.md` to: reflect v2.0 architecture diagram, correct all references from "semantic chunking" to "boundary-aware chunking", remove invalid model identifiers (`sarvam-30b`, `sarvam-2b`) or mark them as unverified, document all new endpoints, document hierarchical synthesis strategy, document storage layer, document extensibility interfaces. Update `.env.example` with all new environment variables and their defaults.  
**Depends on**: All phases  
**Risk**: Low

---

## Execution Order & Dependencies

```
Phase 0:  0.1 → 0.2 → 0.3 + 0.4              (foundation — parallelisable after 0.1)
Phase 1:  1.1 + 1.2 → 1.3 → 1.4 + 1.5 + 1.6  (1.1 and 1.2 parallel; 1.3 after both)
Phase 2:  2.1 → 2.2 → 2.3                      (storage layer — sequential)
Phase 3:  3.1 + 3.2 + 3.3 + 3.4               (all parallelisable)
Phase 4:  4.1 + 4.2 → 4.3 + 4.4 → 4.5         (mostly parallel)
Phase 5:  5.1 → 5.2                             (quick, sequential)
Phase 6:  6.1 → 6.2 + 6.3 → 6.4 → 6.5 + 6.6 + 6.7 + 6.8   (frontend)
Phase 7:  7.1–7.8 (mostly parallel, per module)
Phase 8:  8.1 (after all phases)
```

**Total tasks**: 34  
**High-risk tasks**: Task 1.3 (map-reduce synthesis — core logic replacement)  
**Medium-risk tasks**: Task 1.2 (overlap fix — must not regress chunking)  
**All other tasks**: Low risk
