# AI Knowledge Engineering Platform v2.0

An AI-powered Knowledge Engineering Platform that transforms unstructured documents (PDFs, TXT, MD, DOCX) into structured, validated, AI-ready knowledge datasets with interactive RAG benchmarks using **Sarvam AI**.

---

## 🚀 Quickstart

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

For development and testing:
```powershell
pip install -r requirements-dev.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set your Sarvam API key:
```env
SARVAM_API_KEY=your_actual_sarvam_api_key_here
SARVAM_MODEL=sarvam-105b
```

### 3. Launch
```powershell
python server.py
```
Open your browser at: **`http://127.0.0.1:8000`**

The platform runs in **simulated mode** without an API key — all features work with pre-generated mock data clearly tagged `mode: simulated`.

---

## 🛠️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                Browser (index.html)                 │
│  Tailwind CDN · Lucide Icons · Vanilla JS           │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / JSON
┌──────────────────────▼──────────────────────────────┐
│              FastAPI (server.py)                    │
│  /api/status  /api/process  /api/rag                │
│  /api/health  /api/chunk-preview  /api/export/{fmt} │
│  /api/documents (CRUD)                              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           pipeline.py (backward-compatible facade)  │
│  ingest.py · chunking.py · knowledge.py             │
│  quality.py · rag.py · export.py                    │
└──────────────────────┬──────────────────────────────┘
                       │
┌────────┬─────────────┴──────────────────────────────┐
│Storage │ Sarvam AI API                               │
│SQLite  │ POST /v1/chat/completions                   │
│+ JSON  │ Auth: api-subscription-key header           │
└────────┴────────────────────────────────────────────┘
```

---

## 📋 Pipeline Stages

1. **Document Ingestion** — PDF, TXT, MD, DOCX. Page-level extraction with word/char counts. Magic-byte MIME validation. Configurable size limit.
2. **Boundary-Aware Chunking** — Respects paragraph and sentence delimiters. Sentence-level overlap (whole sentences, not character fractions). Configurable chunk size and overlap.
3. **Hierarchical Map-Reduce Synthesis** — ALL chunks are processed (no silent omissions). Configurable batch size. Per-batch retry. Citations preserved through all stages. Results tagged `mode: live` or `mode: simulated`.
4. **Quality & Deduplication** — Jaccard + TF-IDF cosine similarity. Configurable similarity threshold. Per-QA grounding status. Quality flags.
5. **Interactive RAG** — Keyword retrieval with relevance scoring. Configurable top-k and minimum score.
6. **Persistent Storage** — SQLite metadata + JSON result files. Full document CRUD API.
7. **Multi-Format Export** — JSONL (Alpaca), JSON, CSV, Markdown.

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web dashboard |
| GET | `/api/status` | Key status, model, version |
| GET | `/api/health` | Deep health check |
| POST | `/api/sample` | Demo pipeline on sample doc |
| POST | `/api/process` | Full document pipeline |
| POST | `/api/rag` | RAG query + grounded answer |
| POST | `/api/chunk-preview` | Preview chunks (no LLM) |
| POST | `/api/export/{fmt}` | Server-side download (jsonl/json/csv/md) |
| GET | `/api/documents` | List stored documents |
| GET | `/api/documents/{id}` | Get stored result |
| DELETE | `/api/documents/{id}` | Delete stored result |

---

## 🔑 Sarvam AI API

- **Endpoint**: `https://api.sarvam.ai/v1/chat/completions`
- **Primary auth header**: `api-subscription-key: <key>` (per official docs)
- **Secondary auth**: `Authorization: Bearer <key>` (OpenAI-compatible)
- **Valid models** (verified Nov 2025):
  - `sarvam-105b` — 128K context, complex reasoning (default)
  - `sarvam-105b-conversations` — 32K context, conversational
- **Note**: `sarvam-30b` and `sarvam-2b` are **not valid** model identifiers.

---

## 🏗️ Project Structure

```
LLM KN/
├── config.py               Centralised settings (all env vars)
├── logger.py               Structured JSON logging + StageTimer
├── pipeline.py             Backward-compatible facade
├── server.py               FastAPI application
├── ingest.py               Document extraction + validation
├── chunking.py             Boundary-aware chunking (fixed overlap)
├── knowledge.py            Map-reduce synthesis via Sarvam AI
├── quality.py              Jaccard + TF-IDF + grounding evaluation
├── rag.py                  Keyword retrieval + grounded answers
├── export.py               JSONL/JSON/CSV/Markdown formatters
├── storage/
│   ├── backend.py          StorageBackend ABC
│   └── sqlite_store.py     SQLite + JSON file implementation
├── interfaces/             ABCs for future backend swapping
│   ├── retrieval.py
│   ├── synthesis.py
│   └── evaluation.py
├── extensions/             Stubs for v3+ capabilities
│   ├── vector_retrieval.py
│   ├── hybrid_retrieval.py
│   ├── multi_document.py
│   ├── knowledge_graph.py
│   ├── advanced_eval.py
│   └── human_review.py
├── templates/index.html    Single-page dashboard
├── tests/                  Unit + integration tests (209 passing)
├── data/                   Runtime storage (gitignored)
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── .gitignore
```

---

## 🧪 Running Tests

```powershell
# All tests (209 total)
python -m pytest tests/ -q

# Specific module
python -m pytest tests/test_knowledge.py -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

**Policy**: No test makes a live Sarvam API call. All API interactions use mocked responses.

---

## ⚙️ Environment Variables

See `.env.example` for the complete list with defaults.

Key variables:
- `SARVAM_API_KEY` — your Sarvam AI subscription key
- `SARVAM_MODEL` — model identifier (default: `sarvam-105b`)
- `MAX_UPLOAD_SIZE_MB` — upload size limit (default: 20)
- `SYNTHESIS_BATCH_SIZE` — chunks per synthesis batch (default: 3)
- `STORAGE_DIR` — storage directory (default: `./data/`)
- `ENVIRONMENT` — `development` or `production` (affects CORS + CSP)

---

## 🔒 Security

- MIME validation via magic bytes (not just extension)
- Configurable upload size limit
- CORS restricted to `ALLOWED_ORIGINS` (wildcard only in development)
- Security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- API key never appears in logs or responses (masked as `***`)
- Temp files cleaned up on all paths including error paths
