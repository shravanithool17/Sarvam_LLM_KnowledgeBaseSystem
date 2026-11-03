"""
tests/test_storage.py — Unit tests for storage/sqlite_store.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from storage.sqlite_store import SQLiteStore
from storage.backend import StorageBackend


@pytest.fixture
def store(tmp_storage_dir):
    return SQLiteStore(storage_dir=str(tmp_storage_dir))


def _metadata(doc_id="doc-001", filename="test.pdf"):
    return {
        "filename": filename,
        "size_bytes": 12345,
        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        "page_count": 3,
        "chunk_count": 5,
        "status": "processed",
        "model_used": "sarvam-105b",
    }


def _result(doc_id="doc-001"):
    return {
        "document_id": doc_id,
        "document_name": "test.pdf",
        "mode": "simulated",
        "stats": {"total_pages": 3, "total_chunks": 5, "total_chars": 1000},
        "knowledge": {
            "summary": "A test summary.",
            "facts": [{"entity": "E", "category": "C", "fact": "F", "citation": "CHK-001"}],
            "qa_dataset": [{"id": "QA-001", "instruction": "Q?", "response": "A.", "citation": "CHK-001"}],
        },
        "evaluation": {"overall_health_score": 80, "grounding_score": 90.0, "redundancy_rate": 0.0},
    }


def _eval_data():
    return {
        "overall_health_score": 80,
        "grounding_score": 90.0,
        "redundancy_rate": 5.0,
    }


class TestStorageBackendABC:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            StorageBackend()

    def test_sqlite_store_is_subclass(self, tmp_storage_dir):
        store = SQLiteStore(str(tmp_storage_dir))
        assert isinstance(store, StorageBackend)


class TestSQLiteStoreSaveAndLoad:
    def test_save_and_load_result_round_trip(self, store):
        doc_id = "round-trip-001"
        store.save_document(doc_id, _metadata(doc_id))
        store.save_result(doc_id, _result(doc_id))
        loaded = store.load_result(doc_id)
        assert loaded is not None
        assert loaded["document_id"] == doc_id
        assert loaded["knowledge"]["summary"] == "A test summary."

    def test_load_nonexistent_returns_none(self, store):
        assert store.load_result("does-not-exist-999") is None

    def test_save_document_is_idempotent(self, store):
        doc_id = "idempotent-001"
        meta = _metadata(doc_id)
        store.save_document(doc_id, meta)
        # Second save with updated chunk_count should overwrite
        meta["chunk_count"] = 99
        store.save_document(doc_id, meta)
        docs = store.list_documents()
        found = [d for d in docs if d["doc_id"] == doc_id]
        assert len(found) == 1
        assert found[0]["chunk_count"] == 99

    def test_result_survives_new_store_instance(self, tmp_storage_dir):
        """Data must survive a process restart (new SQLiteStore instance)."""
        doc_id = "persistent-001"
        store1 = SQLiteStore(str(tmp_storage_dir))
        store1.save_document(doc_id, _metadata(doc_id))
        store1.save_result(doc_id, _result(doc_id))

        # Simulate restart: create a fresh instance
        store2 = SQLiteStore(str(tmp_storage_dir))
        loaded = store2.load_result(doc_id)
        assert loaded is not None
        assert loaded["document_id"] == doc_id


class TestSQLiteStoreList:
    def test_list_documents_returns_all(self, store):
        for i in range(3):
            doc_id = f"list-doc-{i:03d}"
            store.save_document(doc_id, _metadata(doc_id, f"file_{i}.pdf"))

        docs = store.list_documents()
        ids = [d["doc_id"] for d in docs]
        assert "list-doc-000" in ids
        assert "list-doc-001" in ids
        assert "list-doc-002" in ids

    def test_list_documents_empty(self, store):
        assert store.list_documents() == []

    def test_list_documents_sorted_by_timestamp(self, store):
        import time
        for i in range(3):
            doc_id = f"sorted-{i:03d}"
            store.save_document(doc_id, _metadata(doc_id))
            time.sleep(0.01)  # ensure distinct timestamps

        docs = store.list_documents()
        # Most recent first
        timestamps = [d["upload_timestamp"] for d in docs]
        assert timestamps == sorted(timestamps, reverse=True)


class TestSQLiteStoreDelete:
    def test_delete_existing_returns_true(self, store):
        doc_id = "del-001"
        store.save_document(doc_id, _metadata(doc_id))
        store.save_result(doc_id, _result(doc_id))
        assert store.delete_document(doc_id) is True

    def test_delete_removes_db_record(self, store):
        doc_id = "del-002"
        store.save_document(doc_id, _metadata(doc_id))
        store.delete_document(doc_id)
        docs = store.list_documents()
        assert not any(d["doc_id"] == doc_id for d in docs)

    def test_delete_removes_json_file(self, store, tmp_storage_dir):
        doc_id = "del-003"
        store.save_document(doc_id, _metadata(doc_id))
        store.save_result(doc_id, _result(doc_id))

        result_path = tmp_storage_dir / doc_id / "result.json"
        assert result_path.exists()

        store.delete_document(doc_id)
        assert not result_path.exists()

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete_document("ghost-doc-999") is False

    def test_load_after_delete_returns_none(self, store):
        doc_id = "del-004"
        store.save_document(doc_id, _metadata(doc_id))
        store.save_result(doc_id, _result(doc_id))
        store.delete_document(doc_id)
        assert store.load_result(doc_id) is None


class TestSQLiteStoreEvaluation:
    def test_save_evaluation_inserts_row(self, store, tmp_storage_dir):
        doc_id = "eval-001"
        store.save_document(doc_id, _metadata(doc_id))
        store.save_evaluation(doc_id, _eval_data())

        # Verify row exists
        from sqlite3 import connect
        conn = connect(str(tmp_storage_dir / "knowledge_platform.db"))
        cursor = conn.execute(
            "SELECT * FROM evaluations WHERE doc_id = ?", (doc_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1

    def test_multiple_evaluations_per_document(self, store, tmp_storage_dir):
        doc_id = "eval-multi-001"
        store.save_document(doc_id, _metadata(doc_id))
        store.save_evaluation(doc_id, _eval_data())
        store.save_evaluation(doc_id, {**_eval_data(), "overall_health_score": 95})

        from sqlite3 import connect
        conn = connect(str(tmp_storage_dir / "knowledge_platform.db"))
        cursor = conn.execute(
            "SELECT COUNT(*) FROM evaluations WHERE doc_id = ?", (doc_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2


class TestSQLiteStoreChunks:
    def test_save_chunks_stores_metadata(self, store, tmp_storage_dir):
        doc_id = "chunks-001"
        store.save_document(doc_id, _metadata(doc_id))
        chunks = [
            {"id": "CHK-001", "page": 1, "char_count": 200, "approx_tokens": 40, "word_count": 38},
            {"id": "CHK-002", "page": 1, "char_count": 210, "approx_tokens": 42, "word_count": 40},
        ]
        store.save_chunks(doc_id, chunks)

        from sqlite3 import connect
        conn = connect(str(tmp_storage_dir / "knowledge_platform.db"))
        cursor = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", (doc_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

    def test_save_chunks_replaces_existing(self, store, tmp_storage_dir):
        doc_id = "chunks-replace-001"
        store.save_document(doc_id, _metadata(doc_id))
        chunks_v1 = [{"id": "CHK-001", "page": 1, "char_count": 100, "approx_tokens": 20, "word_count": 18}]
        chunks_v2 = [
            {"id": "CHK-001", "page": 1, "char_count": 100, "approx_tokens": 20, "word_count": 18},
            {"id": "CHK-002", "page": 2, "char_count": 120, "approx_tokens": 24, "word_count": 22},
        ]
        store.save_chunks(doc_id, chunks_v1)
        store.save_chunks(doc_id, chunks_v2)  # Should replace, not append

        from sqlite3 import connect
        conn = connect(str(tmp_storage_dir / "knowledge_platform.db"))
        cursor = conn.execute("SELECT COUNT(*) FROM chunks WHERE doc_id = ?", (doc_id,))
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2


class TestSQLiteStorePartialFailureRecovery:
    def test_json_write_failure_leaves_no_partial_file(self, store, tmp_storage_dir, monkeypatch):
        """If JSON write fails partway, no partial .tmp file should be left."""
        doc_id = "partial-fail-001"
        store.save_document(doc_id, _metadata(doc_id))

        # Make json.dumps fail
        import json as json_module
        original_dumps = json_module.dumps

        def bad_dumps(obj, **kwargs):
            if isinstance(obj, dict) and "document_id" in obj:
                raise RuntimeError("Simulated serialisation failure")
            return original_dumps(obj, **kwargs)

        monkeypatch.setattr(json_module, "dumps", bad_dumps)

        with pytest.raises(RuntimeError):
            store.save_result(doc_id, _result(doc_id))

        # No partial .tmp file should remain
        tmp_file = tmp_storage_dir / doc_id / "result.tmp"
        assert not tmp_file.exists()
