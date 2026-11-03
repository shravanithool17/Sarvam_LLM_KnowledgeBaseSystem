"""
server.py — FastAPI application for the AI Knowledge Engineering Platform.

All existing API contracts (/api/status, /api/sample, /api/process, /api/rag)
are preserved exactly. New endpoints are additive only.

Security:
  - Upload MIME + magic-byte validation via ingest.validate_upload()
  - Configurable CORS via settings.allowed_origins
  - Security headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
  - API key never returned in any response
  - Temp file cleanup on all paths including errors
  - Structured error responses with consistent {error, code, detail} shape
"""

import io
import os
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import pipeline
from config import settings
from logger import get_logger
from ingest import validate_upload, build_ingestion_summary
from storage.sqlite_store import SQLiteStore
from export import to_jsonl, to_json, to_csv, to_markdown

load_dotenv()

log = get_logger("server")

app = FastAPI(
    title="AI Knowledge Engineering Platform",
    version="2.0.0",
    description="Transforms unstructured documents into structured AI-ready knowledge datasets via Sarvam AI.",
)

# ---------------------------------------------------------------------------
# CORS — wildcard only in development mode
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Injects security headers into all HTML responses."""
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.environment == "production":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.tailwindcss.com https://unpkg.com 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self';"
            )
        else:
            # Permissive in development to support CDN resources
            response.headers["Content-Security-Policy"] = (
                "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
            )
    return response

# ---------------------------------------------------------------------------
# Storage — initialised once at startup
# ---------------------------------------------------------------------------
_storage = SQLiteStore(storage_dir=settings.storage_dir)

# Server start time for uptime calculation
_server_start_time = time.monotonic()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Sample document (preserved exactly from original)
# ---------------------------------------------------------------------------
SAMPLE_DOCUMENT = """
HIGH-PERFORMANCE LLM KNOWLEDGE PIPELINE SPECIFICATION
Author: Advanced Knowledge Engineering Group
Domain: Retrieval-Augmented Generation (RAG) & Fine-Tuning Dataset Creation

1. Executive Summary
Modern enterprise AI initiatives fail when fed unstructured, noisy documents. Typical PDF chatbots suffer from severe hallucination rates exceeding 35% because they rely on naive fixed-length character splitting without semantic boundary awareness. The LLM Knowledge Pipeline is an end-to-end framework that converts unstructured PDF, DOCX, and markdown files into structured, hallucination-resistant knowledge representations.

2. Boundary-Aware Chunking Strategy
Traditional splitting causes contextual fragmentation by severing sentences across arbitrary chunk limits. The pipeline implements boundary-aware chunking. Each chunk respects sentence and paragraph boundaries. Furthermore, chunks are strictly tagged with immutable source metadata: Page Number, Character Position, Token Approximation, and a unique Chunk ID (e.g., CHK-001).

3. Multilingual Knowledge Synthesis via Sarvam AI
The platform utilises Sarvam AI's language models (sarvam-105b and sarvam-105b-conversations) to execute knowledge distillation. Rather than merely summarising, the model constructs three distinct knowledge tiers:
A. Executive Knowledge Synthesis: High-density condensation of core findings.
B. Structured Entity & Fact Matrix: Key concepts, parameters, metrics, and definitions mapped to their parent chunks.
C. Synthetic Instruction-Tuning Pairs: High-quality instruction-response pairs formatted for direct consumption by fine-tuning frameworks like Alpaca, Unsloth, or Llama-Factory.

4. Traceability & Grounding Verification
Every generated Q&A pair and extracted fact must have an exact citation reference. A synthetic answer is considered ungrounded if its key semantic tokens cannot be verified within the referenced source chunk. The pipeline enforces a Grounding Verification threshold (>85%) before accepting knowledge into the final dataset.

5. Deduplication and Redundancy Benchmarking
Unstructured corpuses frequently contain duplicated sections, boilerplate headers, and repetitive clauses. The pipeline computes pair-wise similarity using Jaccard and Cosine metrics. Chunk pairs with similarity exceeding the configured threshold are flagged as redundant.

