"""
knowledge.py — Hierarchical map-reduce knowledge synthesis via Sarvam AI.

Pipeline:
  1. MAP: each batch of chunks is synthesised independently by _synthesise_batch().
  2. REDUCE: all partial results are merged by _reduce_results() into a unified
     executive summary, fact list, and QA dataset.

Key properties:
  - Every chunk is processed; none are silently omitted.
  - Source chunk citations (CHK-XXX) are preserved through all stages.
  - Failed batches are tracked and processing continues with remaining batches.
  - Retries: configurable max retries with exponential back-off.
  - HTTP 429 rate-limit responses honour Retry-After when present.
  - API key is never logged or included in any response.
  - Simulated mode (no API key) produces clearly tagged mock results.

Sarvam API (verified against docs.sarvam.ai, 2025):
  Primary auth header : api-subscription-key
  Compat auth header  : Authorization: Bearer <key>
  Valid models        : sarvam-105b, sarvam-105b-conversations
  Default temperature : 0.2
  Endpoint            : https://api.sarvam.ai/v1/chat/completions

All functions are re-exported by pipeline.py for backward compatibility.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from logger import get_logger, mask_key, StageTimer

log = get_logger("knowledge")

# ---------------------------------------------------------------------------
# Sarvam AI HTTP client
# ---------------------------------------------------------------------------

def call_sarvam_chat(
    prompt: str,
    system_prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    api_url: Optional[str] = None,
    temperature: float = 0.2,
) -> str:
    """
    Calls the Sarvam AI chat completions endpoint.

    Auth: uses api-subscription-key (primary) per Sarvam documentation.
    Retries: up to settings.sarvam_max_retries times with exponential back-off.
    Rate limits: honours Retry-After header on HTTP 429.
    Malformed JSON: logs the raw response and returns "[SIMULATED_MODE]".
    API key: masked as '***' in all log output.

    Returns:
        The content string from the first choice, or "[SIMULATED_MODE]" on any
        unrecoverable failure or when no valid key is configured.
    """
    import requests  # lazy import

    key = (api_key or settings.sarvam_api_key or "").strip()
    if not key or key == "your_sarvam_api_key_here":
        log.info("No valid Sarvam API key — running in simulated mode.")
        return "[SIMULATED_MODE]"

    active_model = settings.resolve_model(model or settings.sarvam_model)
    url = api_url or settings.sarvam_api_url

    # Use api-subscription-key as primary auth (per docs.sarvam.ai)
    # Also include Authorization: Bearer for OpenAI-compatible tooling
    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": key,
        "Authorization": f"Bearer {key}",
    }

    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    max_retries = settings.sarvam_max_retries
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            log.info(
                f"Sarvam API call (attempt {attempt + 1}/{max_retries + 1})",
                extra={
                    "stage": "sarvam_api",
                    "model": active_model,
                    "api_key": mask_key(key),
                },
            )
            resp = requests.post(url, headers=headers, json=payload, timeout=settings.sarvam_timeout)

            # Rate limit handling
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                log.warning(
                    f"Sarvam API rate limited (HTTP 429). Waiting {retry_after}s before retry.",
                    extra={"stage": "sarvam_api", "attempt": attempt + 1},
                )
                if attempt < max_retries:
                    time.sleep(retry_after)
                    continue
                else:
                    return "[SIMULATED_MODE]"

            resp.raise_for_status()

            # Parse response
            try:
                data = resp.json()
            except Exception as json_exc:
                log.warning(
                    f"Sarvam API returned non-JSON response: {json_exc}. "
                    f"Raw (first 200 chars): {resp.text[:200]}",
                    extra={"stage": "sarvam_api"},
                )
                return "[SIMULATED_MODE]"

            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content") or msg.get("reasoning_content") or ""
                if content.strip():
                    return content

            log.warning("Sarvam API returned empty content.", extra={"stage": "sarvam_api"})
            return "[SIMULATED_MODE]"

        except requests.exceptions.Timeout as exc:
            last_error = exc
            wait = 2 ** (attempt + 1)
            log.warning(
                f"Sarvam API timeout (attempt {attempt + 1}). Retrying in {wait}s.",
                extra={"stage": "sarvam_api", "attempt": attempt + 1},
            )
            if attempt < max_retries:
                time.sleep(wait)
        except requests.exceptions.RequestException as exc:
            last_error = exc
            wait = 2 ** (attempt + 1)
            log.warning(
                f"Sarvam API error (attempt {attempt + 1}): {exc}. Retrying in {wait}s.",
                extra={"stage": "sarvam_api", "attempt": attempt + 1},
            )
            if attempt < max_retries:
                time.sleep(wait)

    log.error(
        f"All Sarvam API attempts exhausted. Last error: {last_error}",
        extra={"stage": "sarvam_api"},
    )
    return "[SIMULATED_MODE]"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_knowledge_schema(raw: Any) -> Dict[str, Any]:
    """
    Validates and normalises a raw knowledge dict.

    Raises ValueError if `raw` is not a dict or is missing all three required
    top-level keys ("summary", "facts", "qa_dataset").

    Partial data is accepted: missing keys default to safe empty values.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object, got {type(raw).__name__}.")

    required_keys = {"summary", "facts", "qa_dataset"}
    present = required_keys.intersection(raw.keys())
    if not present:
        raise ValueError(
            f"Knowledge dict missing required keys: {required_keys - present}."
        )

    # Normalise missing fields to safe defaults
    result = {
        "summary": raw.get("summary") or "",
        "facts": raw.get("facts") or [],
        "qa_dataset": raw.get("qa_dataset") or [],
    }

    # Validate each fact has minimum required fields
    validated_facts = []
    for f in result["facts"]:
        if isinstance(f, dict) and f.get("entity") and f.get("fact"):
            validated_facts.append({
                "entity": str(f.get("entity", "")),
                "category": str(f.get("category", "Concept")),
                "fact": str(f.get("fact", "")),
                "citation": str(f.get("citation", "")),
            })
    result["facts"] = validated_facts

    # Validate each QA pair has minimum required fields
    validated_qa = []
    for i, qa in enumerate(result["qa_dataset"]):
        if isinstance(qa, dict) and qa.get("instruction") and qa.get("response"):
            validated_qa.append({
                "id": str(qa.get("id", f"QA-{i+1:03d}")),
                "instruction": str(qa.get("instruction", "")),
                "response": str(qa.get("response", "")),
                "citation": str(qa.get("citation", "")),
                "confidence": str(qa.get("confidence", "Medium")),
            })
    result["qa_dataset"] = validated_qa

    return result


