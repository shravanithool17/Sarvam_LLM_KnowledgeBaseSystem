"""
chunking.py — Boundary-aware text chunking for the AI Knowledge Engineering Platform.

TERMINOLOGY: This module implements *boundary-aware* chunking, which respects
paragraph and sentence delimiters to avoid severing ideas mid-sentence.
It is NOT "semantic chunking" (which refers to embedding-based similarity grouping).

Key function:
  - create_chunks(): splits pages into boundary-aware chunks with corrected overlap.

Overlap fix (v2.0):
  The original implementation computed overlap as `int(overlap/5)` words, which
  was an inaccurate character-based approximation. The corrected implementation
  collects whole sentences from the tail of each chunk until the accumulated
  character count reaches `overlap` characters (or the sentence list is exhausted),
  then prepends those sentences to the next chunk. This ensures overlap always
  consists of complete sentences.

All functions are re-exported by pipeline.py for backward compatibility.
"""

import re
from typing import Any, Dict, List

from config import settings
from logger import get_logger, StageTimer

log = get_logger("chunking")

# ---------------------------------------------------------------------------
# Sentence-level overlap helpers
# ---------------------------------------------------------------------------

# Sentence boundary pattern: split on ". ", "! ", "? ", ".\n", etc.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> List[str]:
    """
    Splits text into sentences on common terminal punctuation boundaries.
    Returns a list of non-empty sentence strings.
    """
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _compute_overlap_text(text: str, overlap_chars: int) -> str:
    """
    Returns a suffix of `text` consisting of whole sentences whose total
    character length is as close to `overlap_chars` as possible (without
    exceeding it greedily — we take sentences from the end until we reach
    the target).

    If no sentence boundary is found, returns the last `overlap_chars`
    characters of text as a fallback (preserves backward compatibility
    for texts without sentence terminators).

    Args:
        text:          The chunk text to extract overlap from.
        overlap_chars: Target overlap length in characters.

    Returns:
        A string (possibly empty) to prepend to the next chunk.
    """
    if overlap_chars <= 0 or not text:
        return ""

    sentences = _split_sentences(text)

    if not sentences:
        # No sentence boundaries found — fall back to character slice
        return text[-overlap_chars:].strip()

    # Walk sentences from the end, accumulating until we hit the char budget
    selected: List[str] = []
    accumulated = 0
    for sentence in reversed(sentences):
        sentence_len = len(sentence) + 1  # +1 for the space separator
        if accumulated + sentence_len <= overlap_chars:
            selected.insert(0, sentence)
            accumulated += sentence_len
        else:
            # Budget would be exceeded — if we have nothing yet, take this one anyway
            # to guarantee at least one sentence of overlap
            if not selected:
                selected.insert(0, sentence)
            break

    return " ".join(selected).strip()


# ---------------------------------------------------------------------------
# Main chunking function
# ---------------------------------------------------------------------------

def create_chunks(
    pages: List[Dict[str, Any]],
    target_chunk_size: int = None,
    overlap: int = None,
    min_chunk_length: int = None,
) -> List[Dict[str, Any]]:
    """
    Splits text from a list of page dicts into boundary-aware chunks.

    Respects paragraph and sentence boundaries. Each chunk receives a
    permanent ID (CHK-001, CHK-002, …), source page reference, and metadata.

    Args:
        pages:             List of page dicts from ingest.extract_text_from_*().
                           Must have at least {"page": int, "text": str}.
        target_chunk_size: Target maximum character length per chunk.
                           Defaults to settings.default_chunk_size.
        overlap:           Target overlap in characters between consecutive chunks,
                           composed of whole sentences.
                           Defaults to settings.default_overlap.
        min_chunk_length:  Chunks shorter than this are discarded.
                           Defaults to settings.min_chunk_length.

    Returns:
        List of chunk dicts:
        {
          "id":            str   — "CHK-001", "CHK-002", ...
          "page":          int   — source page number
          "text":          str   — chunk text
          "char_count":    int,
          "approx_tokens": int   — rough word count as token approximation
          "word_count":    int
        }
    """
    chunk_size = target_chunk_size if target_chunk_size is not None else settings.default_chunk_size
    overlap_chars = overlap if overlap is not None else settings.default_overlap
    min_len = min_chunk_length if min_chunk_length is not None else settings.min_chunk_length

    chunks: List[Dict[str, Any]] = []
    chunk_counter = 1

    with StageTimer(log, "chunking", total_pages=len(pages)):
        for page_info in pages:
            page_num = page_info["page"]
            text = page_info.get("text", "").strip()

            if not text:
                continue

            # Split by paragraphs (two or more newlines) or by sentence terminators
            # followed by whitespace, preserving paragraph-level granularity first.
            paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
            if not paragraphs:
                paragraphs = [text]

            current_chunk = ""
            pending_overlap = ""  # overlap text to prepend to the next chunk

            for para in paragraphs:
                # Further split long paragraphs on sentence boundaries
                sentences = _split_sentences(para) or [para]

                for sentence in sentences:
                    candidate = (current_chunk + " " + sentence).strip() if current_chunk else sentence

                    if len(candidate) <= chunk_size:
                        current_chunk = candidate
                    else:
                        # Current chunk is full — flush it
                        if current_chunk:
                            chunk_text = (pending_overlap + " " + current_chunk).strip() if pending_overlap else current_chunk
                            if len(chunk_text) >= min_len:
                                chunks.append(_make_chunk(chunk_counter, page_num, chunk_text))
                                chunk_counter += 1

                            # Compute sentence-aware overlap for the next chunk
                            pending_overlap = _compute_overlap_text(chunk_text, overlap_chars)

                        # Start a new chunk with the current sentence
                        current_chunk = sentence

            # Flush the last chunk for this page
            if current_chunk:
                chunk_text = (pending_overlap + " " + current_chunk).strip() if pending_overlap else current_chunk
                if len(chunk_text) >= min_len:
                    chunks.append(_make_chunk(chunk_counter, page_num, chunk_text))
                    chunk_counter += 1
                pending_overlap = ""

    log.info(
        f"Chunking complete: {len(chunks)} chunks from {len(pages)} pages",
        extra={"stage": "chunking", "chunk_count": len(chunks)},
    )
    return chunks


def _make_chunk(chunk_id: int, page: int, text: str) -> Dict[str, Any]:
    """Constructs a single chunk dict from components."""
    words = text.split()
    return {
        "id": f"CHK-{chunk_id:03d}",
        "page": page,
        "text": text,
        "char_count": len(text),
        "approx_tokens": max(1, len(words)),
        "word_count": len(words),
    }
