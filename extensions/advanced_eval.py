"""
extensions/advanced_eval.py — STUB: Advanced evaluation laboratory (v3+)

Future capability:
  LLM-as-judge scoring, BLEU/ROUGE metrics, faithfulness evaluation,
  and automated red-teaming against the generated knowledge datasets.

  See interfaces/evaluation.py for the contract.
"""
from interfaces.evaluation import EvaluationBackend


class AdvancedEvaluationBackend(EvaluationBackend):
    """Placeholder — not implemented in v2."""

    def evaluate(self, chunks, qa_dataset, **kwargs):
        raise NotImplementedError("AdvancedEvaluationBackend is not yet implemented.")

    def score(self, str1, str2):
        raise NotImplementedError("AdvancedEvaluationBackend is not yet implemented.")
