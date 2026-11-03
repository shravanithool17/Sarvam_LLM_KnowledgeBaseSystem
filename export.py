"""
export.py — Server-side export formatters for the AI Knowledge Engineering Platform.

Provides:
  - to_jsonl(): Alpaca-format JSONL for instruction fine-tuning
  - to_json():  Full pipeline result as formatted JSON
  - to_csv():   QA dataset as CSV for human review
  - to_markdown(): Summary + facts as readable Markdown

All functions accept the unified pipeline response dict (shape returned by
/api/process or /api/sample) and return a formatted string.

Note: client-side JS exports in index.html are preserved; these server-side
functions power the /api/export/{format} endpoint and provide richer formatting.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict


def _stats_header(data: Dict[str, Any]) -> str:
    """Builds a stats summary comment line for JSONL / CSV headers."""
    stats = data.get("stats", {})
    batch_stats = data.get("batch_processing_stats", {})
    knowledge = data.get("knowledge", {})
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parts = [
        f"document={data.get('document_name', 'unknown')}",
        f"chunks={stats.get('total_chunks', 0)}",
        f"facts={len(knowledge.get('facts', []))}",
        f"qa_pairs={len(knowledge.get('qa_dataset', []))}",
        f"mode={data.get('mode', 'unknown')}",
        f"exported_at={ts}",
    ]
    if batch_stats:
        parts.append(
            f"batches={batch_stats.get('total_batches',0)}"
            f"(ok={batch_stats.get('processed',0)}"
            f",fail={batch_stats.get('failed',0)})"
        )
    return " | ".join(parts)


def to_jsonl(data: Dict[str, Any]) -> str:
    """
    Exports the QA dataset as Alpaca-format JSONL.

    Each line is a JSON object: {instruction, input, output, citation, source_chunk}.
    A stats header comment is prepended.

    Returns:
        Newline-delimited string of JSON objects.
    """
    qa_list = data.get("knowledge", {}).get("qa_dataset", [])
    lines = [f"# stats: {_stats_header(data)}"]

    for qa in qa_list:
        record = {
            "instruction": qa.get("instruction", ""),
            "input": "",  # empty context field (Alpaca format)
            "output": qa.get("response", ""),
            "citation": qa.get("citation", ""),
            "source_chunk": qa.get("citation", ""),
            "confidence": qa.get("confidence", ""),
        }
        lines.append(json.dumps(record, ensure_ascii=False))

    return "\n".join(lines)


def to_json(data: Dict[str, Any]) -> str:
    """
    Exports the full pipeline result as formatted JSON.

    Includes: document metadata, stats, chunks, knowledge (summary/facts/qa),
    evaluation, and batch_processing_stats.

    Returns:
        Pretty-printed JSON string (indent=2).
    """
    export_payload = {
        "document_name": data.get("document_name", ""),
        "document_id": data.get("document_id", ""),
        "mode": data.get("mode", ""),
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": data.get("stats", {}),
        "ingestion_summary": data.get("ingestion_summary", {}),
        "batch_processing_stats": data.get("batch_processing_stats", {}),
        "chunks": data.get("chunks", []),
        "knowledge": {
            "summary": data.get("knowledge", {}).get("summary", ""),
            "facts": data.get("knowledge", {}).get("facts", []),
            "qa_dataset": data.get("knowledge", {}).get("qa_dataset", []),
        },
        "evaluation": data.get("evaluation", {}),
    }
    return json.dumps(export_payload, indent=2, ensure_ascii=False)


def to_csv(data: Dict[str, Any]) -> str:
    """
    Exports the QA dataset as a CSV file with a stats comment header.

    Columns: ID, Instruction, Response, Citation, Confidence

    Returns:
        CSV string suitable for spreadsheet tools.
    """
    output = io.StringIO()

    # Stats header as a comment row
    output.write(f"# stats: {_stats_header(data)}\n")

    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["ID", "Instruction", "Response", "Citation", "Confidence"])

    qa_list = data.get("knowledge", {}).get("qa_dataset", [])
    for qa in qa_list:
        writer.writerow([
            qa.get("id", ""),
            qa.get("instruction", ""),
            qa.get("response", ""),
            qa.get("citation", ""),
            qa.get("confidence", ""),
        ])

    return output.getvalue()


def to_markdown(data: Dict[str, Any]) -> str:
    """
    Exports a human-readable Markdown document containing:
      - Document metadata
      - Executive Summary
      - Structured Facts
      - QA Dataset
      - Evaluation Metrics
      - Batch Processing Stats (if present)

    Returns:
        Markdown-formatted string.
    """
    knowledge = data.get("knowledge", {})
    evaluation = data.get("evaluation", {})
    stats = data.get("stats", {})
    batch_stats = data.get("batch_processing_stats", {})
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Knowledge Report: {data.get('document_name', 'Untitled')}",
        "",
        f"**Exported**: {ts}  ",
        f"**Mode**: {data.get('mode', 'unknown')}  ",
        f"**Pages**: {stats.get('total_pages', 0)}  ",
        f"**Chunks**: {stats.get('total_chunks', 0)}  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        knowledge.get("summary", "_No summary available._"),
        "",
        "---",
        "",
        "## Structured Facts",
        "",
    ]

    for fact in knowledge.get("facts", []):
        lines += [
            f"### {fact.get('entity', 'Unknown')}",
            f"**Category**: {fact.get('category', '')}  ",
            f"**Fact**: {fact.get('fact', '')}  ",
            f"**Citation**: `{fact.get('citation', '')}`  ",
            "",
        ]

    if not knowledge.get("facts"):
        lines.append("_No facts extracted._")
        lines.append("")

    lines += [
        "---",
        "",
        "## Instruction Q&A Dataset",
        "",
    ]

    for qa in knowledge.get("qa_dataset", []):
        lines += [
            f"### {qa.get('id', '')}",
            f"**Instruction**: {qa.get('instruction', '')}  ",
            f"**Response**: {qa.get('response', '')}  ",
            f"**Citation**: `{qa.get('citation', '')}`  ",
            f"**Confidence**: {qa.get('confidence', '')}  ",
            "",
        ]

    if not knowledge.get("qa_dataset"):
        lines.append("_No QA pairs generated._")
        lines.append("")

    lines += [
        "---",
        "",
        "## Evaluation Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Overall Health Score | {evaluation.get('overall_health_score', '--')}% |",
        f"| Grounding Score | {evaluation.get('grounding_score', '--')}% |",
        f"| Redundancy Rate | {evaluation.get('redundancy_rate', '--')}% |",
        f"| Chunks Evaluated | {evaluation.get('total_chunks_evaluated', 0)} |",
        f"| QA Pairs Evaluated | {evaluation.get('total_qa_evaluated', 0)} |",
        "",
    ]

    if batch_stats:
        lines += [
            "---",
            "",
            "## Batch Processing Stats",
            "",
            f"| Stat | Value |",
            f"|------|-------|",
            f"| Total Batches | {batch_stats.get('total_batches', 0)} |",
            f"| Processed | {batch_stats.get('processed', 0)} |",
            f"| Skipped | {batch_stats.get('skipped', 0)} |",
            f"| Failed | {batch_stats.get('failed', 0)} |",
            "",
        ]

    flags = evaluation.get("quality_flags", [])
    if flags:
        lines += [
            "---",
            "",
            "## Quality Flags",
            "",
        ]
        for flag in flags:
            lines.append(f"- `{flag}`")
        lines.append("")

    return "\n".join(lines)
