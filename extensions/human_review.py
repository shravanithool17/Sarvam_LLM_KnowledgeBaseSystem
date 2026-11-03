"""
extensions/human_review.py — STUB: Human-in-the-loop review workflow (v3+)

Future capability:
  Annotation interface for subject-matter experts to review, correct, and
  approve generated facts and QA pairs before committing them to the knowledge
  base. Supports label studio export format, feedback loop integration, and
  confidence re-scoring based on human annotations.
"""


class HumanReviewWorkflow:
    """Placeholder — not implemented in v2."""

    def submit_for_review(self, doc_id, facts, qa_dataset):
        raise NotImplementedError("HumanReviewWorkflow is not yet implemented.")

    def get_review_status(self, doc_id):
        raise NotImplementedError("HumanReviewWorkflow is not yet implemented.")

    def apply_corrections(self, doc_id, corrections):
        raise NotImplementedError("HumanReviewWorkflow is not yet implemented.")