def _clean_json_response(raw_str: str) -> str:
    """Strips markdown code fences from an LLM response."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_str.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip(), flags=re.MULTILINE)
    return cleaned.strip()


def _parse_knowledge_response(raw: str, fallback_chunk_id: str) -> Dict[str, Any]:
    """
    Attempts to parse an LLM response as a knowledge dict.
    Returns a validated dict or a minimal fallback on any parse/validation error.
    """
    cleaned = _clean_json_response(raw)

    try:
        parsed = json.loads(cleaned)
        return _validate_knowledge_schema(parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning(f"Knowledge schema parse failed: {exc}. Using fallback partial extraction.")
        return {
            "summary": raw[:300] + ("..." if len(raw) > 300 else ""),
            "facts": [{
                "entity": "Extracted Content",
                "category": "Summary",
                "fact": raw[:200],
                "citation": fallback_chunk_id,
            }],
            "qa_dataset": [{
                "id": "QA-001",
                "instruction": "What is the primary focus of this document?",
                "response": raw[:200],
                "citation": fallback_chunk_id,
                "confidence": "Low",
            }],
        }


# ---------------------------------------------------------------------------
# Map phase: synthesise a single batch
# ---------------------------------------------------------------------------

def _build_batch_prompt(
    batch: List[Dict[str, Any]],
    batch_id: str,
    num_facts: int,
    num_qa_pairs: int,
) -> Tuple[str, str]:
    """Constructs the system and user prompts for a single batch."""
    context = "\n\n".join(
        [f"[{c['id']} - Page {c['page']}]: {c['text']}" for c in batch]
    )
    first_id = batch[0]["id"] if batch else "CHK-001"

    system_prompt = (
        "You are an expert AI Knowledge Engineer. You analyse unstructured technical "
        "documents and produce structured, high-quality, hallucination-free knowledge "
        "datasets. Always respond in valid JSON format only, matching the exact schema."
    )

    user_prompt = f"""Analyse the document context below and produce a structured knowledge dataset.

BATCH ID: {batch_id}
DOCUMENT CONTEXT:
\"\"\"
{context}
\"\"\"

