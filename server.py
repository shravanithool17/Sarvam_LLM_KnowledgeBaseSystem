import os
import io
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import pipeline

# Load environment variables
load_dotenv()

app = FastAPI(title="LLM Knowledge Pipeline", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Sample Document for 1-Click Instant Testing
SAMPLE_DOCUMENT = """
HIGH-PERFORMANCE LLM KNOWLEDGE PIPELINE SPECIFICATION
Author: Advanced Knowledge Engineering Group
Domain: Retrieval-Augmented Generation (RAG) & Fine-Tuning Dataset Creation

1. Executive Summary
Modern enterprise AI initiatives fail when fed unstructured, noisy documents. Typical PDF chatbots suffer from severe hallucination rates exceeding 35% because they rely on naïve fixed-length character splitting without semantic boundary awareness. The LLM Knowledge Pipeline is an end-to-end framework that converts unstructured PDF, DOCX, and markdown files into structured, hallucination-resistant knowledge representations.

2. Semantic Chunking Strategy
Traditional splitting causes contextual fragmentation by severing sentences across arbitrary chunk limits. The pipeline implements boundary-aware chunking. Each chunk respects semantic clause breaks, paragraph terminations, and header boundaries. Furthermore, chunks are strictly tagged with immutable source metadata: Page Number, Character Position, Token Approximation, and a unique Chunk ID (e.g., CHK-001).

3. Multilingual Knowledge Synthesis via Sarvam AI
The platform utilizes Sarvam AI's specialized language models (such as Sarvam-105B and Sarvam-2B) to execute knowledge distillation. Rather than merely summarizing, the model constructs three distinct knowledge tiers:
A. Executive Knowledge Synthesis: High-density condensation of core findings.
B. Structured Entity & Fact Matrix: Key concepts, parameters, metrics, and definitions mapped to their parent chunks.
C. Synthetic Instruction-Tuning Pairs: High-quality instruction-response pairs formatted for direct consumption by fine-tuning frameworks like Alpaca, Unsloth, or Llama-Factory.

4. Traceability & Grounding Verification
Every generated Q&A pair and extracted fact must have an exact citation reference. A synthetic answer is considered ungrounded if its key semantic tokens cannot be verified within the referenced source chunk. The pipeline enforces a Grounding Verification threshold (>85%) before accepting knowledge into the final dataset.

5. Deduplication and Redundancy Benchmarking
Unstructured corpuses frequently contain duplicated sections, boilerplate headers, and repetitive clauses. The pipeline computes pair-wise similarity using Jaccard and Cosine metrics. Chunk pairs with similarity exceeding 45% are flagged as redundant, ensuring downstream vector databases do not waste storage or pollute search indices with duplicative vectors.

6. Downstream Export & Deployment
The validated knowledge base is exported into three standardized formats:
- JSONL: Standard Alpaca prompt-completion schema for instruction fine-tuning.
- Complete Knowledge JSON: Hierarchical graph containing chunks, facts, citations, and evaluation metrics for vector DB ingestion.
- Tabular CSV: For human review, data labeling audits, and compliance inspection.
"""


class RAGRequest(BaseModel):
    query: str
    chunks: List[Dict[str, Any]]
    api_key: Optional[str] = None
    model: Optional[str] = "sarvam-105b"


class SampleRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = "sarvam-105b"


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the modern dark-mode frontend."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend template not found.")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/status")
async def get_status():
    """Returns whether the Sarvam API key is configured."""
    key = os.getenv("SARVAM_API_KEY", "").strip()
    has_key = bool(key and key != "your_sarvam_api_key_here")
    default_model = os.getenv("SARVAM_MODEL", "sarvam-105b")
    return {
        "status": "online",
        "has_key": has_key,
        "default_model": default_model
    }


@app.post("/api/sample")
async def process_sample(req: SampleRequest):
    """Processes the rich pre-packaged technical document."""
    pages = [{"page": 1, "text": SAMPLE_DOCUMENT, "char_count": len(SAMPLE_DOCUMENT)}]
    chunks = pipeline.create_chunks(pages, target_chunk_size=450, overlap=60)
    
    api_key = req.api_key or os.getenv("SARVAM_API_KEY", "")
    knowledge = pipeline.synthesize_knowledge(chunks, api_key=api_key, model=req.model or "sarvam-105b")
    evaluation = pipeline.evaluate_dataset_quality(chunks, knowledge.get("qa_dataset", []))

    return {
        "document_name": "High-Performance_LLM_Knowledge_Pipeline_Spec.txt",
        "stats": {
            "total_pages": 1,
            "total_chars": len(SAMPLE_DOCUMENT),
            "total_chunks": len(chunks)
        },
        "chunks": chunks,
        "knowledge": knowledge,
        "evaluation": evaluation
    }


@app.post("/api/process")
async def process_document(
    file: UploadFile = File(...),
    model: str = Form("sarvam-105b"),
    api_key: Optional[str] = Form(None)
):
    """Handles PDF or TXT upload, parses, chunks, synthesizes via Sarvam, and evaluates."""
    contents = await file.read()
    filename = file.filename or "uploaded_document"
    
    # 1. Parse text based on format
    if filename.lower().endswith(".pdf"):
        pages = pipeline.extract_text_from_pdf(io.BytesIO(contents))
    else:
        pages = pipeline.extract_text_from_txt(contents)

    if not pages:
        raise HTTPException(status_code=400, detail="Could not extract readable text from the document.")

    # 2. Semantic Chunking
    chunks = pipeline.create_chunks(pages, target_chunk_size=550, overlap=80)

    # 3. Knowledge Synthesis via Sarvam
    active_key = api_key or os.getenv("SARVAM_API_KEY", "")
    knowledge = pipeline.synthesize_knowledge(chunks, api_key=active_key, model=model)

    # 4. Quality & Deduplication Benchmark
    evaluation = pipeline.evaluate_dataset_quality(chunks, knowledge.get("qa_dataset", []))

    return {
        "document_name": filename,
        "stats": {
            "total_pages": len(pages),
            "total_chars": sum(p["char_count"] for p in pages),
            "total_chunks": len(chunks)
        },
        "chunks": chunks,
        "knowledge": knowledge,
        "evaluation": evaluation
    }


@app.post("/api/rag")
async def run_rag(req: RAGRequest):
    """Executes vector retrieval and Sarvam LLM grounded generation."""
    if not req.chunks:
        raise HTTPException(status_code=400, detail="No chunks available for retrieval.")

    # 1. Retrieve top-k relevant chunks
    top_chunks = pipeline.search_chunks(req.query, req.chunks, top_k=2)

    # 2. Generate grounded answer
    active_key = req.api_key or os.getenv("SARVAM_API_KEY", "")
    rag_result = pipeline.answer_rag_query(req.query, top_chunks, api_key=active_key, model=req.model or "sarvam-105b")

    return {
        "query": req.query,
        "retrieved_chunks": top_chunks,
        "answer": rag_result["answer"],
        "citations": rag_result["citations"]
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 Starting LLM Knowledge Pipeline Server on http://127.0.0.1:8000")
    print("=" * 60 + "\n")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

