"""
tests/test_export.py — Unit tests for export.py
"""

import csv
import io
import json

import pytest

from export import to_jsonl, to_json, to_csv, to_markdown


class TestToJSONL:
    def test_valid_jsonl_parseable(self, sample_pipeline_data):
        output = to_jsonl(sample_pipeline_data)
        lines = [l for l in output.splitlines() if not l.startswith("#")]
        for line in lines:
            obj = json.loads(line)
            assert "instruction" in obj
            assert "output" in obj

    def test_stats_header_comment_present(self, sample_pipeline_data):
        output = to_jsonl(sample_pipeline_data)
        first_line = output.splitlines()[0]
        assert first_line.startswith("# stats:")

    def test_empty_qa_dataset(self, sample_pipeline_data):
        data = {**sample_pipeline_data, "knowledge": {"summary": "", "facts": [], "qa_dataset": []}}
        output = to_jsonl(data)
        # Only the stats header line
        lines = [l for l in output.splitlines() if l.strip()]
        assert len(lines) == 1  # just the header

    def test_alpaca_fields_present(self, sample_pipeline_data):
        output = to_jsonl(sample_pipeline_data)
        data_lines = [l for l in output.splitlines() if not l.startswith("#")]
        for line in data_lines:
            obj = json.loads(line)
            assert "instruction" in obj
            assert "input" in obj   # Alpaca empty context
            assert "output" in obj
            assert "citation" in obj

    def test_includes_batch_stats_in_header(self, sample_pipeline_data):
        output = to_jsonl(sample_pipeline_data)
        assert "batches=" in output or "batch" in output.lower()


class TestToJSON:
    def test_valid_json(self, sample_pipeline_data):
        output = to_json(sample_pipeline_data)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_required_keys_present(self, sample_pipeline_data):
        output = to_json(sample_pipeline_data)
        parsed = json.loads(output)
        for key in ("document_name", "chunks", "knowledge", "evaluation"):
            assert key in parsed

    def test_knowledge_subkeys(self, sample_pipeline_data):
        output = to_json(sample_pipeline_data)
        parsed = json.loads(output)
        knowledge = parsed["knowledge"]
        assert "summary" in knowledge
        assert "facts" in knowledge
        assert "qa_dataset" in knowledge

    def test_pretty_printed(self, sample_pipeline_data):
        output = to_json(sample_pipeline_data)
        assert "\n" in output  # indented = multi-line

    def test_empty_pipeline_data(self):
        output = to_json({})
        parsed = json.loads(output)
        assert isinstance(parsed, dict)


class TestToCSV:
    def test_valid_csv_parseable(self, sample_pipeline_data):
        output = to_csv(sample_pipeline_data)
        # Skip the comment header line
        csv_lines = [l for l in output.splitlines() if not l.startswith("#")]
        reader = csv.reader(csv_lines)
        rows = list(reader)
        assert len(rows) >= 1  # at least header row

    def test_header_row_correct(self, sample_pipeline_data):
        output = to_csv(sample_pipeline_data)
        csv_lines = [l for l in output.splitlines() if not l.startswith("#")]
        reader = csv.reader(csv_lines)
        header = next(reader)
        assert "ID" in header
        assert "Instruction" in header
        assert "Response" in header
        assert "Citation" in header

    def test_data_rows_match_qa_count(self, sample_pipeline_data):
        output = to_csv(sample_pipeline_data)
        csv_lines = [l for l in output.splitlines() if not l.startswith("#")]
        reader = csv.reader(csv_lines)
        rows = list(reader)
        qa_count = len(sample_pipeline_data["knowledge"]["qa_dataset"])
        # rows = 1 header + qa_count data rows
        assert len(rows) == qa_count + 1

    def test_stats_comment_present(self, sample_pipeline_data):
        output = to_csv(sample_pipeline_data)
        first_line = output.splitlines()[0]
        assert first_line.startswith("# stats:")

    def test_empty_qa_dataset(self):
        data = {"knowledge": {"summary": "", "facts": [], "qa_dataset": []}, "stats": {}}
        output = to_csv(data)
        csv_lines = [l for l in output.splitlines() if not l.startswith("#")]
        rows = list(csv.reader(csv_lines))
        assert len(rows) == 1  # header only


class TestToMarkdown:
    def test_has_executive_summary_heading(self, sample_pipeline_data):
        output = to_markdown(sample_pipeline_data)
        assert "## Executive Summary" in output

    def test_has_facts_heading(self, sample_pipeline_data):
        output = to_markdown(sample_pipeline_data)
        assert "## Structured Facts" in output

    def test_has_qa_heading(self, sample_pipeline_data):
        output = to_markdown(sample_pipeline_data)
        assert "## Instruction Q&A Dataset" in output

    def test_has_evaluation_metrics(self, sample_pipeline_data):
        output = to_markdown(sample_pipeline_data)
        assert "## Evaluation Metrics" in output

    def test_document_name_in_title(self, sample_pipeline_data):
        output = to_markdown(sample_pipeline_data)
        assert sample_pipeline_data["document_name"] in output

    def test_batch_stats_included_when_present(self, sample_pipeline_data):
        output = to_markdown(sample_pipeline_data)
        assert "Batch Processing" in output

    def test_batch_stats_absent_when_missing(self):
        data = {
            "document_name": "test.pdf",
            "mode": "simulated",
            "stats": {},
            "knowledge": {"summary": "Test.", "facts": [], "qa_dataset": []},
            "evaluation": {},
        }
        output = to_markdown(data)
        assert "Batch Processing Stats" not in output

    def test_summary_text_in_output(self, sample_pipeline_data):
        summary = sample_pipeline_data["knowledge"]["summary"]
        output = to_markdown(sample_pipeline_data)
        # At least the first 50 chars of summary should appear
        assert summary[:50] in output