6. Downstream Export & Deployment
The validated knowledge base is exported into three standardised formats:
- JSONL: Standard Alpaca prompt-completion schema for instruction fine-tuning.
- Complete Knowledge JSON: Hierarchical graph containing chunks, facts, citations, and evaluation metrics.
- Tabular CSV: For human review, data labelling audits, and compliance inspection.
"""


# ---------------------------------------------------------------------------
# Pydantic models (preserved + extended)
# ---------------------------------------------------------------------------

class RAGRequest(BaseModel):
    query: str
    chunks: List[Dict[str, Any]]
    api_key: Optional[str] = None
    model: Optional[str] = "sarvam-105b"


class SampleRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = "sarvam-105b"


class ChunkPreviewRequest(BaseModel):
    text: str
    chunk_size: int = settings.default_chunk_size
    overlap: int = settings.default_overlap


# ---------------------------------------------------------------------------
# Error response helper
# ---------------------------------------------------------------------------

def api_error(
    code: str,
    message: str,
    detail: str = "",
    status: int = 400,
) -> JSONResponse:
    """
    Returns a structured JSONResponse for all API errors.
    Shape: { "error": str, "code": str, "detail": str }
    """
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "detail": detail},
    )


def _strip_api_key(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively removes 'api_key' fields from a response dict before serialisation.
    Ensures API keys never appear in response bodies.
    """
    if not isinstance(data, dict):
        return data
    return {
        k: _strip_api_key(v) if isinstance(v, dict) else v
        for k, v in data.items()
        if k != "api_key"
    }


# ---------------------------------------------------------------------------
# Preserved endpoints (contracts unchanged)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the React SaaS application (or built frontend)."""
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="""<!DOCTYPE html><html><body style="background:#07090e;color:#fff;font-family:sans-serif;padding:40px;text-align:center;">
        <h2>LLM Knowledge Pipeline 2.0 API is Online</h2>
        <p>The React frontend is in <code>frontend/</code> and runs via <code>npm run dev</code> at <a href="http://localhost:5173" style="color:#a855f7;">http://localhost:5173</a>.</p>
        </body></html>"""
    )


@app.get("/api/status")
async def get_status():
    """
    Returns Sarvam API key status, active model, and platform version.
    Preserved backward-compatible shape: { status, has_key, default_model }.
    """
    has_key = settings.has_api_key()
    return {
        "status": "online",
        "has_key": has_key,
        "default_model": settings.sarvam_model,
        # Additive new fields
        "version": "2.0.0",
        "valid_models": settings.VALID_SARVAM_MODELS,
        "environment": settings.environment,
    }


@app.post("/api/sample")
async def process_sample(req: SampleRequest):
    """
    Processes the pre-packaged technical sample document end-to-end.
    Preserved backward-compatible response shape.
    """
    doc_id = str(uuid.uuid4())
    pages = [{"page": 1, "text": SAMPLE_DOCUMENT.strip(), "char_count": len(SAMPLE_DOCUMENT), "word_count": len(SAMPLE_DOCUMENT.split()), "status": "ok", "error_detail": None}]
    ingestion_summary = build_ingestion_summary(pages)

    chunks = pipeline.create_chunks(pages, target_chunk_size=450, overlap=60)

    api_key = req.api_key or settings.sarvam_api_key
    active_model = settings.resolve_model(req.model or settings.sarvam_model)
    knowledge = pipeline.synthesize_knowledge(chunks, api_key=api_key, model=active_model)
    evaluation = pipeline.evaluate_dataset_quality(
        chunks,
        knowledge.get("qa_dataset", []),
        batch_processing_stats=knowledge.get("batch_processing_stats"),
    )

    result = {
        "document_name": "High-Performance_LLM_Knowledge_Pipeline_Spec.txt",
        "document_id": doc_id,
        "mode": knowledge.get("mode", "simulated"),
        "stats": {
            "total_pages": 1,
            "total_chars": len(SAMPLE_DOCUMENT),
            "total_chunks": len(chunks),
        },
        "ingestion_summary": ingestion_summary,
        "batch_processing_stats": knowledge.get("batch_processing_stats", {}),
        "chunks": chunks,
        "knowledge": knowledge,
        "evaluation": evaluation,
    }

    # Persist asynchronously (failures logged but don't break response)
    _persist_result(doc_id, result, chunks, evaluation, active_model)

    return _strip_api_key(result)


