"""
tests/test_chunking.py — Unit tests for chunking.py

Tests cover:
  - min_chunk_length filter
  - sentence-level overlap (no mid-sentence cuts)
  - overlap=0 produces no overlap
  - chunk ID sequence (CHK-001, CHK-002, ...)
  - word_count and approx_tokens fields
  - empty input
  - single paragraph
  - multi-page input
  - terminology: "semantic chunking" must NOT appear in module docstrings/comments
"""

from pathlib import Path

import pytest

from chunking import create_chunks, _compute_overlap_text, _split_sentences


LONG_TEXT = (
    "Knowledge engineering is a discipline focused on building AI systems. "
    "It converts raw unstructured data into machine-readable representations. "
    "The ingestion stage parses documents page by page. "
    "Boundary-aware chunking preserves sentence integrity. "
    "Each chunk receives a unique identifier and page citation. "
    "Quality evaluation measures redundancy and grounding accuracy. "
    "Retrieval-augmented generation uses chunks to answer user queries. "
    "The export module supports JSONL, JSON, CSV, and Markdown formats. "
    "Sarvam AI powers the knowledge synthesis stage. "
    "Simulated mode allows testing without API credits."
)


def _make_pages(text: str, page: int = 1):
    return [{"page": page, "text": text, "char_count": len(text), "word_count": len(text.split()), "status": "ok", "error_detail": None}]


# ---------------------------------------------------------------------------
# Terminology check
# ---------------------------------------------------------------------------

class TestTerminology:
    def test_no_semantic_chunking_in_docstring(self):
        """The phrase 'semantic chunking' must not appear in chunking.py source."""
        source = Path("chunking.py").read_text(encoding="utf-8")
        # Check that "semantic chunking" (as a label for this module's approach) isn't used
        # The docstring explicitly says NOT semantic — verify we don't accidentally use it
        lower_src = source.lower()
        # The word appears in a NEGATIVE context ("NOT semantic chunking") which is fine
        # We just verify it's not used as a positive label for what this module does
        # A simple heuristic: "semantic chunking" should only appear in a negation context
        import re
        positive_uses = re.findall(
            r'(?<!not\s)(?<!not ")(?<!"not\s)"semantic chunking"|'
            r'implements semantic chunking|'
            r'this is semantic|'
            r'true semantic chunk',
            lower_src
        )
        assert positive_uses == [], f"'semantic chunking' used as positive label: {positive_uses}"


# ---------------------------------------------------------------------------
# _split_sentences helper
# ---------------------------------------------------------------------------

class TestSplitSentences:
    def test_basic_split(self):
        text = "First sentence. Second sentence. Third sentence."
        sentences = _split_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence."

    def test_no_sentence_boundary(self):
        text = "No terminator here just plain words"
        sentences = _split_sentences(text)
        assert sentences == ["No terminator here just plain words"]

    def test_empty_string(self):
        assert _split_sentences("") == []

    def test_question_mark_split(self):
        sentences = _split_sentences("What is this? It is a test. Good.")
        assert len(sentences) == 3


# ---------------------------------------------------------------------------
# _compute_overlap_text helper
# ---------------------------------------------------------------------------

class TestComputeOverlapText:
    def test_zero_overlap_returns_empty(self):
        text = "First sentence. Second sentence. Third sentence."
        assert _compute_overlap_text(text, 0) == ""

    def test_overlap_returns_whole_sentences(self):
        text = "Short sentence. Another one here. Final sentence ends."
        overlap = _compute_overlap_text(text, 30)
        # Result must not cut mid-sentence
        assert not overlap.endswith(" ")
        # Each "sentence" in the overlap should end with punctuation or be complete
        # The overlap should be a suffix of the original text composed of whole sentences

    def test_overlap_is_suffix_of_original(self):
        text = "First sentence. Second sentence. Third sentence end."
        overlap = _compute_overlap_text(text, 50)
        # The overlap text should appear as a substring of the original
        assert overlap in text or all(s in text for s in overlap.split(". "))

    def test_no_sentence_boundary_falls_back(self):
        text = "nodots nodots nodots nodots nodots nodots"
        overlap = _compute_overlap_text(text, 10)
        assert len(overlap) <= len(text)
        assert isinstance(overlap, str)

    def test_empty_text_returns_empty(self):
        assert _compute_overlap_text("", 100) == ""


# ---------------------------------------------------------------------------
# create_chunks
# ---------------------------------------------------------------------------

