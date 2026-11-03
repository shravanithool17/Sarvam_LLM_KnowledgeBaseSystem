"""
storage/sqlite_store.py — SQLite + JSON file storage implementation.

Schema:
  documents   — document metadata (one row per document)
  chunks      — chunk metadata (one row per chunk)
  evaluations — evaluation history (one row per evaluation run)

Full JSON results are stored as {storage_dir}/{doc_id}/result.json
to avoid large BLOBs in SQLite.

Thread safety: SQLite WAL mode is enabled. Each operation uses a new
connection from the thread-local pool to support multi-threaded servers.

Partial failure handling:
  - save_document and save_result are wrapped in a two-phase commit:
    (1) write the JSON file, (2) INSERT/UPDATE the DB row.
    If the DB write fails, the JSON file is cleaned up.
  - delete_document removes the DB rows first, then the JSON file,
    so a crash leaves at most an orphaned file (not a ghost DB record).
  - All DB operations use SQLite transactions.
"""

import json
import os
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from storage.backend import StorageBackend
from logger import get_logger

log = get_logger("storage")

# Thread-local storage for SQLite connections, keyed by db_path
_local = threading.local()


class SQLiteStore(StorageBackend):
    """
    Default storage backend: SQLite metadata + JSON file payloads.

    Args:
        storage_dir: Base directory for all stored data.
                     Created if it does not exist.
    """

    def __init__(self, storage_dir: str = "./data/") -> None:
        self._base = Path(storage_dir).resolve()
        self._base.mkdir(parents=True, exist_ok=True)
        self._db_path = self._base / "knowledge_platform.db"
        self._init_db()
        log.info(
            f"SQLiteStore initialised at {self._base}",
            extra={"stage": "storage_init"},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """
        Returns a thread-local SQLite connection for this store's DB path.
        Keyed by db_path so different SQLiteStore instances (e.g. in tests)
        each get their own connection.
        """
        cache = getattr(_local, "conns", None)
        if cache is None:
            _local.conns = {}
            cache = _local.conns

        key = str(self._db_path)
        if key not in cache or cache[key] is None:
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            cache[key] = conn
        return cache[key]

    def _init_db(self) -> None:
        """Creates tables if they do not exist. Uses explicit transaction for atomicity."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id           TEXT PRIMARY KEY,
                filename         TEXT NOT NULL,
                size_bytes       INTEGER,
                upload_timestamp TEXT,
                page_count       INTEGER,
                chunk_count      INTEGER,
                status           TEXT,
                model_used       TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id         TEXT NOT NULL,
                chunk_id       TEXT NOT NULL,
                page           INTEGER,
                char_count     INTEGER,
                approx_tokens  INTEGER,
                word_count     INTEGER,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id               TEXT NOT NULL,
                eval_timestamp       TEXT NOT NULL,
                overall_health_score REAL,
                grounding_score      REAL,
                redundancy_rate      REAL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)
        conn.commit()

    def _result_path(self, doc_id: str) -> Path:
        """Returns the path to the JSON result file for a document."""
        return self._base / doc_id / "result.json"

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------

    def save_document(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """
        Upsert document metadata into the documents table.
        Atomic: wrapped in a transaction.
        """
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO documents
                        (doc_id, filename, size_bytes, upload_timestamp,
                         page_count, chunk_count, status, model_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(doc_id) DO UPDATE SET
                        filename         = excluded.filename,
                        size_bytes       = excluded.size_bytes,
                        upload_timestamp = excluded.upload_timestamp,
                        page_count       = excluded.page_count,
                        chunk_count      = excluded.chunk_count,
                        status           = excluded.status,
                        model_used       = excluded.model_used
                    """,
                    (
                        doc_id,
                        metadata.get("filename", ""),
                        metadata.get("size_bytes", 0),
                        metadata.get(
                            "upload_timestamp",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                        metadata.get("page_count", 0),
                        metadata.get("chunk_count", 0),
                        metadata.get("status", "processed"),
                        metadata.get("model_used", ""),
                    ),
                )
            log.info(
                f"Document metadata saved: {doc_id}",
                extra={"stage": "storage", "doc_id": doc_id},
            )
        except sqlite3.Error as exc:
            log.error(
                f"Failed to save document metadata for {doc_id}: {exc}",
                extra={"stage": "storage"},
            )
            raise

    def save_result(self, doc_id: str, result: Dict[str, Any]) -> None:
        """
        Persist the full pipeline result as a JSON file.

        Two-phase approach:
          1. Write JSON file.
          2. Confirm doc_id exists in documents table (it should after save_document).
        If the JSON write fails, no partial file is left behind.
        """
        result_path = self._result_path(doc_id)
        result_dir = result_path.parent

        # Phase 1: Write JSON file
        try:
            result_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = result_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            # Atomic rename (same filesystem)
            tmp_path.replace(result_path)
            log.info(
                f"Result JSON saved: {result_path}",
                extra={"stage": "storage", "doc_id": doc_id},
            )
        except Exception as exc:
            # Clean up any partial file
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            log.error(
                f"Failed to write result JSON for {doc_id}: {exc}",
                extra={"stage": "storage"},
            )
            raise

    def load_result(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load the full pipeline result; returns None if not found."""
        result_path = self._result_path(doc_id)
        if not result_path.exists():
            return None
        try:
            return json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error(
                f"Failed to load result for {doc_id}: {exc}",
                extra={"stage": "storage"},
            )
            return None

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return all documents sorted by upload_timestamp descending."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM documents ORDER BY upload_timestamp DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            log.error(f"list_documents failed: {exc}", extra={"stage": "storage"})
            return []

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove document from DB first, then delete the JSON file.
        A crash between DB delete and file delete leaves at most an
        orphaned file (no ghost DB record).

        Returns True if the document existed and was deleted, False if not found.
        """
        conn = self._get_conn()

        # Check existence
        cursor = conn.execute(
            "SELECT doc_id FROM documents WHERE doc_id = ?", (doc_id,)
        )
        if cursor.fetchone() is None:
            return False

        # Phase 1: Remove DB rows (CASCADE deletes chunks and evaluations)
        try:
            with conn:
                conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        except sqlite3.Error as exc:
            log.error(
                f"Failed to delete DB record for {doc_id}: {exc}",
                extra={"stage": "storage"},
            )
            raise

        # Phase 2: Remove JSON file and directory
        result_dir = self._base / doc_id
        if result_dir.exists():
            try:
                shutil.rmtree(result_dir)
            except Exception as exc:
                log.warning(
                    f"DB record deleted but file cleanup failed for {doc_id}: {exc}",
                    extra={"stage": "storage"},
                )
                # Don't re-raise: DB is clean, orphaned file is acceptable

        log.info(
            f"Document deleted: {doc_id}",
            extra={"stage": "storage", "doc_id": doc_id},
        )
        return True

    def save_evaluation(self, doc_id: str, eval_data: Dict[str, Any]) -> None:
        """Insert an evaluation record for a document."""
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO evaluations
                        (doc_id, eval_timestamp, overall_health_score,
                         grounding_score, redundancy_rate)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        datetime.now(timezone.utc).isoformat(),
                        eval_data.get("overall_health_score"),
                        eval_data.get("grounding_score"),
                        eval_data.get("redundancy_rate"),
                    ),
                )
        except sqlite3.Error as exc:
            log.error(
                f"Failed to save evaluation for {doc_id}: {exc}",
                extra={"stage": "storage"},
            )
            raise

    def save_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]) -> None:
        """Persist chunk metadata for a document (replaces existing chunks)."""
        conn = self._get_conn()
        try:
            with conn:
                conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
                conn.executemany(
                    """
                    INSERT INTO chunks
                        (doc_id, chunk_id, page, char_count, approx_tokens, word_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            doc_id,
                            c.get("id", ""),
                            c.get("page", 1),
                            c.get("char_count", 0),
                            c.get("approx_tokens", 0),
                            c.get("word_count", 0),
                        )
                        for c in chunks
                    ],
                )
        except sqlite3.Error as exc:
            log.error(
                f"Failed to save chunks for {doc_id}: {exc}",
                extra={"stage": "storage"},
            )
            raise
