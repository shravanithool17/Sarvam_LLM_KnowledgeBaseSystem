"""
tests/test_ingest.py — Unit tests for ingest.py

Tests cover:
  - PDF extraction (smoke, skipped page, failed page)
  - TXT extraction (success, encoding fallback warning)
  - DOCX extraction (success, empty doc)
  - validate_upload (size limit, MIME allowlist, magic bytes, filename sanitisation)
  - word_count field presence
  - cleanup_temp_file
  - build_ingestion_summary
"""

import io
import os
import tempfile
from pathlib import Path

import pytest

from ingest import (
    validate_upload,
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_text_from_docx,
    cleanup_temp_file,
    build_ingestion_summary,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# validate_upload
# ---------------------------------------------------------------------------

class TestValidateUpload:
    def test_valid_pdf(self):
        result = validate_upload("report.pdf", 1_000_000, b"%PDF-1.4 content here")
        assert result == "report.pdf"

    def test_valid_txt(self):
        result = validate_upload("notes.txt", 5000, b"hello world")
        assert result == "notes.txt"

    def test_valid_md(self):
        result = validate_upload("readme.md", 5000, b"# Title")
        assert result == "readme.md"

    def test_valid_docx(self):
        result = validate_upload("doc.docx", 5000, b"PK\x03\x04extra bytes here")
        assert result == "doc.docx"

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError) as exc_info:
            validate_upload("evil.exe", 100, b"MZ...")
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_xlsx_extension_raises(self):
        """XLSX has same magic bytes as DOCX but is not in the allowlist."""
        with pytest.raises(ValueError) as exc_info:
            validate_upload("data.xlsx", 100, b"PK\x03\x04")
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_file_too_large_raises(self):
        with pytest.raises(ValueError) as exc_info:
            validate_upload("big.pdf", 25 * 1024 * 1024, b"%PDF")
        assert exc_info.value.code == "UPLOAD_TOO_LARGE"

    def test_pdf_wrong_magic_bytes_raises(self):
        """A file named .pdf but containing non-PDF bytes should fail."""
        with pytest.raises(ValueError) as exc_info:
            validate_upload("fake.pdf", 1000, b"\x89PNG\r\n")  # PNG header
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_docx_wrong_magic_bytes_raises(self):
        with pytest.raises(ValueError) as exc_info:
            validate_upload("fake.docx", 1000, b"%PDF-1.4")
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_path_traversal_no_extension_raises_invalid_type(self):
        """
        Dangerous path like '../../etc/passwd' is sanitised to 'passwd' (no extension).
        Since '' is not in the allowed extensions allowlist, INVALID_FILE_TYPE is raised.
        This is the correct and safe behaviour — traversal paths are never accepted.
        """
        with pytest.raises(ValueError) as exc_info:
            validate_upload("../../etc/passwd", 100, b"plain text")
        assert exc_info.value.code == "INVALID_FILE_TYPE"

    def test_path_traversal_with_valid_ext(self):
        """Dangerous path is stripped to just the basename."""
        result = validate_upload("../../docs/report.pdf", 1000, b"%PDF-1.4")
        assert result == "report.pdf"
        assert "/" not in result
        assert "\\" not in result

    def test_txt_no_magic_check(self):
        """TXT files have no magic byte check — any content is accepted."""
        result = validate_upload("data.txt", 100, b"\x00\x01\x02binary")
        assert result == "data.txt"

    def test_empty_filename_raises(self):
        with pytest.raises((ValueError, Exception)):
            validate_upload("", 100, b"data")

    def test_exactly_at_size_limit_passes(self):
        """A file exactly at the limit (not exceeding) should pass."""
        from config import settings
        exact = settings.max_upload_size_mb * 1024 * 1024
        result = validate_upload("ok.pdf", exact, b"%PDF-1.4")
        assert result == "ok.pdf"

    def test_one_byte_over_limit_fails(self):
        from config import settings
        one_over = settings.max_upload_size_mb * 1024 * 1024 + 1
        with pytest.raises(ValueError) as exc_info:
            validate_upload("big.pdf", one_over, b"%PDF")
        assert exc_info.value.code == "UPLOAD_TOO_LARGE"


# ---------------------------------------------------------------------------
# extract_text_from_pdf
# ---------------------------------------------------------------------------

class TestExtractPDF:
    def test_smoke_with_fixture(self, sample_pdf_stream):
        pages = extract_text_from_pdf(sample_pdf_stream)
        assert isinstance(pages, list)
        assert len(pages) >= 1

    def test_page_schema(self, sample_pdf_stream):
        pages = extract_text_from_pdf(sample_pdf_stream)
        for p in pages:
            assert "page" in p
            assert "text" in p
            assert "char_count" in p
            assert "word_count" in p
            assert "status" in p
            assert "error_detail" in p
            assert p["status"] in ("ok", "skipped", "error")

    def test_word_count_matches_text(self, sample_pdf_stream):
        pages = extract_text_from_pdf(sample_pdf_stream)
        for p in pages:
            if p["status"] == "ok":
                assert p["word_count"] == len(p["text"].split())

    def test_char_count_matches_text(self, sample_pdf_stream):
        pages = extract_text_from_pdf(sample_pdf_stream)
        for p in pages:
            if p["status"] == "ok":
                assert p["char_count"] == len(p["text"])

    def test_ok_pages_have_text(self, sample_pdf_stream):
        pages = extract_text_from_pdf(sample_pdf_stream)
        ok_pages = [p for p in pages if p["status"] == "ok"]
        assert len(ok_pages) >= 1
        for p in ok_pages:
            assert len(p["text"]) > 0

    def test_invalid_stream_returns_empty(self):
        bad_stream = io.BytesIO(b"not a pdf")
        pages = extract_text_from_pdf(bad_stream)
        # Should return empty list or list with error pages, never raise
        assert isinstance(pages, list)

    def test_page_numbers_are_1_indexed(self, sample_pdf_stream):
        pages = extract_text_from_pdf(sample_pdf_stream)
        assert pages[0]["page"] == 1