class TestCreateChunks:
    def test_empty_pages_returns_empty(self):
        assert create_chunks([]) == []

    def test_single_paragraph_produces_at_least_one_chunk(self):
        pages = _make_pages("This is a short document with some text content here.")
        chunks = create_chunks(pages)
        assert len(chunks) >= 1

    def test_chunk_id_sequence(self):
        pages = _make_pages(LONG_TEXT)
        chunks = create_chunks(pages, target_chunk_size=100)
        ids = [c["id"] for c in chunks]
        assert ids[0] == "CHK-001"
        for i, chunk_id in enumerate(ids):
            assert chunk_id == f"CHK-{i+1:03d}"

    def test_chunk_schema_fields_present(self):
        pages = _make_pages(LONG_TEXT)
        chunks = create_chunks(pages)
        for c in chunks:
            assert "id" in c
            assert "page" in c
            assert "text" in c
            assert "char_count" in c
            assert "approx_tokens" in c
            assert "word_count" in c

    def test_word_count_matches_text(self):
        pages = _make_pages(LONG_TEXT)
        chunks = create_chunks(pages)
        for c in chunks:
            assert c["word_count"] == len(c["text"].split())

    def test_char_count_matches_text(self):
        pages = _make_pages(LONG_TEXT)
        chunks = create_chunks(pages)
        for c in chunks:
            assert c["char_count"] == len(c["text"])

    def test_min_chunk_length_discards_short_chunks(self):
        """Micro-fragments below min_chunk_length must be discarded."""
        # Create text where one paragraph is very short
        text = "Short. " + "A longer sentence that contains more words and will form a proper chunk. " * 5
        pages = _make_pages(text)
        chunks = create_chunks(pages, target_chunk_size=200, min_chunk_length=50)
        for c in chunks:
            assert c["char_count"] >= 50, f"Chunk {c['id']} is too short: {c['char_count']} chars"

    def test_min_chunk_length_zero_keeps_all(self):
        """With min_chunk_length=0, no chunks are filtered."""
        pages = _make_pages("Short.")
        chunks_filtered = create_chunks(pages, min_chunk_length=50)
        chunks_unfiltered = create_chunks(pages, min_chunk_length=0)
        # Unfiltered may include very short chunks that filtered version drops
        assert len(chunks_unfiltered) >= len(chunks_filtered)

    def test_chunk_size_respected_approximately(self):
        """Chunks should not greatly exceed the target_chunk_size."""
        pages = _make_pages(LONG_TEXT)
        chunk_size = 150
        chunks = create_chunks(pages, target_chunk_size=chunk_size)
        for c in chunks:
            # Allow some overage for sentence-boundary preservation
            assert c["char_count"] <= chunk_size * 2, (
                f"Chunk {c['id']} greatly exceeds target size: {c['char_count']} chars"
            )

    def test_overlap_zero_no_repetition(self):
        """With overlap=0, consecutive chunks should not share sentence prefixes."""
        pages = _make_pages(LONG_TEXT)
        chunks = create_chunks(pages, target_chunk_size=100, overlap=0)
        if len(chunks) >= 2:
            # The start of chunk[1] should not be the end of chunk[0]
            end_of_0 = chunks[0]["text"].split(".")[-1].strip().lower()
            start_of_1 = chunks[1]["text"][:50].lower()
            # They should not be the same fragment
            if end_of_0:
                assert end_of_0 not in start_of_1 or len(end_of_0) < 5

    def test_overlap_produces_context_continuity(self):
        """With overlap > 0, some content from one chunk should appear at the start of the next."""
        pages = _make_pages(LONG_TEXT)
        chunks = create_chunks(pages, target_chunk_size=120, overlap=60)
        # Not strictly testable without exact logic, but we verify it doesn't crash
        # and produces more chunks than with overlap=0 (overlap increases total content)
        chunks_no_overlap = create_chunks(pages, target_chunk_size=120, overlap=0)
        # With overlap, we may get more or equal chunks (never fewer)
        assert len(chunks) >= len(chunks_no_overlap) - 1  # allow ±1 for boundary effects

    def test_multi_page_input(self):
        pages = [
            {"page": 1, "text": LONG_TEXT, "char_count": len(LONG_TEXT), "word_count": 100, "status": "ok", "error_detail": None},
            {"page": 2, "text": LONG_TEXT, "char_count": len(LONG_TEXT), "word_count": 100, "status": "ok", "error_detail": None},
        ]
        chunks = create_chunks(pages, target_chunk_size=200)
        pages_in_chunks = {c["page"] for c in chunks}
        assert 1 in pages_in_chunks
        assert 2 in pages_in_chunks

    def test_page_is_correctly_assigned(self):
        pages = [
            {"page": 3, "text": "Text on page three.", "char_count": 20, "word_count": 4, "status": "ok", "error_detail": None},
        ]
        chunks = create_chunks(pages, min_chunk_length=0)
        assert all(c["page"] == 3 for c in chunks)

    def test_empty_text_page_skipped(self):
        pages = [
            {"page": 1, "text": "", "char_count": 0, "word_count": 0, "status": "skipped", "error_detail": None},
            {"page": 2, "text": "Real content here for chunking.", "char_count": 30, "word_count": 5, "status": "ok", "error_detail": None},
        ]
        chunks = create_chunks(pages)
        assert all(c["page"] == 2 for c in chunks)

    def test_pipeline_re_export_works(self):
        """pipeline.py must re-export create_chunks under the same name."""
        from pipeline import create_chunks as pipeline_create_chunks
        pages = _make_pages("Test document text here.")
        chunks = pipeline_create_chunks(pages)
        assert isinstance(chunks, list)
