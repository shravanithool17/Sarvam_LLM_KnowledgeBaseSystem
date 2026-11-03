"""
pipeline.py — Backward-compatible facade for the AI Knowledge Engineering Platform.

This module preserves the original public interface so that all existing callers
(server.py, tests, external code) continue to work without modification.

All logic now lives in dedicated sub-modules:
  - ingest.py   : document extraction and validation
  - chunking.py : boundary-aware chunking (not "semantic chunking")
  - knowledge.py: hierarchical map-reduce synthesis via Sarvam AI
  - quality.py  : deduplication and grounding evaluation
  - rag.py      : retrieval and grounded answer generation
  - export.py   : multi-format export

Re-exports below mirror the original pipeline.py function signatures exactly.
"""

# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------
from ingest import (
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_text_from_docx,
    validate_upload,
    cleanup_temp_file,
    build_ingestion_summary,
)

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
from chunking import create_chunks

# ---------------------------------------------------------------------------
# Knowledge synthesis
# ---------------------------------------------------------------------------
from knowledge import (
    call_sarvam_chat,
    synthesize_knowledge,
    get_simulated_knowledge,
)

# ---------------------------------------------------------------------------
# Quality & deduplication
# ---------------------------------------------------------------------------
from quality import (
    compute_jaccard_similarity,
    evaluate_dataset_quality,
    compute_tfidf_cosine,
)

# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------
from rag import search_chunks, answer_rag_query

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
from export import to_jsonl, to_json, to_csv, to_markdown


# ---------------------------------------------------------------------------
# __all__ — explicitly declares the public API
# ---------------------------------------------------------------------------
__all__ = [
    # Ingest
    "extract_text_from_pdf",
    "extract_text_from_txt",
    "extract_text_from_docx",
    "validate_upload",
    "cleanup_temp_file",
    "build_ingestion_summary",
    # Chunking
    "create_chunks",
    # Knowledge
    "call_sarvam_chat",
    "synthesize_knowledge",
    "get_simulated_knowledge",
    # Quality
    "compute_jaccard_similarity",
    "evaluate_dataset_quality",
    "compute_tfidf_cosine",
    # RAG
    "search_chunks",
    "answer_rag_query",
    # Export
    "to_jsonl",
    "to_json",
    "to_csv",
    "to_markdown",
]