@app.post("/api/process")
async def process_document(
    file: UploadFile = File(...),
    model: str = Form(settings.sarvam_model),
    api_key: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    overlap: Optional[int] = Form(None),
    num_facts: Optional[int] = Form(None),
    num_qa_pairs: Optional[int] = Form(None),
    top_k: Optional[int] = Form(None),
):
    """
    Ingests an uploaded PDF, TXT, MD, or DOCX file and runs the full knowledge pipeline.
    Preserved backward-compatible response shape. New optional parameters are additive.
    """
    contents = await file.read()
    filename = file.filename or "uploaded_document"

    # Security: validate upload (MIME, size, magic bytes)
    try:
        safe_filename = validate_upload(filename, len(contents), contents[:8])
    except ValueError as exc:
        code = getattr(exc, "code", "INVALID_FILE_TYPE")
        status = 413 if code == "UPLOAD_TOO_LARGE" else 400
        return api_error(code, str(exc), status=status)

    doc_id = str(uuid.uuid4())

    try:
        # 1. Parse document
        ext = Path(safe_filename).suffix.lower()
        if ext == ".pdf":
            pages = pipeline.extract_text_from_pdf(io.BytesIO(contents))
        elif ext == ".docx":
            pages = pipeline.extract_text_from_docx(contents)
        else:
            pages = pipeline.extract_text_from_txt(contents)

        if not pages or not any(p.get("status") == "ok" for p in pages):
            return api_error(
                "NO_TEXT_EXTRACTED",
                "Could not extract readable text from the document.",
                detail=f"File: {safe_filename}",
                status=400,
            )

        ingestion_summary = build_ingestion_summary(pages)

        # 2. Boundary-aware chunking
        effective_chunk_size = chunk_size or settings.default_chunk_size
        effective_overlap = overlap if overlap is not None else settings.default_overlap
        chunks = pipeline.create_chunks(
            pages,
            target_chunk_size=effective_chunk_size,
            overlap=effective_overlap,
        )

        # 3. Knowledge synthesis
        active_key = api_key or settings.sarvam_api_key
        active_model = settings.resolve_model(model)
        knowledge = pipeline.synthesize_knowledge(
            chunks,
            api_key=active_key,
            model=active_model,
            num_facts=num_facts,
            num_qa_pairs=num_qa_pairs,
        )

        # 4. Quality evaluation
        evaluation = pipeline.evaluate_dataset_quality(
            chunks,
            knowledge.get("qa_dataset", []),
            batch_processing_stats=knowledge.get("batch_processing_stats"),
        )

        result = {
            "document_name": safe_filename,
            "document_id": doc_id,
            "mode": knowledge.get("mode", "simulated"),
            "stats": {
                "total_pages": len(pages),
                "total_chars": sum(p.get("char_count", 0) for p in pages),
                "total_chunks": len(chunks),
            },
            "ingestion_summary": ingestion_summary,
            "batch_processing_stats": knowledge.get("batch_processing_stats", {}),
            "chunks": chunks,
            "knowledge": knowledge,
            "evaluation": evaluation,
        }

        # Persist (failures are logged but don't break the response)
        _persist_result(doc_id, result, chunks, evaluation, active_model, safe_filename, len(contents), len(pages))

        return _strip_api_key(result)

    except Exception as exc:
        log.error(f"Pipeline error for {doc_id}: {exc}", extra={"stage": "process"})
        return api_error(
            "PIPELINE_ERROR",
            "An error occurred during document processing.",
            detail=str(exc),
            status=500,
        )


@app.post("/api/rag")
async def run_rag(req: RAGRequest):
    """
    Executes keyword retrieval and Sarvam AI grounded generation.
    Preserved backward-compatible response shape.
    """
    if not req.chunks:
        return api_error("NO_CHUNKS", "No chunks available for retrieval.", status=400)

    top_chunks = pipeline.search_chunks(
        req.query,
        req.chunks,
        top_k=settings.default_top_k,
    )

    active_key = req.api_key or settings.sarvam_api_key
    active_model = settings.resolve_model(req.model or settings.sarvam_model)
    rag_result = pipeline.answer_rag_query(
        req.query,
        top_chunks,
        api_key=active_key,
        model=active_model,
    )

    return _strip_api_key({
        "query": req.query,
        "retrieved_chunks": top_chunks,
        "answer": rag_result["answer"],
        "citations": rag_result["citations"],
    })


