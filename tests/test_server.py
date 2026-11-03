"""
tests/test_server.py — Integration tests for server.py endpoints.

All Sarvam API calls are mocked — no live API credits consumed.
"""

import io
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Patch requests.post BEFORE importing server to prevent live calls during module load
with patch("requests.post"):
    import server
    from server import app

FIXTURES = Path(__file__).parent / "fixtures"

client = TestClient(app, raise_server_exceptions=False)


def _make_sarvam_mock():
    """Returns a mock that simulates a valid Sarvam API response."""
    canned = {
        "summary": "Test summary from mock.",
        "facts": [{"entity": "E", "category": "C", "fact": "F.", "citation": "CHK-001"}],
        "qa_dataset": [{"id": "QA-001", "instruction": "Q?", "response": "A.", "citation": "CHK-001", "confidence": "High"}],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(canned)}}]
    }
    return mock_resp


# ---------------------------------------------------------------------------
# GET /api/status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_returns_200(self):
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_required_fields_present(self):
        resp = client.get("/api/status")
        data = resp.json()
        assert "status" in data
        assert "has_key" in data
        assert "default_model" in data

    def test_no_api_key_in_response(self):
        resp = client.get("/api/status")
        text = resp.text
        # The actual API key value should never appear in the response
        key = server.settings.sarvam_api_key
        if key and key != "your_sarvam_api_key_here":
            assert key not in text


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_required_fields(self):
        resp = client.get("/api/health")
        data = resp.json()
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "checks" in data

    def test_checks_has_required_keys(self):
        resp = client.get("/api/health")
        checks = resp.json()["checks"]
        assert "storage" in checks
        assert "python_version" in checks
        assert "disk_free_mb" in checks

    def test_status_is_ok_even_if_sarvam_unreachable(self):
        """Health check should always return 200, even if Sarvam is unreachable."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestServeUI:
    def test_returns_html(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_html_contains_sarvam(self):
        resp = client.get("/")
        assert "Sarvam" in resp.text

    def test_security_headers_present(self):
        resp = client.get("/")
        assert "x-frame-options" in resp.headers or "X-Frame-Options" in resp.headers


# ---------------------------------------------------------------------------
# POST /api/sample
# ---------------------------------------------------------------------------

class TestSample:
    def test_returns_200_with_mock(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post("/api/sample", json={"model": "sarvam-105b"})
        assert resp.status_code == 200

    def test_response_schema(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post("/api/sample", json={})
        data = resp.json()
        assert "document_name" in data
        assert "chunks" in data
        assert "knowledge" in data
        assert "evaluation" in data
        assert "stats" in data

    def test_no_api_key_in_response(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post("/api/sample", json={"api_key": "sk-secret-test-key"})
        assert "sk-secret-test-key" not in resp.text

    def test_document_id_present(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post("/api/sample", json={})
        assert "document_id" in resp.json()

    def test_mode_field_present(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post("/api/sample", json={})
        assert "mode" in resp.json()

    def test_batch_processing_stats_present(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post("/api/sample", json={})
        assert "batch_processing_stats" in resp.json()


# ---------------------------------------------------------------------------
# POST /api/process — upload validation
# ---------------------------------------------------------------------------

class TestProcessUpload:
    def _upload_txt(self, content: bytes, filename: str = "test.txt"):
        return client.post(
            "/api/process",
            files={"file": (filename, io.BytesIO(content), "text/plain")},
            data={"model": "sarvam-105b"},
        )

    def test_valid_txt_returns_200(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = self._upload_txt(
                (FIXTURES / "sample.txt").read_bytes(), "sample.txt"
            )
        assert resp.status_code == 200

    def test_response_has_required_fields(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = self._upload_txt(
                (FIXTURES / "sample.txt").read_bytes(), "sample.txt"
            )
        data = resp.json()
        assert "chunks" in data
        assert "knowledge" in data
        assert "evaluation" in data
        assert "document_id" in data

    def test_file_too_large_returns_413(self):
        # Create a content body that claims to be oversized via the size check in validate_upload
        # We simulate by passing a filename and patching settings
        from config import settings
        original = settings.max_upload_size_mb
        settings.max_upload_size_mb = 0  # force everything to be too large
        try:
            resp = self._upload_txt(b"some content", "test.txt")
            assert resp.status_code == 413
            assert resp.json()["code"] == "UPLOAD_TOO_LARGE"
        finally:
            settings.max_upload_size_mb = original

    def test_unsupported_file_type_returns_400(self):
        resp = client.post(
            "/api/process",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
            data={"model": "sarvam-105b"},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_FILE_TYPE"

    def test_pdf_with_wrong_magic_bytes_returns_400(self):
        resp = client.post(
            "/api/process",
            files={"file": ("fake.pdf", io.BytesIO(b"\x89PNG fake content"), "application/pdf")},
            data={"model": "sarvam-105b"},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_FILE_TYPE"

    def test_no_api_key_in_response(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post(
                "/api/process",
                files={"file": ("test.txt", io.BytesIO(b"Some test content for processing."), "text/plain")},
                data={"model": "sarvam-105b", "api_key": "sk-should-not-appear"},
            )
        assert "sk-should-not-appear" not in resp.text

    def test_custom_chunk_parameters_accepted(self):
        with patch("requests.post", return_value=_make_sarvam_mock()):
            resp = client.post(
                "/api/process",
                files={"file": ("test.txt", io.BytesIO(b"Knowledge engineering is a discipline. " * 20), "text/plain")},
                data={"model": "sarvam-105b", "chunk_size": "200", "overlap": "50"},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/rag
# ---------------------------------------------------------------------------

class TestRAG:
    def _sample_chunks(self):
        return [
            {"id": "CHK-001", "page": 1, "text": "knowledge engineering AI systems",
             "char_count": 35, "approx_tokens": 5, "word_count": 5},
            {"id": "CHK-002", "page": 1, "text": "document processing pipeline",
             "char_count": 30, "approx_tokens": 4, "word_count": 4},
        ]

    def test_returns_200(self):
        resp = client.post("/api/rag", json={
            "query": "What is knowledge engineering?",
            "chunks": self._sample_chunks(),
        })
        assert resp.status_code == 200

    def test_response_schema(self):
        resp = client.post("/api/rag", json={
            "query": "What is this?",
            "chunks": self._sample_chunks(),
        })
        data = resp.json()
        assert "query" in data
        assert "retrieved_chunks" in data
        assert "answer" in data
        assert "citations" in data

    def test_empty_chunks_returns_400(self):
        resp = client.post("/api/rag", json={
            "query": "What is this?",
            "chunks": [],
        })
        assert resp.status_code == 400
        assert "code" in resp.json()

    def test_no_api_key_in_response(self):
        resp = client.post("/api/rag", json={
            "query": "test",
            "chunks": self._sample_chunks(),
            "api_key": "sk-secret-rag-key",
        })
        assert "sk-secret-rag-key" not in resp.text


# ---------------------------------------------------------------------------
# POST /api/chunk-preview
# ---------------------------------------------------------------------------

class TestChunkPreview:
    def test_returns_chunks(self):
        resp = client.post("/api/chunk-preview", json={
            "text": "First sentence here. Second sentence here. Third sentence in this chunk."
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "chunks" in data
        assert "total_chunks" in data

    def test_chunk_schema(self):
        resp = client.post("/api/chunk-preview", json={
            "text": "Knowledge engineering sentence one. Another sentence here."
        })
        for chunk in resp.json()["chunks"]:
            assert "id" in chunk
            assert "text" in chunk
            assert "char_count" in chunk

    def test_text_too_long_returns_400(self):
        resp = client.post("/api/chunk-preview", json={"text": "x" * 50_001})
        assert resp.status_code == 400
        assert resp.json()["code"] == "TEXT_TOO_LONG"

    def test_custom_chunk_size_accepted(self):
        resp = client.post("/api/chunk-preview", json={
            "text": "Some longer content. " * 50,
            "chunk_size": 100,
            "overlap": 20,
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/export/{format}
# ---------------------------------------------------------------------------

class TestExport:
    def test_jsonl_export(self, sample_pipeline_data):
        resp = client.post("/api/export/jsonl", json=sample_pipeline_data)
        assert resp.status_code == 200
        assert "jsonlines" in resp.headers.get("content-type", "") or "json" in resp.headers.get("content-type", "")
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_json_export(self, sample_pipeline_data):
        resp = client.post("/api/export/json", json=sample_pipeline_data)
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_csv_export(self, sample_pipeline_data):
        resp = client.post("/api/export/csv", json=sample_pipeline_data)
        assert resp.status_code == 200
        assert "csv" in resp.headers.get("content-type", "")

    def test_md_export(self, sample_pipeline_data):
        resp = client.post("/api/export/md", json=sample_pipeline_data)
        assert resp.status_code == 200

    def test_unsupported_format_returns_400(self, sample_pipeline_data):
        resp = client.post("/api/export/xyz", json=sample_pipeline_data)
        assert resp.status_code == 400
        assert resp.json()["code"] == "UNSUPPORTED_FORMAT"


# ---------------------------------------------------------------------------
# Document storage endpoints
# ---------------------------------------------------------------------------

class TestDocumentStorage:
    def test_list_documents_returns_200(self):
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "documents" in data
        assert "total" in data

    def test_get_nonexistent_document_returns_404(self):
        resp = client.get("/api/documents/nonexistent-doc-id-xyz")
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_delete_nonexistent_document_returns_404(self):
        resp = client.delete("/api/documents/nonexistent-doc-id-xyz")
        assert resp.status_code == 404

    def test_process_then_retrieve(self):
        """Full flow: process a document, then retrieve it by document_id."""
        with patch("requests.post", return_value=_make_sarvam_mock()):
            process_resp = client.post(
                "/api/process",
                files={"file": ("test.txt", io.BytesIO(b"This is a test document with sufficient content. " * 10), "text/plain")},
                data={"model": "sarvam-105b"},
            )
        assert process_resp.status_code == 200
        doc_id = process_resp.json().get("document_id")
        assert doc_id

        # Retrieve stored result
        get_resp = client.get(f"/api/documents/{doc_id}")
        assert get_resp.status_code == 200
        assert get_resp.json().get("document_id") == doc_id

    def test_process_then_delete(self):
        """Full flow: process a document, delete it, confirm it's gone."""
        with patch("requests.post", return_value=_make_sarvam_mock()):
            process_resp = client.post(
                "/api/process",
                files={"file": ("del_test.txt", io.BytesIO(b"Delete test content. " * 10), "text/plain")},
                data={"model": "sarvam-105b"},
            )
        doc_id = process_resp.json().get("document_id")

        del_resp = client.delete(f"/api/documents/{doc_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        get_resp = client.get(f"/api/documents/{doc_id}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Error response shape
# ---------------------------------------------------------------------------

class TestErrorShape:
    def test_error_responses_have_consistent_shape(self):
        """All 4xx responses must have error, code, detail fields."""
        # unsupported file type
        resp = client.post(
            "/api/process",
            files={"file": ("bad.xyz", io.BytesIO(b"content"), "application/octet-stream")},
            data={},
        )
        if resp.status_code >= 400:
            data = resp.json()
            assert "error" in data
            assert "code" in data
            assert "detail" in data

    def test_chunk_preview_error_shape(self):
        resp = client.post("/api/chunk-preview", json={"text": "x" * 60000})
        data = resp.json()
        assert "error" in data
        assert "code" in data
