"""
extensions/vector_retrieval.py — STUB: Vector database retrieval (v3+)

Future capability:
  Replace the keyword-based RetrievalBackend with dense vector search using
  an embedded vector database (Chroma, Pinecone, Weaviate, or pgvector).

  Planned features:
  - Text embedding via a sentence transformer model
  - Approximate nearest-neighbour (ANN) search over chunk embeddings
  - Persistent vector index with incremental updates
  - Filtering by document_id, page, or metadata tags

  Implementation entry point:
    class VectorRetrievalBackend(RetrievalBackend):
        def search(self, query, chunks, top_k, min_score): ...
        def index_chunks(self, doc_id, chunks): ...

  See interfaces/retrieval.py for the contract.
"""
from interfaces.retrieval import RetrievalBackend


class VectorRetrievalBackend(RetrievalBackend):
    """Placeholder — not implemented in v2."""

    def search(self, query, chunks, top_k=2, min_score=0.0):
        raise NotImplementedError(
            "VectorRetrievalBackend is not yet implemented. "
            "Use the default keyword-based search_chunks() from rag.py."
        )

    def index_chunks(self, doc_id, chunks):
        raise NotImplementedError(
            "VectorRetrievalBackend is not yet implemented."
        )
