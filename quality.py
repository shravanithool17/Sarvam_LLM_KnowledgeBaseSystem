"""
quality.py — Deduplication and grounding quality evaluation.

Provides:
  - compute_jaccard_similarity(): word-level Jaccard similarity
  - compute_tfidf_cosine(): TF-IDF cosine similarity using numpy
  - evaluate_dataset_quality(): full deduplication + grounding benchmark

All functions are re-exported by pipeline.py for backward compatibility.
"""

import math
import re
from typing import Any, Dict, List, Optional

import numpy as np

from config import settings
from logger import get_logger, StageTimer

log = get_logger("quality")


# ---------------------------------------------------------------------------
# Similarity metrics
# ---------------------------------------------------------------------------

def compute_jaccard_similarity(str1: str, str2: str) -> float:
    """
    Calculates word-level Jaccard similarity between two strings.
    Returns a float in [0.0, 1.0].
    """
    words1 = set(re.findall(r"\w+", str1.lower()))
    words2 = set(re.findall(r"\w+", str2.lower()))
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)


def _tokenize(text: str) -> List[str]:
    """Lowercases and splits on non-word chars."""
    return re.findall(r"\w+", text.lower())


def compute_tfidf_cosine(str1: str, str2: str) -> float:
    """
    Calculates TF-IDF cosine similarity between two strings using numpy.
    Returns a float in [0.0, 1.0].

    The 'corpus' is the pair of documents themselves, so IDF down-weights
    terms that appear in both strings.

    Returns 1.0 for identical non-empty strings, 0.0 for completely disjoint ones.
    """
    tokens1 = _tokenize(str1)
    tokens2 = _tokenize(str2)

    if not tokens1 or not tokens2:
        return 0.0

    # Build vocabulary from both documents
    vocab = sorted(set(tokens1) | set(tokens2))
    if not vocab:
        return 0.0

    word_index = {w: i for i, w in enumerate(vocab)}
    n_docs = 2  # our mini-corpus is always 2 documents

    def _tf_idf_vector(tokens: List[str]) -> np.ndarray:
        n = len(tokens)
        tf = np.zeros(len(vocab))
        for t in tokens:
            tf[word_index[t]] += 1
        tf = tf / n if n > 0 else tf

        # IDF: log((n_docs + 1) / (doc_freq + 1)) + 1  (sklearn-style smoothing)
        idf = np.zeros(len(vocab))
        for i, w in enumerate(vocab):
            doc_freq = (1 if w in set(tokens1) else 0) + (1 if w in set(tokens2) else 0)
            idf[i] = math.log((n_docs + 1) / (doc_freq + 1)) + 1

        return tf * idf

    vec1 = _tf_idf_vector(tokens1)
    vec2 = _tf_idf_vector(tokens2)

    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    cosine = float(np.dot(vec1, vec2) / (norm1 * norm2))
    # Clamp to [0, 1] to handle floating-point edge cases
    return max(0.0, min(1.0, cosine))


# ---------------------------------------------------------------------------
# Quality evaluation
# ---------------------------------------------------------------------------

def evaluate_dataset_quality(
    chunks: List[Dict[str, Any]],
    qa_dataset: List[Dict[str, Any]],
    threshold: Optional[float] = None,
    batch_processing_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluates dataset quality across two dimensions:

    1. Redundancy: chunk pairs with Jaccard similarity > threshold are flagged.
    2. Grounding: QA citations are verified against their source chunk texts.

    Args:
        chunks:                 Chunk list from create_chunks().
        qa_dataset:             QA list from synthesize_knowledge().
        threshold:              Similarity threshold (default: settings.similarity_threshold).
        batch_processing_stats: Optional batch stats dict to generate quality flags.

    Returns:
        Backward-compatible evaluation dict with additive new fields:
        {
          "overall_health_score": int (0–100),
          "grounding_score":      float,
          "redundancy_rate":      float,
          "duplicate_pairs":      [...],
          "total_chunks_evaluated": int,
          "total_qa_evaluated":   int,
          -- new fields (additive) --
          "per_qa_grounding":     [{"id", "grounded", "citation_valid"}, ...],
          "quality_flags":        [str, ...]   e.g. ["low_grounding", "high_redundancy"]
        }
    """
    sim_threshold = threshold if threshold is not None else settings.similarity_threshold

    with StageTimer(log, "quality_evaluation", chunk_count=len(chunks), qa_count=len(qa_dataset)):

        # 1. Chunk deduplication
        duplicates: List[Dict[str, Any]] = []
        total_comparisons = 0
        high_sim_count = 0

        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                total_comparisons += 1
                sim = compute_jaccard_similarity(chunks[i]["text"], chunks[j]["text"])
                if sim > sim_threshold:
                    high_sim_count += 1
                    duplicates.append({
                        "chunk_a": chunks[i]["id"],
                        "chunk_b": chunks[j]["id"],
                        "similarity": round(sim * 100, 1),
                        "preview": chunks[i]["text"][:60] + "...",
                    })

        redundancy_rate = round(
            (high_sim_count / max(1, total_comparisons)) * 100, 1
        )

        # 2. Grounding and citation traceability
        chunk_map = {c["id"]: c["text"] for c in chunks}
        valid_citations = 0
        per_qa_grounding: List[Dict[str, Any]] = []

        for qa in qa_dataset:
            cit = qa.get("citation", "")
            citation_valid = cit in chunk_map
            grounded = False

            if citation_valid:
                ans_words = set(re.findall(r"\w{4,}", qa.get("response", "").lower()))
                chunk_words = set(re.findall(r"\w{4,}", chunk_map[cit].lower()))
                if ans_words and len(ans_words & chunk_words) >= 2:
                    grounded = True
                    valid_citations += 1

            per_qa_grounding.append({
                "id": qa.get("id", ""),
                "grounded": grounded,
                "citation_valid": citation_valid,
            })

        grounding_score = round(
            (valid_citations / max(1, len(qa_dataset))) * 100, 1
        )

        # 3. Overall health score
        overall_health = max(
            10,
            min(100, round((grounding_score * 0.7) + ((100 - redundancy_rate) * 0.3))),
        )

        # 4. Quality flags
        quality_flags: List[str] = []
        if grounding_score < 50:
            quality_flags.append("low_grounding")
        if redundancy_rate > 30:
            quality_flags.append("high_redundancy")
        if batch_processing_stats and batch_processing_stats.get("failed", 0) > 0:
            quality_flags.append("failed_batches")
        if len(qa_dataset) == 0:
            quality_flags.append("no_qa_pairs")

    return {
        # Original fields (backward compatible)
        "overall_health_score": overall_health,
        "grounding_score": grounding_score,
        "redundancy_rate": redundancy_rate,
        "duplicate_pairs": duplicates,
        "total_chunks_evaluated": len(chunks),
        "total_qa_evaluated": len(qa_dataset),
        # New additive fields
        "per_qa_grounding": per_qa_grounding,
        "quality_flags": quality_flags,
    }
