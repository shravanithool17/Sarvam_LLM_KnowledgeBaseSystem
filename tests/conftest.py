"""
conftest.py — Shared pytest fixtures for the AI Knowledge Engineering Platform test suite.

Key fixtures:
  - mock_sarvam_response: patches requests.post so no live Sarvam API calls are made.
  - sample_chunks: a realistic list of chunk dicts matching the pipeline schema.
  - sample_pipeline_data: a full pipeline response dict for export/storage tests.
  - tmp_storage_dir: a temporary directory for storage tests (auto-cleaned).

Policy: NO test in this suite makes a live Sarvam API call.
"""

import json
import io
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Canned Sarvam API response (valid knowledge JSON)
# ---------------------------------------------------------------------------
_CANNED_KNOWLEDGE = {
    "summary": (
        "This document describes a knowledge engineering pipeline that transforms "
        "unstructured documents into structured AI-ready datasets. It covers "
        "boundary-aware chunking, hierarchical synthesis, and quality evaluation."
    ),
    "facts": [
        {
            "entity": "Knowledge Pipeline",
            "category": "Architecture",
            "fact": "Transforms unstructured PDFs into structured, high-grade AI datasets.",
            "citation": "CHK-001",
        },
        {
            "entity": "Boundary-Aware Chunking",
            "category": "Process",
            "fact": "Respects paragraph and sentence boundaries to prevent fragmentation.",
            "citation": "CHK-002",
        },
        {
            "entity": "Sarvam AI",
            "category": "Model",
            "fact": "Powers multilingual synthesis and instruction-tuning dataset generation.",
            "citation": "CHK-003",
        },
    ],
    "qa_dataset": [
        {
            "id": "QA-001",
            "instruction": "What is the primary objective of the knowledge pipeline?",
            "response": (
                "The pipeline automates the end-to-end transformation of unstructured "
                "documents into validated, deployment-ready knowledge representations."
            ),
            "citation": "CHK-001",
            "confidence": "High",
        },
        {
            "id": "QA-002",
            "instruction": "How does the pipeline ensure traceability?",
            "response": (
                "Every extracted fact and synthetic instruction-answer pair is mapped "
                "directly to its origin chunk ID and page number."
            ),
            "citation": "CHK-002",
            "confidence": "High",
        },
        {
            "id": "QA-003",
            "instruction": "What similarity metric is used for deduplication?",
            "response": (
                "The pipeline uses Jaccard similarity to detect redundant chunk pairs, "
                "flagging those with similarity exceeding the configured threshold."
            ),
            "citation": "CHK-003",
            "confidence": "High",
        },
    ],
}


def _make_mock_response(knowledge_dict: dict | None = None) -> MagicMock:
    """Build a mock requests.Response that mimics a successful Sarvam API call."""
    payload = knowledge_dict or _CANNED_KNOWLEDGE
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "id": "chatcmpl-test-000",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "sarvam-105b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(payload),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 200, "completion_tokens": 300, "total_tokens": 500},
    }
    return mock_resp


@pytest.fixture
def mock_sarvam_response():
    """
    Patches requests.post globally so no live Sarvam API call is made.
    Returns the mock object so tests can inspect call arguments.
    """
    mock_resp = _make_mock_response()
    with patch("requests.post", return_value=mock_resp) as mock_post:
        yield mock_post


@pytest.fixture
def mock_sarvam_response_factory():
    """
    Like mock_sarvam_response but allows the test to provide custom knowledge JSON.
    Usage: mock = mock_sarvam_response_factory(custom_dict)
    """
    def _factory(knowledge_dict: dict):
        mock_resp = _make_mock_response(knowledge_dict)
        return patch("requests.post", return_value=mock_resp)
    return _factory


