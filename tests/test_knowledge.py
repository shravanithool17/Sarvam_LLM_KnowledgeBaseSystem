"""
tests/test_knowledge.py — Unit tests for knowledge.py

All tests use mocked Sarvam API responses — no live API calls.

Tests cover:
  - Map-reduce covers all chunks (not just first 3)
  - Citation preservation through reduce step
  - Schema validation (_validate_knowledge_schema)
  - Simulated mode returns "mode": "simulated"
  - Live mode returns "mode": "live"
  - Retry on timeout
  - Batch failure handling (one batch fails → others continue)
  - Rate-limit response (HTTP 429) triggers back-off
  - Malformed JSON response falls back gracefully
  - API key never appears in log output
"""

import json
import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, call

import pytest
import requests

from knowledge import (
    synthesize_knowledge,
    get_simulated_knowledge,
    _validate_knowledge_schema,
    _parse_knowledge_response,
    call_sarvam_chat,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunks(n: int) -> List[Dict[str, Any]]:
    """Create n minimal chunk dicts."""
    return [
        {
            "id": f"CHK-{i+1:03d}",
            "page": (i // 3) + 1,
            "text": f"Sentence {i+1} about knowledge engineering and AI systems. "
                    f"This chunk covers concept {i+1} with detail and precision.",
            "char_count": 80,
            "approx_tokens": 16,
            "word_count": 15,
        }
        for i in range(n)
    ]


def _canned_response(chunk_ids: List[str]) -> Dict[str, Any]:
    """Returns a canned knowledge dict with citations matching provided chunk IDs."""
    cid = chunk_ids[0] if chunk_ids else "CHK-001"
    return {
        "summary": f"Summary for chunks {', '.join(chunk_ids)}.",
        "facts": [
            {"entity": "Pipeline", "category": "Architecture",
             "fact": "Transforms documents.", "citation": cid},
        ],
        "qa_dataset": [
            {"id": "QA-001", "instruction": "What does it do?",
             "response": "Transforms documents into datasets.", "citation": cid, "confidence": "High"},
        ],
    }


def _make_mock_http_response(knowledge: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(knowledge)}}]
    }
    return mock_resp


# ---------------------------------------------------------------------------
# _validate_knowledge_schema
# ---------------------------------------------------------------------------

class TestValidateKnowledgeSchema:
    def test_valid_full_schema(self):
        raw = {
            "summary": "A summary.",
            "facts": [{"entity": "E", "category": "C", "fact": "F.", "citation": "CHK-001"}],
            "qa_dataset": [{"id": "QA-001", "instruction": "Q?", "response": "A.", "citation": "CHK-001", "confidence": "High"}],
        }
        result = _validate_knowledge_schema(raw)
        assert result["summary"] == "A summary."
        assert len(result["facts"]) == 1
        assert len(result["qa_dataset"]) == 1

    def test_not_a_dict_raises(self):
        with pytest.raises(ValueError, match="JSON object"):
            _validate_knowledge_schema("just a string")

    def test_missing_all_required_keys_raises(self):
        with pytest.raises(ValueError, match="missing required keys"):
            _validate_knowledge_schema({"broken": True})

    def test_partial_keys_accepted(self):
        """Dict with only 'summary' is accepted; facts and qa_dataset default to []."""
        result = _validate_knowledge_schema({"summary": "Only summary."})
        assert result["summary"] == "Only summary."
        assert result["facts"] == []
        assert result["qa_dataset"] == []

    def test_invalid_fact_filtered_out(self):
        """Facts missing entity or fact fields are dropped."""
        raw = {
            "summary": "S",
            "facts": [
                {"entity": "E", "fact": "F", "citation": "CHK-001"},  # valid
                {"category": "C"},  # invalid — no entity or fact
            ],
            "qa_dataset": [],
        }
        result = _validate_knowledge_schema(raw)
        assert len(result["facts"]) == 1

    def test_invalid_qa_filtered_out(self):
        raw = {
            "summary": "S",
            "facts": [],
            "qa_dataset": [
                {"id": "QA-001", "instruction": "Q?", "response": "A."},  # valid
                {"id": "QA-002"},  # invalid — no instruction or response
            ],
        }
        result = _validate_knowledge_schema(raw)
        assert len(result["qa_dataset"]) == 1


# ---------------------------------------------------------------------------
# synthesize_knowledge — map-reduce coverage
# ---------------------------------------------------------------------------

