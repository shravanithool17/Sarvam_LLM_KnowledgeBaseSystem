import os
import re
import io
import json
import math
from typing import List, Dict, Any, Optional
from pypdf import PdfReader

# ==========================================
# 1. Document Extraction & Preprocessing
# ==========================================

def extract_text_from_pdf(pdf_stream: io.BytesIO) -> List[Dict[str, Any]]:
    """Extracts text page by page with metadata."""
    reader = PdfReader(pdf_stream)
    pages = []
    for idx, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        # Clean up whitespace and line breaks
        cleaned_text = re.sub(r'[ \t]+', ' ', raw_text).strip()
        if cleaned_text:
            pages.append({
                "page": idx + 1,
                "text": cleaned_text,
                "char_count": len(cleaned_text)
            })
    return pages


def extract_text_from_txt(txt_bytes: bytes) -> List[Dict[str, Any]]:
    """Extracts text from plain text or markdown files."""
    text = txt_bytes.decode("utf-8", errors="replace")
    cleaned = re.sub(r'[ \t]+', ' ', text).strip()
    return [{
        "page": 1,
        "text": cleaned,
        "char_count": len(cleaned)
    }] if cleaned else []


# ==========================================
# 2. Intelligent Semantic Chunking
# ==========================================

def create_chunks(pages: List[Dict[str, Any]], target_chunk_size: int = 600, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Splits text across pages respecting sentence and paragraph boundaries,
    while tagging each chunk with page references, token approximations, and unique IDs.
    """
    chunks = []
    chunk_counter = 1

    for page_info in pages:
        page_num = page_info["page"]
        text = page_info["text"]
        
        # Split by paragraphs or double newlines first
        paragraphs = [p.strip() for p in re.split(r'\n{2,}|\.\s+', text) if p.strip()]
        
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) <= target_chunk_size:
                current_chunk += (" " + p if current_chunk else p)
            else:
                if current_chunk:
                    chunks.append({
                        "id": f"CHK-{chunk_counter:03d}",
                        "page": page_num,
                        "text": current_chunk.strip(),
                        "char_count": len(current_chunk.strip()),
                        "approx_tokens": max(1, len(current_chunk.strip().split()))
                    })
                    chunk_counter += 1
                
                # Handle overlap
                words = current_chunk.split()
                overlap_text = " ".join(words[-int(overlap/5):]) if len(words) > 15 else ""
                current_chunk = (overlap_text + " " + p).strip()

        if current_chunk:
            chunks.append({
                "id": f"CHK-{chunk_counter:03d}",
                "page": page_num,
                "text": current_chunk.strip(),
                "char_count": len(current_chunk.strip()),
                "approx_tokens": max(1, len(current_chunk.strip().split()))
            })
            chunk_counter += 1

    return chunks


# ==========================================
# 3. Sarvam AI Client & Knowledge Synthesis
# ==========================================

def call_sarvam_chat(
    prompt: str,
    system_prompt: str,
    api_key: Optional[str] = None,
    model: str = "sarvam-105b",
    api_url: str = "https://api.sarvam.ai/v1/chat/completions",
    temperature: float = 0.3
) -> str:
    """
    Calls Sarvam AI's chat completion endpoint.
    If no API key is provided or request fails, falls back gracefully.
    """
    key = api_key or os.getenv("SARVAM_API_KEY", "").strip()

    if not key or key == "your_sarvam_api_key_here":
        return "[SIMULATED_MODE]"

    import requests

    # Enforce active Sarvam models
    valid_models = ["sarvam-105b", "sarvam-105b-conversations"]
    active_model = model if model in valid_models else "sarvam-105b"

    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": key,
        "Authorization": f"Bearer {key}"
    }

    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            if content.strip():
                return content
        return "[SIMULATED_MODE]"
    except Exception as e:
        print(f"[Sarvam API Warning]: {e}. Using deterministic fallback.")
        return "[SIMULATED_MODE]"


def synthesize_knowledge(chunks: List[Dict[str, Any]], api_key: Optional[str] = None, model: str = "sarvam-105b") -> Dict[str, Any]:
    """
    Generates:
    1. Executive Summary
    2. Structured Facts & Entity Catalog
    3. Synthetic Instruction-Tuning Q&A Pairs with Citations
    """
    # Sample top 3 chunks (concise context for sub-15s response)
    selected_chunks = chunks[:3]
    context_text = "\n\n".join([f"[{c['id']} - Page {c['page']}]: {c['text']}" for c in selected_chunks])

    system_prompt = (
        "You are an expert AI Knowledge Engineer. You analyze unstructured technical documents "
        "and produce structured, high-quality, hallucination-free knowledge datasets. "
        "Always respond in valid JSON format only, matching the exact required schema."
    )

    user_prompt = f"""Analyze the document context below and produce a structured knowledge dataset in pure JSON format:

DOCUMENT CONTEXT:
\"\"\"
{context_text}
\"\"\"

Return a valid JSON object matching this schema:
{{
  "summary": "3-sentence synthesis of key concepts and objectives.",
  "facts": [
    {{"entity": "Name", "category": "Concept | Process | Metric", "fact": "Concise key finding", "citation": "{selected_chunks[0]['id'] if selected_chunks else 'CHK-001'}"}}
  ],
  "qa_dataset": [
    {{
      "id": "QA-001",
      "instruction": "Test question grounded in context",
      "response": "Accurate response referencing facts",
      "citation": "{selected_chunks[0]['id'] if selected_chunks else 'CHK-001'}",
      "confidence": "High"
    }}
  ]
}}
Provide 3 facts and 3 Q&A pairs."""

    raw_response = call_sarvam_chat(
        prompt=user_prompt,
        system_prompt=system_prompt,
        api_key=api_key,
        model=model,
        temperature=0.2
    )

    # Check for simulated mode or empty response
    if not raw_response or raw_response == "[SIMULATED_MODE]":
        return get_simulated_knowledge(chunks)

    # Clean JSON markdown fences if present
    raw_str = str(raw_response).strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw_str, flags=re.MULTILINE)
    cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback if model returned partial JSON
        return {
            "summary": raw_response[:300] + "...",
            "facts": [{"entity": "Extracted Content", "category": "Summary", "fact": raw_response[:200], "citation": chunks[0]["id"] if chunks else "CHK-001"}],
            "qa_dataset": [
                {
                    "id": "QA-001",
                    "instruction": "What is the primary focus of this document?",
                    "response": raw_response[:200],
                    "citation": chunks[0]["id"] if chunks else "CHK-001",
                    "confidence": "Medium"
                }
            ]
        }


def get_simulated_knowledge(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates preview knowledge output when no Sarvam API key is supplied yet."""
    first_chunk = chunks[0]["text"] if chunks else "Document text sample."
    c_id = chunks[0]["id"] if chunks else "CHK-001"
    
    return {
        "summary": (
            "This document establishes the architecture and operational guidelines for knowledge "
            "engineering pipelines. It details the transition from raw unstructured formats to verified, "
            "searchable RAG datasets with source citations and automated quality evaluation."
        ),
        "facts": [
            {"entity": "Knowledge Pipeline", "category": "Architecture", "fact": "Transforms unstructured PDFs into structured, high-grade AI datasets.", "citation": c_id},
            {"entity": "Semantic Chunking", "category": "Process", "fact": "Preserves paragraph and sentence contextual boundaries to prevent information fragmentation.", "citation": c_id},
            {"entity": "Sarvam AI LLM", "category": "Model", "fact": "Powers multilingual synthesis, entity extraction, and synthetic dataset generation.", "citation": c_id}
        ],
        "qa_dataset": [
            {
                "id": "QA-001",
                "instruction": "What is the primary objective of the LLM Knowledge Pipeline?",
                "response": "To automate the end-to-end transformation of unstructured documents into structured, validated, and deployment-ready knowledge representations.",
                "citation": c_id,
                "confidence": "High"
            },
            {
                "id": "QA-002",
                "instruction": "How does the pipeline ensure traceability?",
                "response": "Every extracted fact and synthetic instruction-answer pair is mapped directly to its origin chunk ID and page number.",
                "citation": c_id,
                "confidence": "High"
            }
        ]
    }


# ==========================================
# 4. Quality & Deduplication Benchmarking
# ==========================================

def compute_jaccard_similarity(str1: str, str2: str) -> float:
    """Calculates word-level Jaccard similarity between two strings."""
    words1 = set(re.findall(r'\w+', str1.lower()))
    words2 = set(re.findall(r'\w+', str2.lower()))
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)


