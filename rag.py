"""
rag.py — Retrieval-Augmented Generation engine.

Provides keyword-based chunk retrieval and grounded answer generation via Sarvam AI.

All functions are re-exported by pipeline.py for backward compatibility.
"""

import math
import re
from typing import Any, Dict, List, Optional

from config import settings
from logger import get_logger, StageTimer

log = get_logger("rag")


def search_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant chunks for a query using keyword overlap scoring
    (normalised intersection size, cosine-style).

    Args:
        query:     The user's search query.
        chunks:    List of chunk dicts from create_chunks().
        top_k:     Maximum number of results to return (default: settings.default_top_k).
        min_score: Minimum relevance_score (0–100) to include in results
                   (default: settings.rag_min_score). Chunks below this threshold
                   are excluded. With min_score=0.0, all scored chunks are returned
                   (backward-compatible behaviour).

    Returns:
        List of chunk dicts augmented with "relevance_score" (float, 0–100),
        sorted descending by score, capped at top_k.
    """
    k = top_k if top_k is not None else settings.default_top_k
    score_floor = min_score if min_score is not None else settings.rag_min_score

    query_words = set(re.findall(r"\w+", query.lower()))

    with StageTimer(log, "rag_retrieval", query_len=len(query), num_chunks=len(chunks)):
        scored: List[Dict[str, Any]] = []

        for chunk in chunks:
            chunk_words = set(re.findall(r"\w+", chunk["text"].lower()))
            if not chunk_words:
                continue

            common = query_words & chunk_words
            # Normalised cosine-style keyword overlap score
            score = (
                len(common) / math.sqrt(len(query_words) * len(chunk_words))
                if query_words
                else 0.0
            )

            relevance = round(score * 100, 1)

            if relevance >= score_floor:
                scored.append({**chunk, "relevance_score": relevance})

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:k]


def answer_rag_query(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: Optional[str] = "sarvam-105b",
) -> Dict[str, Any]:
    """
    Generates a grounded answer citing the retrieved chunks via Sarvam AI.

    Returns:
        {
          "answer":   str  — the grounded answer text
          "citations": [str, ...]  — chunk IDs cited
        }
    """
    from knowledge import call_sarvam_chat  # avoid circular import

    context = "\n\n".join(
        [f"[{c['id']} (Page {c['page']})]: {c['text']}" for c in retrieved_chunks]
    )

    system_prompt = (
        "You are an accurate RAG assistant. Answer the user query using ONLY the provided "
        "context chunks. Explicitly cite the chunk IDs [CHK-XXX] used in your answer. "
        "Do not invent information not present in the context."
    )
    user_prompt = (
        f"Context:\n{context}\n\nQuestion: {query}\n\n"
        "Provide a factual, grounded answer with chunk citations."
    )

    with StageTimer(log, "rag_generation"):
        raw = call_sarvam_chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            model=model,
            temperature=0.2,
        )

    if raw == "[SIMULATED_MODE]":
        top_id = retrieved_chunks[0]["id"] if retrieved_chunks else "CHK-001"
        return {
            "answer": (
                f"Based on retrieved context [{top_id}], the system indicates that knowledge "
                "extraction requires strict verification and boundary-aware chunking to preserve context."
            ),
            "citations": [c["id"] for c in retrieved_chunks],
        }

    return {
        "answer": raw,
        "citations": [c["id"] for c in retrieved_chunks],
    }