# ---------------------------------------------------------------------------
# New endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """
    Deep health check: Sarvam API reachability, storage status, system info.
    Always returns HTTP 200 — individual check results are in 'checks'.
    """
    import platform
    uptime_seconds = round(time.monotonic() - _server_start_time)

    # Storage check
    storage_status = "ok"
    try:
        _storage.list_documents()
    except Exception as exc:
        storage_status = f"error: {exc}"

    # Sarvam API reachability (lightweight: check if key is configured)
    sarvam_status = "not_configured"
    if settings.has_api_key():
        try:
            import requests as req_lib
            resp = req_lib.head(
                settings.sarvam_api_url.replace("/chat/completions", ""),
                timeout=5,
            )
            sarvam_status = "reachable"
        except Exception:
            sarvam_status = "unreachable"

    # Disk space
    disk_free_mb = 0
    try:
        disk_usage = shutil.disk_usage(settings.storage_dir)
        disk_free_mb = round(disk_usage.free / (1024 * 1024))
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "2.0.0",
        "uptime_seconds": uptime_seconds,
        "checks": {
            "sarvam_api": sarvam_status,
            "storage": storage_status,
            "disk_free_mb": disk_free_mb,
            "python_version": sys.version.split()[0],
        },
    }


@app.post("/api/chunk-preview")
async def chunk_preview(req: ChunkPreviewRequest):
    """
    Returns boundary-aware chunks for arbitrary text without any LLM call.
    Useful for previewing chunking parameters before running the full pipeline.
    """
    if len(req.text) > 50_000:
        return api_error(
            "TEXT_TOO_LONG",
            "Text exceeds the 50,000 character limit for chunk preview.",
            detail=f"Received {len(req.text)} chars.",
            status=400,
        )

    pages = [{"page": 1, "text": req.text, "char_count": len(req.text), "word_count": len(req.text.split()), "status": "ok", "error_detail": None}]
    chunks = pipeline.create_chunks(
        pages,
        target_chunk_size=req.chunk_size,
        overlap=req.overlap,
    )
    return {"chunks": chunks, "total_chunks": len(chunks)}


@app.post("/api/export/{fmt}")
async def export_data(fmt: str, request: Request):
    """
    Server-side export of pipeline result data.
    Accepts the full pipeline response JSON in the request body.
    Supported formats: jsonl, json, csv, md.
    """
    SUPPORTED_FORMATS = {"jsonl", "json", "csv", "md"}
    if fmt not in SUPPORTED_FORMATS:
        return api_error(
            "UNSUPPORTED_FORMAT",
            f"Format '{fmt}' is not supported.",
            detail=f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}",
            status=400,
        )

    try:
        data = await request.json()
    except Exception:
        return api_error("INVALID_JSON", "Request body is not valid JSON.", status=400)

    FORMAT_CONFIG = {
        "jsonl": (to_jsonl, "application/x-jsonlines", ".jsonl"),
        "json":  (to_json,  "application/json",         ".json"),
        "csv":   (to_csv,   "text/csv",                 ".csv"),
        "md":    (to_markdown, "text/markdown",         ".md"),
    }

    export_fn, mime_type, extension = FORMAT_CONFIG[fmt]
    content = export_fn(data)
    doc_name = data.get("document_name", "knowledge_export").replace(" ", "_")
    filename = f"{doc_name.rsplit('.', 1)[0]}{extension}"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/documents")
async def list_documents():
    """Lists all stored documents with metadata, sorted by most recent first."""
    try:
        docs = _storage.list_documents()
        return {"documents": docs, "total": len(docs)}
    except Exception as exc:
        return api_error("STORAGE_ERROR", "Failed to retrieve documents.", detail=str(exc), status=500)


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str):
    """Returns the full stored pipeline result for a document."""
    try:
        result = _storage.load_result(doc_id)
        if result is None:
            return api_error("NOT_FOUND", f"Document '{doc_id}' not found.", status=404)
        return result
    except Exception as exc:
        return api_error("STORAGE_ERROR", "Failed to load document.", detail=str(exc), status=500)


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Removes all stored data for a document."""
    try:
        deleted = _storage.delete_document(doc_id)
        if not deleted:
            return api_error("NOT_FOUND", f"Document '{doc_id}' not found.", status=404)
        return {"deleted": True, "doc_id": doc_id}
    except Exception as exc:
        return api_error("STORAGE_ERROR", "Failed to delete document.", detail=str(exc), status=500)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _persist_result(
    doc_id: str,
    result: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    evaluation: Dict[str, Any],
    model_used: str,
    filename: str = "sample",
    size_bytes: int = 0,
    page_count: int = 1,
) -> None:
    """
    Persists the pipeline result to storage.
    Failures are logged but never propagate to the HTTP response.
    """
    try:
        _storage.save_document(doc_id, {
            "filename": result.get("document_name", filename),
            "size_bytes": size_bytes,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "page_count": page_count or result.get("stats", {}).get("total_pages", 1),
            "chunk_count": len(chunks),
            "status": "processed",
            "model_used": model_used,
        })
        _storage.save_result(doc_id, result)
        _storage.save_chunks(doc_id, chunks)
        _storage.save_evaluation(doc_id, evaluation)
    except Exception as exc:
        log.error(
            f"Storage persistence failed for {doc_id}: {exc}",
            extra={"stage": "storage", "doc_id": doc_id},
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("Starting AI Knowledge Engineering Platform on http://127.0.0.1:8000")
    print("=" * 60 + "\n")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