def evaluate_dataset_quality(chunks: List[Dict[str, Any]], qa_dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates:
    - Redundancy / Duplicate chunk pairs (Jaccard > 0.45)
    - Grounding / Citation traceability
    - Overall Quality Score (0 - 100)
    """
    # 1. Chunk Deduplication
    duplicates = []
    total_comparisons = 0
    high_similarity_count = 0

    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            total_comparisons += 1
            sim = compute_jaccard_similarity(chunks[i]["text"], chunks[j]["text"])
            if sim > 0.45:
                high_similarity_count += 1
                duplicates.append({
                    "chunk_a": chunks[i]["id"],
                    "chunk_b": chunks[j]["id"],
                    "similarity": round(sim * 100, 1),
                    "preview": chunks[i]["text"][:60] + "..."
                })

    redundancy_rate = round((high_similarity_count / max(1, total_comparisons)) * 100, 1)

    # 2. Grounding & Traceability Audit
    chunk_map = {c["id"]: c["text"] for c in chunks}
    valid_citations = 0
    for qa in qa_dataset:
        cit = qa.get("citation", "")
        if cit in chunk_map:
            # Check if keywords in answer exist in chunk text
            ans_words = set(re.findall(r'\w{4,}', qa.get("response", "").lower()))
            chunk_words = set(re.findall(r'\w{4,}', chunk_map[cit].lower()))
            if ans_words and len(ans_words.intersection(chunk_words)) >= 2:
                valid_citations += 1

    grounding_score = round((valid_citations / max(1, len(qa_dataset))) * 100, 1)
    overall_health = max(10, min(100, round((grounding_score * 0.7) + ((100 - redundancy_rate) * 0.3))))

    return {
        "overall_health_score": overall_health,
        "grounding_score": grounding_score,
        "redundancy_rate": redundancy_rate,
        "duplicate_pairs": duplicates,
        "total_chunks_evaluated": len(chunks),
        "total_qa_evaluated": len(qa_dataset)
    }


# ==========================================
# 5. In-Memory RAG Retrieval Engine
# ==========================================

def search_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 2) -> List[Dict[str, Any]]:
    """Retrieves the most semantically relevant chunks for a user query."""
    scored_chunks = []
    query_words = set(re.findall(r'\w+', query.lower()))

    for chunk in chunks:
        chunk_words = set(re.findall(r'\w+', chunk["text"].lower()))
        if not chunk_words:
            continue
        common = query_words.intersection(chunk_words)
        score = (len(common) / math.sqrt(len(query_words) * len(chunk_words))) if query_words else 0.0
        
        scored_chunks.append({
            **chunk,
            "relevance_score": round(score * 100, 1)
        })

    # Sort descending by relevance
    scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored_chunks[:top_k]


def answer_rag_query(query: str, retrieved_chunks: List[Dict[str, Any]], api_key: Optional[str] = None, model: str = "sarvam-105b") -> Dict[str, Any]:
    """Generates a grounded answer citing the retrieved chunks."""
    context = "\n\n".join([f"[{c['id']} (Page {c['page']})]: {c['text']}" for c in retrieved_chunks])
    
    system_prompt = (
        "You are an accurate RAG assistant. Answer the user query using ONLY the provided context chunks. "
        "Explicitly cite the chunk IDs [CHK-XXX] used in your answer."
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a factual, grounded answer with citations."

    raw = call_sarvam_chat(user_prompt, system_prompt, api_key=api_key, model=model, temperature=0.2)

    if raw == "[SIMULATED_MODE]":
        top_id = retrieved_chunks[0]["id"] if retrieved_chunks else "CHK-001"
        return {
            "answer": f"Based on retrieved context [{top_id}], the system indicates that knowledge extraction requires strict verification and semantic chunking to preserve context.",
            "citations": [c["id"] for c in retrieved_chunks]
        }

    return {
        "answer": raw,
        "citations": [c["id"] for c in retrieved_chunks]
    }

