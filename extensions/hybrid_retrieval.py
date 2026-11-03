"""
extensions/hybrid_retrieval.py — STUB: Hybrid retrieval (keyword + vector) (v3+)

Future capability:
  Combine BM25/TF-IDF keyword scoring with dense vector similarity using a
  reciprocal rank fusion (RRF) or weighted ensemble approach.

  See interfaces/retrieval.py for the contract.
"""
from interfaces.retrieval import RetrievalBackend


class HybridRetrievalBackend(RetrievalBackend):
    """Placeholder — not implemented in v2."""

    def search(self, query, chunks, top_k=2, min_score=0.0):
        raise NotImplementedError("HybridRetrievalBackend is not yet implemented.")

    def index_chunks(self, doc_id, chunks):
        raise NotImplementedError("HybridRetrievalBackend is not yet implemented.")
