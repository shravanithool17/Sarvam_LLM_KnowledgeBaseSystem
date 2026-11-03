"""
tests/test_quality.py — Unit tests for quality.py
"""

import pytest

from quality import (
    compute_jaccard_similarity,
    compute_tfidf_cosine,
    evaluate_dataset_quality,
)


class TestJaccard:
    def test_identical_strings(self):
        assert compute_jaccard_similarity("hello world", "hello world") == 1.0

    def test_completely_disjoint(self):
        assert compute_jaccard_similarity("apple pie", "ocean current") == 0.0

    def test_partial_overlap(self):
        score = compute_jaccard_similarity("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0

    def test_empty_strings(self):
        assert compute_jaccard_similarity("", "") == 0.0

    def test_one_empty(self):
        assert compute_jaccard_similarity("hello", "") == 0.0

    def test_case_insensitive(self):
        score = compute_jaccard_similarity("Hello World", "hello world")
        assert score == 1.0


class TestTFIDFCosine:
    def test_identical_strings(self):
        score = compute_tfidf_cosine("hello world test", "hello world test")
        assert abs(score - 1.0) < 0.001

    def test_disjoint_strings(self):
        score = compute_tfidf_cosine("apple pie baking", "ocean current waves")
        assert score < 0.1

    def test_partial_overlap(self):
        score = compute_tfidf_cosine("knowledge pipeline AI", "knowledge system AI")
        assert 0.0 < score < 1.0

    def test_empty_strings(self):
        assert compute_tfidf_cosine("", "") == 0.0

    def test_one_empty(self):
        assert compute_tfidf_cosine("hello world", "") == 0.0

    def test_returns_float_in_range(self):
        score = compute_tfidf_cosine("any text here", "other text there")
        assert 0.0 <= score <= 1.0


class TestEvaluateDatasetQuality:
    def _make_chunks(self, texts):
        return [
            {"id": f"CHK-{i+1:03d}", "text": t, "char_count": len(t), "approx_tokens": 10, "word_count": len(t.split()), "page": 1}
            for i, t in enumerate(texts)
        ]

    def _make_qa(self, chunk_id, response_text):
        return {
            "id": "QA-001",
            "instruction": "What is this?",
            "response": response_text,
            "citation": chunk_id,
            "confidence": "High",
        }

    def test_no_duplicates_clean_dataset(self):
        chunks = self._make_chunks([
            "Knowledge engineering builds AI systems from unstructured data.",
            "Retrieval augmented generation answers user queries from documents.",
        ])
        result = evaluate_dataset_quality(chunks, [])
        assert result["redundancy_rate"] == 0.0
        assert result["duplicate_pairs"] == []

    def test_duplicate_chunks_detected(self):
        identical = "This exact same sentence appears twice in the chunk corpus."
        chunks = self._make_chunks([identical, identical])
        result = evaluate_dataset_quality(chunks, [], threshold=0.45)
        assert len(result["duplicate_pairs"]) >= 1
        assert result["redundancy_rate"] > 0

    def test_configurable_threshold(self):
        """Lower threshold catches more pairs; higher threshold catches fewer."""
        chunks = self._make_chunks([
            "knowledge pipeline system AI",
            "knowledge pipeline system ML",
        ])
        low_thresh = evaluate_dataset_quality(chunks, [], threshold=0.1)
        high_thresh = evaluate_dataset_quality(chunks, [], threshold=0.9)
        assert len(low_thresh["duplicate_pairs"]) >= len(high_thresh["duplicate_pairs"])

    def test_grounding_valid_citation(self):
        chunks = self._make_chunks([
            "The knowledge pipeline transforms unstructured documents into structured datasets."
        ])
        qa = [self._make_qa("CHK-001", "The pipeline transforms documents into structured datasets.")]
        result = evaluate_dataset_quality(chunks, qa)
        assert result["grounding_score"] > 0
        assert result["per_qa_grounding"][0]["grounded"] is True
        assert result["per_qa_grounding"][0]["citation_valid"] is True

    def test_grounding_invalid_citation(self):
        chunks = self._make_chunks(["Some text about something."])
        qa = [self._make_qa("CHK-999", "Answer using wrong citation.")]
        result = evaluate_dataset_quality(chunks, qa)
        assert result["per_qa_grounding"][0]["citation_valid"] is False
        assert result["per_qa_grounding"][0]["grounded"] is False

    def test_per_qa_grounding_present(self):
        chunks = self._make_chunks(["Test document text content here."])
        qa = [self._make_qa("CHK-001", "Test document text content.")]
        result = evaluate_dataset_quality(chunks, qa)
        assert "per_qa_grounding" in result
        assert len(result["per_qa_grounding"]) == 1
        pqg = result["per_qa_grounding"][0]
        assert "id" in pqg
        assert "grounded" in pqg
        assert "citation_valid" in pqg

    def test_quality_flags_low_grounding(self):
        chunks = self._make_chunks(["Completely unrelated text about rocks and minerals."])
        qa = [self._make_qa("CHK-999", "Something about entirely different topics entirely.")]
        result = evaluate_dataset_quality(chunks, qa)
        # Invalid citation → ungrounded → low grounding flag
        assert "low_grounding" in result["quality_flags"] or result["grounding_score"] <= 50

    def test_quality_flags_no_qa_pairs(self):
        chunks = self._make_chunks(["Some text."])
        result = evaluate_dataset_quality(chunks, [])
        assert "no_qa_pairs" in result["quality_flags"]

    def test_quality_flags_failed_batches(self):
        chunks = self._make_chunks(["Some text."])
        batch_stats = {"total_batches": 3, "processed": 2, "skipped": 0, "failed": 1}
        result = evaluate_dataset_quality(chunks, [], batch_processing_stats=batch_stats)
        assert "failed_batches" in result["quality_flags"]

    def test_backward_compatible_fields(self):
        """All original fields must be present."""
        chunks = self._make_chunks(["Text content here."])
        result = evaluate_dataset_quality(chunks, [])
        required = [
            "overall_health_score", "grounding_score", "redundancy_rate",
            "duplicate_pairs", "total_chunks_evaluated", "total_qa_evaluated"
        ]
        for field in required:
            assert field in result, f"Missing backward-compatible field: {field}"

    def test_overall_health_in_range(self):
        chunks = self._make_chunks(["Some document text content here."])
        result = evaluate_dataset_quality(chunks, [])
        assert 0 <= result["overall_health_score"] <= 100


class TestRAGRetrieval:
    """Quick smoke tests for rag.search_chunks from here (full coverage in test_rag.py)."""

    def test_search_chunks_import_from_pipeline(self):
        from pipeline import search_chunks
        chunks = [{"id": "CHK-001", "page": 1, "text": "knowledge AI pipeline", "char_count": 25, "approx_tokens": 4, "word_count": 3}]
        results = search_chunks("knowledge pipeline", chunks, top_k=1)
        assert len(results) == 1
        assert "relevance_score" in results[0]
