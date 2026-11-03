"""
ingest.py — Document extraction and ingestion for the AI Knowledge Engineering Platform.

Supports: PDF (.pdf), plain text (.txt, .md), DOCX (.docx).

Key functions:
  - validate_upload(): magic-byte MIME check, size enforcement, filename sanitisation
  - extract_text_from_pdf(): page-by-page PDF extraction
  - extract_text_from_txt(): plain text / markdown extraction
  - extract_text_from_docx(): DOCX paragraph extraction
  - cleanup_temp_file(): safe temp-file deletion

All functions are re-exported by pipeline.py for backward compatibility.
"""

import io
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from logger import get_logger, StageTimer

log = get_logger("ingest")

# ---------------------------------------------------------------------------
# Allowed file types — both extension and magic-byte signatures
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# Magic byte signatures: (offset, bytes_to_match)
_MAGIC_BYTES: Dict[str, Tuple[int, bytes]] = {
    ".pdf": (0, b"%PDF"),
    ".docx": (0, b"PK\x03\x04"),  # DOCX (and XLSX, PPTX) are ZIP archives
    # .txt and .md have no reliable magic bytes — extension check only
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_upload(
    filename: str,
    size_bytes: int,
    content_header: bytes = b"",
) -> str:
    """
    Validates a file upload. Raises ValueError on any violation.

    Checks (in order):
      1. Extension is in the allowlist.
      2. File size does not exceed MAX_UPLOAD_SIZE_MB.
      3. Magic bytes match the declared extension (where applicable).
      4. Sanitise and return the safe filename (no path traversal).

    Args:
        filename:       Original filename from the upload.
        size_bytes:     Total file size in bytes.
        content_header: First 8 bytes of file content for magic-byte check.

    Returns:
        The sanitised filename (basename only, no directory components).

    Raises:
        ValueError with a `code` attribute set to one of:
          "INVALID_FILE_TYPE"  — extension not in allowlist or magic mismatch
          "UPLOAD_TOO_LARGE"   — file exceeds MAX_UPLOAD_SIZE_MB
    """
    # Step 1 — Sanitise filename: strip path traversal, keep basename only
    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", ".."):
        err = ValueError("Invalid filename.")
        err.code = "INVALID_FILE_TYPE"  # type: ignore[attr-defined]
        raise err

    # Step 2 — Extension check
    ext = Path(safe_name).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        err = ValueError(
            f"File type '{ext}' is not supported. "
            f"Allowed types: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )
        err.code = "INVALID_FILE_TYPE"  # type: ignore[attr-defined]
        raise err

    # Step 3 — Size check
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        err = ValueError(
            f"File size {size_bytes / (1024*1024):.1f} MB exceeds the "
            f"{settings.max_upload_size_mb} MB limit."
        )
        err.code = "UPLOAD_TOO_LARGE"  # type: ignore[attr-defined]
        raise err

    # Step 4 — Magic-byte check (only for types with known signatures)
    if ext in _MAGIC_BYTES and content_header:
        magic_offset, magic_bytes = _MAGIC_BYTES[ext]
        header_slice = content_header[magic_offset: magic_offset + len(magic_bytes)]
        if header_slice != magic_bytes:
            err = ValueError(
                f"File content does not match declared type '{ext}'. "
                "The file signature (magic bytes) is invalid."
            )
            err.code = "INVALID_FILE_TYPE"  # type: ignore[attr-defined]
            raise err

    return safe_name


def cleanup_temp_file(path: Optional[str]) -> None:
    """
    Safely removes a temporary file if it exists.
    Logs a warning on failure but never raises.
    """
    if not path:
        return
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
            log.debug(f"Cleaned up temp file: {p.name}")
    except Exception as exc:
        log.warning(f"Failed to clean up temp file '{path}': {exc}")


# ---------------------------------------------------------------------------
# PDF Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_stream: io.BytesIO) -> List[Dict[str, Any]]:
    """
    Extracts text page by page from a PDF stream.

    Returns a list of page dicts:
      {
        "page": int,          — 1-indexed page number
        "text": str,          — cleaned extracted text
        "char_count": int,
        "word_count": int,
        "status": "ok" | "skipped" | "error",
        "error_detail": str | None
      }

    Pages that yield no text are marked "skipped".
    Pages that raise an exception are marked "error" with error_detail set.
    """
    from pypdf import PdfReader  # late import: only load if actually used

    pages: List[Dict[str, Any]] = []

    with StageTimer(log, "pdf_extraction"):
        try:
            reader = PdfReader(pdf_stream)
        except Exception as exc:
            log.error(f"Failed to open PDF: {exc}")
            return []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            try:
                raw_text = page.extract_text() or ""
                cleaned = re.sub(r"[ \t]+", " ", raw_text).strip()
                if not cleaned:
                    pages.append({
                        "page": page_num,
                        "text": "",
                        "char_count": 0,
                        "word_count": 0,
                        "status": "skipped",
                        "error_detail": "No extractable text on this page.",
                    })
                else:
                    pages.append({
                        "page": page_num,
                        "text": cleaned,
                        "char_count": len(cleaned),
                        "word_count": len(cleaned.split()),
                        "status": "ok",
                        "error_detail": None,
                    })
            except Exception as exc:
                log.warning(f"Page {page_num} extraction failed: {exc}")
                pages.append({
                    "page": page_num,
                    "text": "",
                    "char_count": 0,
                    "word_count": 0,
                    "status": "error",
                    "error_detail": str(exc),
                })

    return pages


# ---------------------------------------------------------------------------
# Plain Text / Markdown Extraction
# ---------------------------------------------------------------------------

def extract_text_from_txt(txt_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text from plain-text or Markdown files.

    Attempts UTF-8 decoding first; falls back to latin-1 and records a warning
    in `error_detail` rather than silently replacing characters.

    Returns a single-element list (plain text is treated as one page).
    """
    encoding_warning: Optional[str] = None

    try:
        text = txt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        encoding_warning = (
            f"UTF-8 decoding failed ({exc}); falling back to latin-1. "
            "Some characters may not render correctly."
        )
        log.warning(encoding_warning)
        text = txt_bytes.decode("latin-1", errors="replace")

    cleaned = re.sub(r"[ \t]+", " ", text).strip()

    if not cleaned:
        return []

    page: Dict[str, Any] = {
        "page": 1,
        "text": cleaned,
        "char_count": len(cleaned),
        "word_count": len(cleaned.split()),
        "status": "ok",
        "error_detail": encoding_warning,
    }
    return [page]


# ---------------------------------------------------------------------------
# DOCX Extraction
# ---------------------------------------------------------------------------

def extract_text_from_docx(docx_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text from a DOCX file, paragraph by paragraph.
    All paragraphs are joined and treated as a single page.

    Requires python-docx (listed in requirements.txt as 'python-docx').

    Returns a single-element list matching the page schema.
    Raises ImportError with guidance if python-docx is not installed.
    """
    try:
        from docx import Document  # python-docx
    except ImportError:
        raise ImportError(
            "python-docx is required for DOCX support. "
            "Install it with: pip install python-docx"
        )

    with StageTimer(log, "docx_extraction"):
        try:
            doc = Document(io.BytesIO(docx_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            text = " ".join(paragraphs)
            cleaned = re.sub(r"[ \t]+", " ", text).strip()

            if not cleaned:
                return []

            return [{
                "page": 1,
                "text": cleaned,
                "char_count": len(cleaned),
                "word_count": len(cleaned.split()),
                "status": "ok",
                "error_detail": None,
            }]
        except Exception as exc:
            log.error(f"DOCX extraction failed: {exc}")
            return []


# ---------------------------------------------------------------------------
# Ingestion summary helper
# ---------------------------------------------------------------------------

def build_ingestion_summary(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a summary dict from the page list returned by any extraction function.
    """
    processed = sum(1 for p in pages if p.get("status") == "ok")
    skipped = sum(1 for p in pages if p.get("status") == "skipped")
    failed = sum(1 for p in pages if p.get("status") == "error")
    warnings = [p["error_detail"] for p in pages if p.get("error_detail")]

    return {
        "pages_processed": processed,
        "pages_skipped": skipped,
        "pages_failed": failed,
        "encoding_warnings": warnings,
    }
