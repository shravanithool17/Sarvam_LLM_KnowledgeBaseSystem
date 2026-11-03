"""
interfaces/retrieval.py — RetrievalBackend abstract interface.

Default implementation: keyword + TF-IDF scoring in rag.py.
Future implementations: vector_retrieval.py, hybrid_retrieval.py (see extensions/).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class RetrievalBackend(ABC):
    """Abstract interface for chunk retrieval engines."""

    @abstractmethod
    def search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 2,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant chunks for a query.

        Returns:
            List of chunk dicts augmented with 'relevance_score' (0–100),
            sorted descending, capped at top_k.
        """
        ...

    @abstractmethod
    def index_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]) -> None:
        """
        Index chunks for a document (optional pre-computation step).
        Default implementations may be no-ops.
        """
        ...
