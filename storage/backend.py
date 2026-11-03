"""
storage/backend.py — Abstract storage interface for the AI Knowledge Engineering Platform.

This ABC is the single migration boundary. To swap from SQLite to PostgreSQL
or a vector database, implement a new concrete class and replace the default
instantiation in server.py — no other code needs to change.

Concrete implementations must:
  - Be thread-safe (or document their concurrency limitations)
  - Perform atomic writes where possible to prevent partial records
  - Return None (not raise) for missing document IDs on load/get operations
  - Clean up all associated files on delete
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StorageBackend(ABC):
    """
    Abstract base class defining the storage contract.

    All methods that retrieve a non-existent document should return None
    (or an empty list) rather than raising KeyError or similar.
    """

    @abstractmethod
    def save_document(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """
        Persist document metadata.

        Args:
            doc_id:   UUID string identifying the document.
            metadata: Dict containing at minimum:
                      filename, size_bytes, upload_timestamp, page_count,
                      chunk_count, status, model_used.

        Behaviour on duplicate doc_id: upsert (overwrite existing record).
        """
        ...

    @abstractmethod
    def save_result(self, doc_id: str, result: Dict[str, Any]) -> None:
        """
        Persist the full pipeline result for a document.

        The result dict is the complete JSON returned by /api/process.
        Implementations may store this as a JSON file, BLOB, or equivalent.

        Args:
            doc_id: UUID string identifying the document.
            result: Full pipeline response dict.
        """
        ...

    @abstractmethod
    def load_result(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the full pipeline result for a document.

        Returns:
            The pipeline result dict, or None if doc_id does not exist.
        """
        ...

    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        Return metadata for all stored documents, sorted by upload_timestamp
        descending (most recent first).

        Returns:
            List of metadata dicts. Empty list if no documents stored.
        """
        ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all stored data for a document (metadata, result, chunks, evaluations).

        Args:
            doc_id: UUID string identifying the document.

        Returns:
            True if the document existed and was deleted; False if not found.
        """
        ...

    @abstractmethod
    def save_evaluation(self, doc_id: str, eval_data: Dict[str, Any]) -> None:
        """
        Persist a quality evaluation result for a document.

        Multiple evaluations may be stored per document (one per pipeline run).

        Args:
            doc_id:    UUID string identifying the document.
            eval_data: Evaluation dict from evaluate_dataset_quality().
        """
        ...

    def save_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]) -> None:
        """
        Optional: persist chunk metadata for a document.
        Default implementation is a no-op (override to enable).

        Args:
            doc_id: UUID string identifying the document.
            chunks: List of chunk dicts.
        """
        pass