# ---------------------------------------------------------------------------
# Reusable chunk + pipeline data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chunks():
    """A realistic list of chunk dicts matching the pipeline chunk schema."""
    return [
        {
            "id": "CHK-001",
            "page": 1,
            "text": (
                "Knowledge engineering is the discipline of building systems that "
                "encode, organise, and retrieve structured information from documents. "
                "It bridges the gap between raw unstructured data and machine-interpretable "
                "representations suitable for AI applications and pipelines."
            ),
            "char_count": 280,
            "approx_tokens": 56,
            "word_count": 45,
        },
        {
            "id": "CHK-002",
            "page": 1,
            "text": (
                "Modern knowledge pipelines begin with document ingestion. "
                "A document may arrive in PDF, plain text, or DOCX format. "
                "The ingestion stage extracts raw text page by page, preserving "
                "structural boundaries such as paragraphs and sections."
            ),
            "char_count": 250,
            "approx_tokens": 50,
            "word_count": 42,
        },
        {
            "id": "CHK-003",
            "page": 2,
            "text": (
                "Boundary-aware chunking respects sentence and paragraph delimiters "
                "to avoid severing ideas mid-sentence. Each chunk receives a unique "
                "identifier and carries a reference to its source page number."
            ),
            "char_count": 220,
            "approx_tokens": 44,
            "word_count": 36,
        },
        {
            "id": "CHK-004",
            "page": 2,
            "text": (
                "After chunking, an AI model analyses each batch of chunks and produces "
                "a structured knowledge representation including an executive summary, "
                "a catalogue of key facts and entities, and instruction-response pairs."
            ),
            "char_count": 240,
            "approx_tokens": 48,
            "word_count": 38,
        },
        {
            "id": "CHK-005",
            "page": 3,
            "text": (
                "Quality evaluation uses Jaccard similarity to measure redundancy between "
                "chunk pairs. Grounding verification checks that the keywords of each "
                "generated answer appear in the cited source chunk text."
            ),
            "char_count": 230,
            "approx_tokens": 46,
            "word_count": 37,
        },
    ]


@pytest.fixture
def sample_qa_dataset():
    """A small QA dataset matching the pipeline schema."""
    return _CANNED_KNOWLEDGE["qa_dataset"]


@pytest.fixture
def sample_pipeline_data(sample_chunks, sample_qa_dataset):
    """
    A complete pipeline response dict suitable for export/storage tests.
    Matches the shape returned by /api/process.
    """
    return {
        "document_name": "sample.txt",
        "document_id": "test-doc-uuid-0001",
        "mode": "simulated",
        "stats": {
            "total_pages": 3,
            "total_chars": 1200,
            "total_chunks": len(sample_chunks),
        },
        "ingestion_summary": {
            "pages_processed": 3,
            "pages_skipped": 0,
            "pages_failed": 0,
            "encoding_warnings": [],
        },
        "chunks": sample_chunks,
        "knowledge": {
            "summary": _CANNED_KNOWLEDGE["summary"],
            "facts": _CANNED_KNOWLEDGE["facts"],
            "qa_dataset": sample_qa_dataset,
            "mode": "simulated",
        },
        "evaluation": {
            "overall_health_score": 82,
            "grounding_score": 90.0,
            "redundancy_rate": 0.0,
            "duplicate_pairs": [],
            "total_chunks_evaluated": len(sample_chunks),
            "total_qa_evaluated": len(sample_qa_dataset),
            "per_qa_grounding": [
                {"id": qa["id"], "grounded": True, "citation_valid": True}
                for qa in sample_qa_dataset
            ],
            "quality_flags": [],
        },
        "batch_processing_stats": {
            "total_batches": 2,
            "processed": 2,
            "skipped": 0,
            "failed": 0,
        },
    }


# ---------------------------------------------------------------------------
# Temporary storage directory
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_storage_dir(tmp_path) -> Path:
    """A temporary directory for SQLite storage tests. Auto-deleted after each test."""
    storage = tmp_path / "test_storage"
    storage.mkdir()
    return storage


# ---------------------------------------------------------------------------
# File fixture helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_txt_bytes() -> bytes:
    """Raw bytes of the sample.txt fixture."""
    return (FIXTURES_DIR / "sample.txt").read_bytes()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Raw bytes of the sample.pdf fixture."""
    return (FIXTURES_DIR / "sample.pdf").read_bytes()


@pytest.fixture
def sample_pdf_stream(sample_pdf_bytes) -> io.BytesIO:
    """BytesIO stream of the sample.pdf fixture."""
    return io.BytesIO(sample_pdf_bytes)