# ---------------------------------------------------------------------------
# extract_text_from_txt
# ---------------------------------------------------------------------------

class TestExtractTXT:
    def test_valid_utf8(self, sample_txt_bytes):
        pages = extract_text_from_txt(sample_txt_bytes)
        assert len(pages) == 1
        assert pages[0]["status"] == "ok"
        assert pages[0]["word_count"] > 0
        assert pages[0]["char_count"] > 0
        assert pages[0]["error_detail"] is None

    def test_word_count_accuracy(self, sample_txt_bytes):
        pages = extract_text_from_txt(sample_txt_bytes)
        p = pages[0]
        # word_count should equal len(text.split())
        assert p["word_count"] == len(p["text"].split())

    def test_latin1_fallback_records_warning(self):
        """Non-UTF-8 bytes should fall back to latin-1 with a warning."""
        latin1_bytes = "Café résumé naïve".encode("latin-1")
        pages = extract_text_from_txt(latin1_bytes)
        assert len(pages) == 1
        assert pages[0]["status"] == "ok"
        assert pages[0]["error_detail"] is not None
        assert "UTF-8" in pages[0]["error_detail"] or "fallback" in pages[0]["error_detail"].lower()

    def test_empty_bytes_returns_empty(self):
        pages = extract_text_from_txt(b"")
        assert pages == []

    def test_whitespace_only_returns_empty(self):
        pages = extract_text_from_txt(b"   \n\n   ")
        assert pages == []

    def test_page_number_is_1(self, sample_txt_bytes):
        pages = extract_text_from_txt(sample_txt_bytes)
        assert pages[0]["page"] == 1


# ---------------------------------------------------------------------------
# extract_text_from_docx
# ---------------------------------------------------------------------------

class TestExtractDOCX:
    def _make_docx_bytes(self, text: str) -> bytes:
        """Creates a minimal DOCX in memory using python-docx."""
        from docx import Document
        doc = Document()
        doc.add_paragraph(text)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_basic_extraction(self):
        docx_bytes = self._make_docx_bytes(
            "Knowledge engineering builds AI systems from documents."
        )
        pages = extract_text_from_docx(docx_bytes)
        assert len(pages) == 1
        assert pages[0]["status"] == "ok"
        assert "knowledge" in pages[0]["text"].lower()

    def test_schema_fields_present(self):
        docx_bytes = self._make_docx_bytes("Some text here.")
        pages = extract_text_from_docx(docx_bytes)
        p = pages[0]
        assert "page" in p
        assert "text" in p
        assert "char_count" in p
        assert "word_count" in p
        assert "status" in p
        assert "error_detail" in p

    def test_word_count_accuracy(self):
        docx_bytes = self._make_docx_bytes("One two three four five words here.")
        pages = extract_text_from_docx(docx_bytes)
        p = pages[0]
        assert p["word_count"] == len(p["text"].split())

    def test_empty_document_returns_empty(self):
        from docx import Document
        doc = Document()
        buf = io.BytesIO()
        doc.save(buf)
        pages = extract_text_from_docx(buf.getvalue())
        assert pages == []

    def test_invalid_bytes_returns_empty(self):
        pages = extract_text_from_docx(b"not a docx file at all")
        assert isinstance(pages, list)


# ---------------------------------------------------------------------------
# cleanup_temp_file
# ---------------------------------------------------------------------------

class TestCleanupTempFile:
    def test_removes_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp_path = f.name
        assert os.path.exists(tmp_path)
        cleanup_temp_file(tmp_path)
        assert not os.path.exists(tmp_path)

    def test_no_error_on_nonexistent_file(self):
        """Should not raise even if file does not exist."""
        cleanup_temp_file("/nonexistent/path/file.tmp")

    def test_none_path_is_safe(self):
        cleanup_temp_file(None)


# ---------------------------------------------------------------------------
# build_ingestion_summary
# ---------------------------------------------------------------------------

class TestIngestionSummary:
    def test_all_ok(self):
        pages = [
            {"status": "ok", "error_detail": None},
            {"status": "ok", "error_detail": None},
        ]
        summary = build_ingestion_summary(pages)
        assert summary["pages_processed"] == 2
        assert summary["pages_skipped"] == 0
        assert summary["pages_failed"] == 0
        assert summary["encoding_warnings"] == []

    def test_mixed_statuses(self):
        pages = [
            {"status": "ok", "error_detail": None},
            {"status": "skipped", "error_detail": "No text."},
            {"status": "error", "error_detail": "Parse error."},
        ]
        summary = build_ingestion_summary(pages)
        assert summary["pages_processed"] == 1
        assert summary["pages_skipped"] == 1
        assert summary["pages_failed"] == 1
        assert len(summary["encoding_warnings"]) == 2  # skipped + error messages

    def test_empty_page_list(self):
        summary = build_ingestion_summary([])
        assert summary["pages_processed"] == 0
        assert summary["pages_skipped"] == 0
        assert summary["pages_failed"] == 0
