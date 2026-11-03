"""
interfaces/synthesis.py — SynthesisBackend abstract interface.

Default implementation: map-reduce Sarvam AI pipeline in knowledge.py.
Future implementations: multi_document.py, knowledge_graph.py (see extensions/).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SynthesisBackend(ABC):
    """Abstract interface for knowledge synthesis engines."""

    @abstractmethod
    def synthesise(
        self,
        chunks: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Synthesise knowledge from a list of chunks.

        Returns:
            Dict containing at minimum: summary, facts, qa_dataset, mode,
            batch_processing_stats.
        """
        ...

    @abstractmethod
    def reduce(
        self,
        partial_results: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge multiple partial synthesis results into a unified result.
        """
        ...