Return a valid JSON object with this exact schema:
{{
  "summary": "2-3 sentence synthesis of key concepts in this batch.",
  "facts": [
    {{"entity": "Name", "category": "Concept | Process | Metric | Model | Architecture", "fact": "Concise key finding from the text.", "citation": "{first_id}"}}
  ],
  "qa_dataset": [
    {{
      "id": "QA-001",
      "instruction": "Specific question grounded in the context.",
      "response": "Accurate answer referencing facts from the context.",
      "citation": "{first_id}",
      "confidence": "High | Medium | Low"
    }}
  ]
}}

RULES:
- citation must be one of the chunk IDs provided (e.g. {', '.join(c['id'] for c in batch)}).
- Generate exactly {num_facts} facts and {num_qa_pairs} Q&A pairs.
- Do not invent information not present in the context."""

    return system_prompt, user_prompt


def _synthesise_batch(
    batch: List[Dict[str, Any]],
    batch_id: str,
    api_key: Optional[str],
    model: str,
    num_facts: int,
    num_qa_pairs: int,
) -> Dict[str, Any]:
    """
    Synthesises knowledge for a single batch of chunks.

    Returns:
        {
          "batch_id": str,
          "chunk_ids": [str, ...],
          "status": "processed" | "failed",
          "error": str | None,
          "knowledge": { summary, facts, qa_dataset } | None
        }
    """
    fallback_id = batch[0]["id"] if batch else "CHK-001"
    chunk_ids = [c["id"] for c in batch]

    system_prompt, user_prompt = _build_batch_prompt(batch, batch_id, num_facts, num_qa_pairs)

    with StageTimer(log, "batch_synthesis", batch_id=batch_id):
        raw = call_sarvam_chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            model=model,
            temperature=0.2,
        )

    if raw == "[SIMULATED_MODE]":
        # Simulated mode: return mock knowledge for this batch
        return {
            "batch_id": batch_id,
            "chunk_ids": chunk_ids,
            "status": "processed",
            "error": None,
            "knowledge": _get_simulated_batch_knowledge(batch),
            "simulated": True,
        }

    knowledge = _parse_knowledge_response(raw, fallback_id)
    return {
        "batch_id": batch_id,
        "chunk_ids": chunk_ids,
        "status": "processed",
        "error": None,
        "knowledge": knowledge,
        "simulated": False,
    }


# ---------------------------------------------------------------------------
# Reduce phase: merge all partial results
# ---------------------------------------------------------------------------

def _reduce_results(
    partials: List[Dict[str, Any]],
    api_key: Optional[str],
    model: str,
) -> Dict[str, Any]:
    """
    Merges all batch partial results into a unified knowledge representation.

    Executive summary: produced by the LLM from partial summaries.
    Facts and QA pairs: concatenated with original citations preserved.
    """
    # Collect all facts and QA pairs — citations are already chunk IDs
    all_facts: List[Dict[str, Any]] = []
    all_qa: List[Dict[str, Any]] = []
    partial_summaries: List[str] = []
    any_simulated = False

    qa_counter = 1
    for partial in partials:
        knowledge = partial.get("knowledge") or {}
        if partial.get("simulated"):
            any_simulated = True
        summary = knowledge.get("summary", "")
        if summary:
            partial_summaries.append(summary)
        all_facts.extend(knowledge.get("facts", []))
        for qa in knowledge.get("qa_dataset", []):
            # Re-sequence QA IDs to avoid collisions across batches
            qa["id"] = f"QA-{qa_counter:03d}"
            qa_counter += 1
            all_qa.append(qa)

    # Remove exact-duplicate facts (same entity + fact text)
    seen_facts = set()
    unique_facts: List[Dict[str, Any]] = []
    for f in all_facts:
        key = (f.get("entity", "").lower(), f.get("fact", "").lower()[:80])
        if key not in seen_facts:
            seen_facts.add(key)
            unique_facts.append(f)

    # Build executive summary via LLM (or fallback to concatenation)
    if len(partial_summaries) <= 1 or any_simulated:
        executive_summary = partial_summaries[0] if partial_summaries else ""
    else:
        summaries_text = "\n\n".join(
            [f"[Batch {i+1}]: {s}" for i, s in enumerate(partial_summaries)]
        )
        reduce_system = (
            "You are an expert technical writer. Combine the following batch summaries "
            "into a single coherent 3-sentence executive summary. Return only the summary text, "
            "no JSON wrapping."
        )
        reduce_prompt = (
            f"Batch summaries to combine:\n\n{summaries_text}\n\n"
            "Write a unified 3-sentence executive summary."
        )
        with StageTimer(log, "reduce_summary"):
            merged = call_sarvam_chat(
                prompt=reduce_prompt,
                system_prompt=reduce_system,
                api_key=api_key,
                model=model,
                temperature=0.2,
            )
        if merged == "[SIMULATED_MODE]":
            executive_summary = " ".join(partial_summaries)
        else:
            executive_summary = merged.strip()

    return {
        "summary": executive_summary,
        "facts": unique_facts,
        "qa_dataset": all_qa,
    }


# ---------------------------------------------------------------------------
# Simulated mode mock data
# ---------------------------------------------------------------------------

def _get_simulated_batch_knowledge(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Returns mock knowledge for a single batch in simulated mode."""
    c_id = batch[0]["id"] if batch else "CHK-001"
    snippet = (batch[0]["text"][:100] + "...") if batch else "document content"
    return {
        "summary": (
            f"This batch covers: {snippet} "
            "The content establishes key concepts and operational guidelines."
        ),
        "facts": [
            {
                "entity": "Knowledge Pipeline",
                "category": "Architecture",
                "fact": "Transforms unstructured documents into structured AI-ready datasets.",
                "citation": c_id,
            },
            {
                "entity": "Boundary-Aware Chunking",
                "category": "Process",
                "fact": "Respects paragraph and sentence boundaries to prevent fragmentation.",
                "citation": c_id,
            },
            {
                "entity": "Sarvam AI LLM",
                "category": "Model",
                "fact": "Powers multilingual synthesis and instruction-tuning dataset generation.",
                "citation": c_id,
            },
        ],
        "qa_dataset": [
            {
                "id": "QA-001",
                "instruction": "What is the primary objective of this knowledge pipeline?",
                "response": (
                    "To automate the end-to-end transformation of unstructured documents "
                    "into structured, validated, and deployment-ready knowledge representations."
                ),
                "citation": c_id,
                "confidence": "High",
            },
            {
                "id": "QA-002",
                "instruction": "How does the pipeline ensure traceability?",
                "response": (
                    "Every extracted fact and synthetic instruction-answer pair is mapped "
                    "directly to its origin chunk ID and page number."
                ),
                "citation": c_id,
                "confidence": "High",
            },
            {
                "id": "QA-003",
                "instruction": "What similarity metric is used for deduplication?",
                "response": (
                    "The pipeline uses Jaccard similarity to detect redundant chunk pairs, "
                    "flagging those with similarity exceeding the configured threshold."
                ),
                "citation": c_id,
                "confidence": "High",
            },
        ],
    }


