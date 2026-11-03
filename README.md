<div align="center">

<img src="https://img.shields.io/badge/Powered%20by-Sarvam%20AI-7c3aed?style=for-the-badge&logo=sparkles&logoColor=white"/>
<img src="https://img.shields.io/badge/Frontend-React%2019%20%7C%20Vite%20%7C%20TypeScript-61dafb?style=for-the-badge&logo=react&logoColor=black"/>
<img src="https://img.shields.io/badge/Styling-Tailwind%20CSS-38bdf8?style=for-the-badge&logo=tailwindcss&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Tests-209%20Passing-22c55e?style=for-the-badge&logo=pytest&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge"/>

<br/><br/>

# 🧠 AI Knowledge Engineering Platform

### *Transform unstructured documents into production-ready AI datasets — powered by Sarvam AI*

<br/>

> **Upload a PDF. Get structured facts, synthetic Q&A pairs, grounding scores, and fine-tuning datasets — in seconds.**

<br/>

[🚀 Quickstart](#-quickstart) · [✨ Features](#-features) · [🏗️ Architecture](#️-architecture) · [📡 API Reference](#-api-reference) · [🧪 Tests](#-running-tests) · [⚙️ Config](#️-configuration)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📄 Smart Document Ingestion
- PDF, TXT, Markdown, DOCX support
- Magic-byte MIME validation (not just extension)
- Per-page word & character counts
- Encoding error detection with graceful fallback
- Configurable upload size limit

</td>
<td width="50%">

### ✂️ Boundary-Aware Chunking
- Respects sentence & paragraph boundaries
- **Fixed overlap** — whole sentences, not character fractions
- Configurable chunk size & overlap via UI sliders
- Minimum chunk length filter (no micro-fragments)
- Live chunk preview endpoint (no LLM call needed)

</td>
</tr>
<tr>
<td width="50%">

### 🤖 Hierarchical Map-Reduce Synthesis
- **Every chunk processed** — nothing silently omitted
- Configurable batch size with per-batch retry
- Exponential back-off + HTTP 429 rate-limit handling
- Source citations preserved through all merge stages
- Clearly tagged `mode: live` vs `mode: simulated`

</td>
<td width="50%">

### 🔍 Quality & Deduplication Engine
- Jaccard similarity + TF-IDF cosine metrics
- Per-QA grounding status verification
- Configurable similarity threshold
- Quality flags: `low_grounding`, `high_redundancy`, `failed_batches`
- Batch processing stats surfaced in the UI

</td>
</tr>
<tr>
<td width="50%">

### 💾 Persistent Storage
- SQLite metadata + JSON result files
- Atomic writes (tmp → rename, no corrupt records)
- Full document CRUD API
- Designed for PostgreSQL / vector DB migration
- `StorageBackend` ABC as the single swap point

</td>
<td width="50%">

### 📦 Multi-Format Export
- **JSONL** — Alpaca/HuggingFace fine-tuning format
- **JSON** — Full knowledge graph for vector DB ingestion
- **CSV** — Human review & annotation audits
- **Markdown** — Readable report with metrics
- Client-side *and* server-side download endpoints

</td>
</tr>
</table>

---

## 🚀 Quickstart

### 1 · Clone & Install

```bash
git clone https://github.com/shravanithool17/Sarvam_LLM_KnowledgeBaseSystem.git
cd Sarvam_LLM_KnowledgeBaseSystem

pip install -r requirements.txt
```

### 2 · Configure

```bash
cp .env.example .env
```

Open `.env` and add your Sarvam AI key:

```env
SARVAM_API_KEY=your_key_here      # get from dashboard.sarvam.ai
SARVAM_MODEL=sarvam-105b          # or sarvam-105b-conversations
```

> **No key?** The platform runs in **simulated mode** — all features work with realistic mock data, clearly labelled.

### 3 · Launch Backend & React SaaS Frontend

**Terminal 1 — Backend (FastAPI):**
```bash
python server.py
# Server running at http://127.0.0.1:8000
```

**Terminal 2 — Premium React SaaS Frontend:**
```bash
cd frontend
npm install
npm run dev
# Frontend running at http://localhost:5173
```

Open **[http://localhost:5173](http://localhost:5173)** to experience the full React SaaS application! 🎉

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Browser  (index.html)                         │
│   Tailwind CSS  ·  Lucide Icons  ·  Vanilla JS  ·  localStorage    │
│   Toast notifications  ·  Skeletons  ·  Chunk sliders  ·  Session  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  REST / JSON
┌──────────────────────────────▼──────────────────────────────────────┐
│                       FastAPI  (server.py)                          │
│                                                                     │
│  /api/status     /api/process    /api/rag     /api/health           │
│  /api/sample     /api/export     /api/chunk-preview                 │
│  /api/documents  (list · get · delete)                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                  pipeline.py  (backward-compatible facade)          │
│                                                                     │
│   ingest.py      chunking.py      knowledge.py   (map-reduce)      │
│   quality.py     rag.py           export.py                         │
│                                                                     │
│   storage/sqlite_store.py  ←→  storage/backend.py  (ABC)           │
│   interfaces/  (RetrievalBackend · SynthesisBackend · EvalBackend)  │
│   extensions/  (vector, hybrid, multi-doc, graph — stubs for v3)   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTPS  ·  api-subscription-key
┌──────────────────────────────▼──────────────────────────────────────┐
│                       Sarvam AI API                                 │
│            POST /v1/chat/completions                                │
│            sarvam-105b  (128K ctx)  ·  sarvam-105b-conversations    │
└─────────────────────────────────────────────────────────────────────┘
```

### Pipeline Flow

```
Upload PDF/TXT/DOCX
        │
        ▼
 validate_upload()          ← magic-byte MIME check + size limit
        │
        ▼
 extract_text_from_*()      ← page-level extraction with word counts
        │
        ▼
 create_chunks()            ← boundary-aware, sentence-level overlap
        │
        ▼
  ┌─────┴──────┐
  │  MAP phase │   synthesise each batch independently via Sarvam AI
  └─────┬──────┘        ↑ retry + back-off per batch
        │
  ┌─────┴──────┐
  │ REDUCE     │   merge summaries via LLM · concat facts & QA pairs
  └─────┬──────┘        ↑ citations preserved throughout
        │
        ▼
 evaluate_dataset_quality() ← Jaccard + cosine · grounding · flags
        │
        ▼
 SQLiteStore.save_*()       ← metadata + result.json + evaluation
        │
        ▼
 JSON response → dashboard  ← mode: live | simulated
```

---

## 🖥️ Dashboard Preview

The web dashboard is a **6-tab dark glassmorphic SPA**:

| Tab | What you see |
|-----|-------------|
| 🔮 **AI Knowledge Synthesis** | Executive summary · Structured fact & entity matrix with citations |
| 💬 **Instruction Q&A Dataset** | Generated instruction-response pairs ready for fine-tuning |
| ✂️ **Chunks Inspector** | Every boundary-aware chunk with ID, page, token count |
| 🛡️ **Quality & Dedup Bench** | Health score · Grounding % · Redundancy rate · Batch stats |
| 🔍 **Interactive RAG** | Ask questions, get grounded answers with source citations |
| 📥 **Export Hub** | One-click JSONL / JSON / CSV download |

**New in v2:**
- 🔔 Toast notifications (no more browser `alert()`)
- ⚙️ Chunk size + overlap sliders
- 🔄 Session restore from `localStorage`
- 💀 Loading skeletons on all tabs
- 📊 Batch processing stats card
- 🏷️ LIVE / SIMULATED mode badge

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web dashboard |
| `GET` | `/api/status` | Key status, active model, version |
| `GET` | `/api/health` | Deep health check (Sarvam, storage, disk) |
| `POST` | `/api/sample` | Run pipeline on built-in sample document |
| `POST` | `/api/process` | Upload & process a document |
| `POST` | `/api/rag` | RAG query with grounded answer |
| `POST` | `/api/chunk-preview` | Preview chunking (no LLM call) |
| `POST` | `/api/export/{fmt}` | Download `jsonl` / `json` / `csv` / `md` |
| `GET` | `/api/documents` | List all stored documents |
| `GET` | `/api/documents/{id}` | Retrieve a stored result |
| `DELETE` | `/api/documents/{id}` | Delete a stored result |

### `/api/process` — key parameters

```bash
curl -X POST http://localhost:8000/api/process \
  -F "file=@document.pdf" \
  -F "model=sarvam-105b" \
  -F "chunk_size=550" \
  -F "overlap=80" \
  -F "num_facts=5" \
  -F "num_qa_pairs=5"
```

### Response shape

```json
{
  "document_id":   "uuid-v4",
  "document_name": "document.pdf",
  "mode":          "live | simulated",
  "stats":         { "total_pages": 8, "total_chunks": 24, "total_chars": 48000 },
  "chunks":        [ { "id": "CHK-001", "page": 1, "text": "...", "word_count": 88 } ],
  "knowledge": {
    "summary":    "3-sentence executive synthesis...",
    "facts":      [ { "entity": "...", "category": "...", "fact": "...", "citation": "CHK-003" } ],
    "qa_dataset": [ { "id": "QA-001", "instruction": "...", "response": "...", "citation": "CHK-003" } ]
  },
  "evaluation": {
    "overall_health_score": 87,
    "grounding_score": 93.0,
    "redundancy_rate": 2.1,
    "per_qa_grounding": [ { "id": "QA-001", "grounded": true, "citation_valid": true } ],
    "quality_flags": []
  },
  "batch_processing_stats": { "total_batches": 8, "processed": 8, "failed": 0 }
}
```

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all 209 tests
pytest tests/ -q

# Run a specific module
pytest tests/test_knowledge.py -v

# With coverage report
pytest tests/ --cov=. --cov-report=term-missing
```

**Test policy**: No test makes a live Sarvam API call. All HTTP interactions use mocked responses — zero API credits consumed by the test suite.

| Module | Tests | Coverage |
|--------|-------|---------|
| `test_ingest.py` | 39 | ingest.py |
| `test_chunking.py` | 24 | chunking.py |
| `test_knowledge.py` | 21 | knowledge.py |
| `test_quality.py` | 22 | quality.py |
| `test_rag.py` | 11 | rag.py |
| `test_export.py` | 18 | export.py |
| `test_storage.py` | 19 | sqlite_store.py |
| `test_server.py` | 43 | server.py |
| **Total** | **209** | **0 failures** |

---

## ⚙️ Configuration

All settings are loaded from `.env` — copy `.env.example` to get started.

| Variable | Default | Description |
|----------|---------|-------------|
| `SARVAM_API_KEY` | *(required)* | Your Sarvam AI subscription key |
| `SARVAM_MODEL` | `sarvam-105b` | Model: `sarvam-105b` or `sarvam-105b-conversations` |
| `SARVAM_TIMEOUT` | `90` | API request timeout in seconds |
| `SARVAM_MAX_RETRIES` | `2` | Retry attempts on transient errors |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum upload file size |
| `DEFAULT_CHUNK_SIZE` | `600` | Target chunk size in characters |
| `DEFAULT_OVERLAP` | `100` | Overlap in characters (whole sentences) |
| `SYNTHESIS_BATCH_SIZE` | `3` | Chunks per synthesis batch |
| `DEFAULT_NUM_FACTS` | `3` | Facts generated per batch |
| `DEFAULT_NUM_QA_PAIRS` | `3` | Q&A pairs generated per batch |
| `SIMILARITY_THRESHOLD` | `0.45` | Jaccard threshold for duplicate detection |
| `STORAGE_DIR` | `./data/` | SQLite + JSON storage directory |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `ALLOWED_ORIGINS` | `*` (dev only) | CORS allowlist for production |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 🗂️ Project Structure

```
📦 Sarvam_LLM_KnowledgeBaseSystem
├── 🐍 config.py                  Centralised settings (all env vars)
├── 🐍 logger.py                  Structured JSON logging + StageTimer
├── 🐍 pipeline.py                Backward-compatible public API facade
├── 🐍 server.py                  FastAPI application
│
├── 🐍 ingest.py                  PDF / TXT / DOCX extraction + validation
├── 🐍 chunking.py                Boundary-aware chunking (fixed overlap)
├── 🐍 knowledge.py               Map-reduce synthesis via Sarvam AI
├── 🐍 quality.py                 Deduplication + grounding evaluation
├── 🐍 rag.py                     Keyword retrieval + grounded answers
├── 🐍 export.py                  JSONL / JSON / CSV / Markdown formatters
│
├── 📁 storage/
│   ├── backend.py                StorageBackend ABC (migration boundary)
│   └── sqlite_store.py           Default: SQLite + JSON files
│
├── 📁 interfaces/                ABCs for pluggable backends (v3+)
│   ├── retrieval.py              RetrievalBackend
│   ├── synthesis.py              SynthesisBackend
│   └── evaluation.py             EvaluationBackend
│
├── 📁 extensions/                Stubs for future capabilities
│   ├── vector_retrieval.py       → Chroma / Pinecone / Weaviate
│   ├── hybrid_retrieval.py       → BM25 + vector fusion
│   ├── multi_document.py         → Cross-document synthesis
│   ├── knowledge_graph.py        → Entity-relationship graphs
│   ├── advanced_eval.py          → LLM-as-judge, BLEU/ROUGE
│   └── human_review.py           → Annotation workflow
│
├── 📁 templates/
│   └── index.html                Dark glassmorphic SPA (6 tabs)
│
├── 📁 tests/                     209 tests, 0 failures, 0 live API calls
│   ├── conftest.py               Shared fixtures + mock_sarvam_response
│   ├── test_ingest.py
│   ├── test_chunking.py
│   ├── test_knowledge.py
│   ├── test_quality.py
│   ├── test_rag.py
│   ├── test_export.py
│   ├── test_storage.py
│   ├── test_server.py
│   └── fixtures/
│       ├── sample.txt
│       └── sample.pdf
│
├── 📄 requirements.txt
├── 📄 requirements-dev.txt
├── 📄 .env.example
├── 📄 pytest.ini
└── 📄 .gitignore
```

---

## 🔒 Security

- **Magic-byte MIME validation** — file signature checked, not just extension
- **Configurable upload size limit** — default 20 MB, override via env
- **CORS allowlist** — wildcard only in `development` mode
- **Security headers** — CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **API key isolation** — masked as `***` in all logs, stripped from all responses
- **Temp file cleanup** — `try/finally` on all upload handlers, including error paths
- **Atomic storage writes** — write to `.tmp`, then rename; no partial JSON files

---

## 🗺️ Roadmap

| Version | Planned capability |
|---------|-------------------|
| **v2** *(current)* | Map-reduce synthesis · SQLite storage · Security hardening · 209 tests |
| **v3** | Vector DB retrieval (Chroma / Pinecone) · Hybrid BM25+vector search |
| **v3** | Multi-document cross-synthesis · Knowledge graph generation |
| **v3** | LLM-as-judge evaluation · Human-in-the-loop review workflow |
| **v3** | PostgreSQL backend · Multi-user sessions · Streaming responses |

Interface stubs for all v3 features are already in the `extensions/` and `interfaces/` directories — no redesign required.

---

## 🙏 Acknowledgements

- **[Sarvam AI](https://www.sarvam.ai/)** — for `sarvam-105b`, India's frontier language model
- **[FastAPI](https://fastapi.tiangolo.com/)** — high-performance async Python API framework
- **[Tailwind CSS](https://tailwindcss.com/)** — utility-first CSS framework for the dashboard
- **[pypdf](https://github.com/py-pdf/pypdf)** — PDF text extraction
- **[python-docx](https://python-docx.readthedocs.io/)** — DOCX support

---

<div align="center">

Built with ❤️ using **Sarvam AI** · **FastAPI** · **Python**

<br/>

⭐ Star this repo if it helped you build something cool!

</div>
