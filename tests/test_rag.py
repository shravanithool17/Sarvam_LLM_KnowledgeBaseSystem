"""
tests/test_rag.py — Unit tests for rag.py
"""

import pytest

from rag import search_chunks, answer_rag_query


def _make_chunks():
    return [
        {"id": "CHK-001", "page": 1, "text": "knowledge engineering AI pipeline systems",
         "char_count": 45, "approx_tokens": 7, "word_count": 6},
        {"id": "CHK-002", "page": 1, "text": "retrieval augmented generation document search",
         "char_count": 47, "approx_tokens": 6, "word_count": 5},
        {"id": "CHK-003", "page": 2, "text": "quality evaluation Jaccard similarity metrics",
         "char_count": 46, "approx_tokens": 6, "word_count": 5},
        {"id": "CHK-004", "page": 2, "text": "completely unrelated content about cooking recipes",
         "char_count": 50, "approx_tokens": 7, "word_count": 6},
    ]


class TestSearchChunks:
    def test_returns_top_k_results(self):
        chunks = _make_chunks()
        results = search_chunks("knowledge AI", chunks, top_k=2)
        assert len(results) == 2

    def test_top_k_one(self):
        chunks = _make_chunks()
        results = search_chunks("knowledge pipeline", chunks, top_k=1)
        assert len(results) == 1

    def test_relevance_score_present(self):
        chunks = _make_chunks()
        results = search_chunks("knowledge", chunks, top_k=4)
        for r in results:
            assert "relevance_score" in r
            assert 0.0 <= r["relevance_score"] <= 100.0

    def test_sorted_descending_by_score(self):
        chunks = _make_chunks()
        results = search_chunks("knowledge AI pipeline", chunks, top_k=4)
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_most_relevant_chunk_ranked_first(self):
        chunks = _make_chunks()
        results = search_chunks("knowledge engineering AI", chunks, top_k=2)
        assert results[0]["id"] == "CHK-001"

    def test_min_score_filter_excludes_low_relevance(self):
        chunks = _make_chunks()
        results = search_chunks("knowledge", chunks, top_k=4, min_score=50.0)
        for r in results:
            assert r["relevance_score"] >= 50.0

    def test_min_score_zero_returns_all_relevant(self):
        chunks = _make_chunks()
        results_zero = search_chunks("knowledge", chunks, top_k=4, min_score=0.0)
        results_high = search_chunks("knowledge", chunks, top_k=4, min_score=50.0)
        assert len(results_zero) >= len(results_high)

    def test_empty_chunk_list_returns_empty(self):
        results = search_chunks("knowledge", [], top_k=2)
        assert results == []

    def test_single_chunk(self):
        chunks = [{"id": "CHK-001", "page": 1, "text": "knowledge document",
                   "char_count": 18, "approx_tokens": 2, "word_count": 2}]
        results = search_chunks("knowledge", chunks, top_k=5)
        assert len(results) == 1

    def test_query_with_no_matching_words(self):
        chunks = _make_chunks()
        results = search_chunks("zzzzzzz qqqqqq", chunks, top_k=2, min_score=0.01)
        assert results == []

    def test_pipeline_re_export_works(self):
        from pipeline import search_chunks as pipeline_search
        chunks = _make_chunks()
        results = pipeline_search("knowledge", chunks, top_k=1)
        assert isinstance(results, list)
        assert len(results) == 1


class TestAnswerRAGQuery:
    def test_simulated_mode_returns_answer(self):
        chunks = _make_chunks()[:2]
        result = answer_rag_query("What is knowledge engineering?", chunks, api_key="")
        assert "answer" in result
        assert "citations" in result
        assert len(result["citations"]) > 0

    def test_citations_match_retrieved_chunks(self):
        chunks = _make_chunks()[:2]
        result = answer_rag_query("What is retrieval?", chunks, api_key="")
        for cit in result["citations"]:
            assert cit in [c["id"] for c in chunks]

    def test_empty_chunks_returns_default_citation(self):
        result = answer_rag_query("Query with no context", [], api_key="")
        assert "answer" in result

    def test_live_mode_with_mock(self, mock_sarvam_response):
        chunks = _make_chunks()[:2]
        with pytest.MonkeyPatch.context() as mp:
            # mock_sarvam_response patches requests.post globally
            result = answer_rag_query(
                "What is knowledge engineering?",
                chunks,
                api_key="sk-test-key"
            )
        assert "answer" in result