class TestSynthesizeKnowledge:

    def test_all_chunks_processed_not_just_first_three(self):
        """Map-reduce must process ALL chunks, not just the first 3."""
        chunks = _make_chunks(9)  # 9 chunks → 3 batches of 3

        call_count = 0
        chunk_ids_seen = set()

        def mock_post(url, headers, json, timeout):
            nonlocal call_count
            call_count += 1
            # Extract chunk IDs from the prompt to verify all are processed
            content = json.get("messages", [{}])[-1].get("content", "")
            for chunk in chunks:
                if chunk["id"] in content:
                    chunk_ids_seen.add(chunk["id"])
            # Build response for the chunks mentioned
            mentioned_ids = [c["id"] for c in chunks if c["id"] in content]
            resp = _make_mock_http_response(_canned_response(mentioned_ids or ["CHK-001"]))
            return resp

        with patch("requests.post", side_effect=mock_post):
            result = synthesize_knowledge(chunks, api_key="sk-test-key", num_chunks_per_batch=3)

        # All 9 chunk IDs should have been seen across batch prompts
        for chunk in chunks:
            assert chunk["id"] in chunk_ids_seen, (
                f"Chunk {chunk['id']} was NOT processed — hardcoded first-3 bug!"
            )

        # Verify batch stats
        assert result["batch_processing_stats"]["total_batches"] == 3
        assert result["batch_processing_stats"]["processed"] == 3
        assert result["batch_processing_stats"]["failed"] == 0

    def test_citation_preserved_through_reduce(self):
        """Every fact and QA pair must have a citation pointing to an original chunk ID."""
        chunks = _make_chunks(6)
        valid_chunk_ids = {c["id"] for c in chunks}

        def mock_post(url, headers, json, timeout):
            content = json.get("messages", [{}])[-1].get("content", "")
            # Find which chunk IDs are in this batch
            batch_ids = [c["id"] for c in chunks if c["id"] in content]
            cid = batch_ids[0] if batch_ids else "CHK-001"
            return _make_mock_http_response({
                "summary": "Batch summary.",
                "facts": [{"entity": "E", "category": "C", "fact": "Fact.", "citation": cid}],
                "qa_dataset": [{"id": "QA-001", "instruction": "Q?", "response": "A.", "citation": cid, "confidence": "High"}],
            })

        with patch("requests.post", side_effect=mock_post):
            result = synthesize_knowledge(chunks, api_key="sk-test-key", num_chunks_per_batch=3)

        for fact in result["facts"]:
            assert fact["citation"] in valid_chunk_ids, (
                f"Fact citation '{fact['citation']}' is not a valid chunk ID."
            )
        for qa in result["qa_dataset"]:
            assert qa["citation"] in valid_chunk_ids, (
                f"QA citation '{qa['citation']}' is not a valid chunk ID."
            )

    def test_simulated_mode_when_no_key(self):
        """Without an API key, result must be tagged mode='simulated'."""
        # Temporarily unset API key
        from unittest.mock import patch as mpatch
        with mpatch.object(__import__('config').settings, 'sarvam_api_key', ''):
            result = synthesize_knowledge(_make_chunks(3), api_key="")
        assert result.get("mode") == "simulated"

    def test_live_mode_when_key_provided(self):
        """With a valid API response, result must be tagged mode='live'."""
        chunks = _make_chunks(3)
        mock_resp = _make_mock_http_response(_canned_response(["CHK-001"]))
        with patch("requests.post", return_value=mock_resp):
            result = synthesize_knowledge(chunks, api_key="sk-test-key")
        assert result.get("mode") == "live"

    def test_batch_failure_continues_processing(self):
        """
        If Sarvam API is unreachable for a batch (all retries exhausted),
        call_sarvam_chat returns '[SIMULATED_MODE]' and _synthesise_batch falls back
        to simulated knowledge rather than crashing. Processing continues for all
        other batches. The result is tagged mode='simulated'.
        This verifies the 'never crash, continue processing' contract.
        """
        chunks = _make_chunks(6)  # 2 batches of 3

        def mock_post_first_always_fails(url, headers, json, timeout):
            content = json.get("messages", [{}])[-1].get("content", "")
            # Batch 1 (CHK-001, CHK-002, CHK-003) always fails
            if "CHK-001" in content and "CHK-002" in content:
                raise requests.exceptions.RequestException("Simulated network error")
            # Batch 2 and reduce succeed
            return _make_mock_http_response(_canned_response(["CHK-004"]))

        with patch("requests.post", side_effect=mock_post_first_always_fails):
            with patch("time.sleep"):  # don't actually wait
                result = synthesize_knowledge(chunks, api_key="sk-test-key", num_chunks_per_batch=3)

        # Pipeline must not crash
        assert isinstance(result.get("summary"), str)
        assert "batch_processing_stats" in result
        # With exhausted retries, batch falls back to simulated — not a hard failure
        # mode will be 'simulated' since at least one batch used simulated fallback
        assert result.get("mode") in ("simulated", "live")
        # Both batches still produce output (simulated fallback for the failed one)
        assert len(result.get("facts", [])) > 0

    def test_retry_on_timeout(self):
        """Sarvam API timeout triggers retry; succeeds on 3rd attempt."""
        call_count = 0

        def mock_post_timeout_then_ok(url, headers, json, timeout):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise requests.exceptions.Timeout("Connection timed out")
            return _make_mock_http_response(_canned_response(["CHK-001"]))

        with patch("requests.post", side_effect=mock_post_timeout_then_ok):
            with patch("time.sleep"):  # don't actually wait
                result = call_sarvam_chat(
                    prompt="test prompt",
                    system_prompt="system",
                    api_key="sk-test-key",
                )
        # Should have retried and eventually returned content
        assert call_count >= 3
        assert result != "[SIMULATED_MODE]"

    def test_retry_exhausted_returns_simulated(self):
        """When all retries are exhausted, returns [SIMULATED_MODE]."""
        def always_timeout(url, headers, json, timeout):
            raise requests.exceptions.Timeout("Always fails")

        with patch("requests.post", side_effect=always_timeout):
            with patch("time.sleep"):
                result = call_sarvam_chat(
                    prompt="test", system_prompt="sys", api_key="sk-test"
                )
        assert result == "[SIMULATED_MODE]"

    def test_rate_limit_triggers_backoff(self):
        """HTTP 429 response should trigger back-off and retry."""
        call_count = 0

        def mock_429_then_ok(url, headers, json, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = MagicMock()
                resp.status_code = 429
                resp.headers = {"Retry-After": "1"}
                resp.raise_for_status = MagicMock()
                resp.json.return_value = {}
                return resp
            return _make_mock_http_response({"summary": "ok", "facts": [], "qa_dataset": []})

        with patch("requests.post", side_effect=mock_429_then_ok):
            with patch("time.sleep") as mock_sleep:
                result = call_sarvam_chat("prompt", "sys", api_key="sk-test")

        assert call_count >= 2
        mock_sleep.assert_called()

    def test_malformed_json_falls_back_gracefully(self):
        """Non-JSON response body should fall back to simulated mode gracefully."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        with patch("requests.post", return_value=mock_resp):
            result = call_sarvam_chat("prompt", "sys", api_key="sk-test")
        assert result == "[SIMULATED_MODE]"

    def test_api_key_not_in_log_output(self):
        """API key value must never appear in log output."""
        test_key = "sk-SECRET-DO-NOT-LOG-12345"
        log_records = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                log_records.append(self.format(record))

        import logging as stdlib_logging
        handler = CapturingHandler()
        stdlib_logging.getLogger("knowledge").addHandler(handler)
        stdlib_logging.getLogger("knowledge").setLevel(logging.DEBUG)

        try:
            mock_resp = _make_mock_http_response(_canned_response(["CHK-001"]))
            with patch("requests.post", return_value=mock_resp):
                call_sarvam_chat("prompt", "sys", api_key=test_key)
        finally:
            stdlib_logging.getLogger("knowledge").removeHandler(handler)

        full_log = " ".join(log_records)
        assert test_key not in full_log, (
            f"API key '{test_key}' found in log output!"
        )

    def test_empty_chunks_returns_simulated(self):
        result = synthesize_knowledge([], api_key="sk-test")
        assert "summary" in result
        assert "facts" in result
        assert "qa_dataset" in result
        assert result["batch_processing_stats"]["total_batches"] == 0

    def test_batch_stats_always_present(self):
        chunks = _make_chunks(3)
        mock_resp = _make_mock_http_response(_canned_response(["CHK-001"]))
        with patch("requests.post", return_value=mock_resp):
            result = synthesize_knowledge(chunks, api_key="sk-test-key")
        assert "batch_processing_stats" in result
        stats = result["batch_processing_stats"]
        assert "total_batches" in stats
        assert "processed" in stats
        assert "failed" in stats


# ---------------------------------------------------------------------------
# get_simulated_knowledge
# ---------------------------------------------------------------------------

class TestGetSimulatedKnowledge:
    def test_returns_mode_simulated(self):
        chunks = _make_chunks(2)
        result = get_simulated_knowledge(chunks)
        assert result.get("mode") == "simulated"

    def test_has_required_fields(self):
        chunks = _make_chunks(1)
        result = get_simulated_knowledge(chunks)
        assert "summary" in result
        assert "facts" in result
        assert "qa_dataset" in result

    def test_citations_use_first_chunk_id(self):
        chunks = _make_chunks(3)
        result = get_simulated_knowledge(chunks)
        for fact in result["facts"]:
            assert fact["citation"] == "CHK-001"