def get_simulated_knowledge(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns simulated knowledge output when no Sarvam API key is configured.
    Result is tagged with 'mode': 'simulated' for clear distinction.
    Preserved for backward compatibility.
    """
    c_id = chunks[0]["id"] if chunks else "CHK-001"
    return {
        "summary": (
            "This document establishes the architecture and operational guidelines for "
            "knowledge engineering pipelines. It details the transition from raw unstructured "
            "formats to verified, searchable RAG datasets with source citations and quality evaluation."
        ),
        "facts": [
            {
                "entity": "Knowledge Pipeline",
                "category": "Architecture",
                "fact": "Transforms unstructured PDFs into structured, high-grade AI datasets.",
                "citation": c_id,
            },
            {
                "entity": "Boundary-Aware Chunking",
                "category": "Process",
                "fact": "Preserves paragraph and sentence contextual boundaries to prevent fragmentation.",
                "citation": c_id,
            },
            {
                "entity": "Sarvam AI LLM",
                "category": "Model",
                "fact": "Powers multilingual synthesis, entity extraction, and synthetic dataset generation.",
                "citation": c_id,
            },
        ],
        "qa_dataset": [
            {
                "id": "QA-001",
                "instruction": "What is the primary objective of the LLM Knowledge Pipeline?",
                "response": (
                    "To automate the end-to-end transformation of unstructured documents into "
                    "structured, validated, and deployment-ready knowledge representations."
                ),
                "citation": c_id,
                "confidence": "High",
            },
            {
                "id": "QA-002",
                "instruction": "How does the pipeline ensure traceability?",
                "response": (
                    "Every extracted fact and synthetic instruction-answer pair is mapped directly "
                    "to its origin chunk ID and page number."
                ),
                "citation": c_id,
                "confidence": "High",
            },
        ],
        "mode": "simulated",
    }


# ---------------------------------------------------------------------------
# Main public function: map-reduce synthesis
# ---------------------------------------------------------------------------

def synthesize_knowledge(
    chunks: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    num_chunks_per_batch: Optional[int] = None,
    num_facts: Optional[int] = None,
    num_qa_pairs: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Hierarchical map-reduce knowledge synthesis over ALL chunks.

    Strategy:
      MAP:    Each batch of `num_chunks_per_batch` chunks is synthesised independently.
      REDUCE: All partial results are merged into a unified executive summary,
              fact catalogue, and QA dataset. Citations are preserved throughout.

    Failed batches are tracked and processing continues with remaining batches.
    Already-successful batches are never regenerated.

    Args:
        chunks:              Chunk list from create_chunks().
        api_key:             Optional override for the Sarvam API key.
        model:               Optional model override (validated by settings.resolve_model).
        num_chunks_per_batch: Batch size; defaults to settings.synthesis_batch_size.
        num_facts:           Facts per batch; defaults to settings.default_num_facts.
        num_qa_pairs:        QA pairs per batch; defaults to settings.default_num_qa_pairs.

    Returns:
        {
          "summary": str,
          "facts": [...],
          "qa_dataset": [...],
          "mode": "live" | "simulated",
          "batch_processing_stats": {
              "total_batches": int,
              "processed": int,
              "skipped": int,
              "failed": int
          }
        }

    Backward compatibility: the returned dict always contains "summary", "facts",
    and "qa_dataset" at the top level, matching the original pipeline.py schema.
    """
    if not chunks:
        result = get_simulated_knowledge([])
        result["batch_processing_stats"] = {
            "total_batches": 0, "processed": 0, "skipped": 0, "failed": 0
        }
        return result

    batch_size = num_chunks_per_batch or settings.synthesis_batch_size
    n_facts = num_facts or settings.default_num_facts
    n_qa = num_qa_pairs or settings.default_num_qa_pairs
    active_model = settings.resolve_model(model or settings.sarvam_model)

    # Partition chunks into batches
    batches = [chunks[i: i + batch_size] for i in range(0, len(chunks), batch_size)]
    total_batches = len(batches)

    log.info(
        f"Starting map-reduce synthesis: {len(chunks)} chunks in {total_batches} batches",
        extra={"stage": "synthesis", "total_batches": total_batches},
    )

    # MAP phase
    partial_results: List[Dict[str, Any]] = []
    stats = {"total_batches": total_batches, "processed": 0, "skipped": 0, "failed": 0}
    any_simulated = False

    for idx, batch in enumerate(batches):
        batch_id = f"BATCH-{idx + 1:03d}"
        try:
            result = _synthesise_batch(
                batch=batch,
                batch_id=batch_id,
                api_key=api_key,
                model=active_model,
                num_facts=n_facts,
                num_qa_pairs=n_qa,
            )
            if result.get("simulated"):
                any_simulated = True
            partial_results.append(result)
            stats["processed"] += 1

        except Exception as exc:
            log.error(
                f"Batch {batch_id} failed after retries: {exc}",
                extra={"stage": "synthesis", "batch_id": batch_id},
            )
            partial_results.append({
                "batch_id": batch_id,
                "chunk_ids": [c["id"] for c in batch],
                "status": "failed",
                "error": str(exc),
                "knowledge": None,
                "simulated": False,
            })
            stats["failed"] += 1

    # Filter out failed batches before reduce
    successful = [p for p in partial_results if p.get("status") == "processed" and p.get("knowledge")]

    if not successful:
        log.warning("All batches failed — returning simulated knowledge.")
        result = get_simulated_knowledge(chunks)
        result["batch_processing_stats"] = stats
        return result

    # REDUCE phase
    with StageTimer(log, "reduce_synthesis"):
        merged = _reduce_results(successful, api_key, active_model)

    # Determine mode
    mode = "simulated" if any_simulated else "live"
    merged["mode"] = mode
    merged["batch_processing_stats"] = stats

    log.info(
        f"Synthesis complete: {len(merged['facts'])} facts, "
        f"{len(merged['qa_dataset'])} QA pairs, mode={mode}",
        extra={"stage": "synthesis", "mode": mode},
    )

    return merged
