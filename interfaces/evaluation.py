"""
interfaces/evaluation.py — EvaluationBackend abstract interface.

Default implementation: Jaccard/grounding engine in quality.py.
Future implementations: advanced_eval.py (LLM-as-judge, BLEU/ROUGE — see extensions/).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EvaluationBackend(ABC):
    """Abstract interface for knowledge quality evaluation engines."""

    @abstractmethod
    def evaluate(
        self,
        chunks: List[Dict[str, Any]],
        qa_dataset: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of a generated knowledge dataset.

        Returns:
            Dict containing at minimum: overall_health_score, grounding_score,
            redundancy_rate, duplicate_pairs, per_qa_grounding, quality_flags.
        """
        ...

    @abstractmethod
    def score(
        self,
        str1: str,
        str2: str,
    ) -> float:
        """
        Compute a similarity score between two text strings.
        Returns a float in [0.0, 1.0].
        """
        ...
