from __future__ import annotations

from pathlib import Path

import pytest

from src.rag.adapters.parser import PdfParser
from src.rag.ingestion.authority import ADVISORY, NORMATIVE, UNTRUSTED
from src.rag.ingestion.ingest import ingest_pdfs
from src.rag.logging import configure_logging

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"


def test_ingest_extracts_four_records(ingested, records):
    run_id, parsed, _ = ingested
    assert run_id == "test-run"
    assert len(parsed) == 4
    assert set(records) == {
        "ap-us-0001-v1.0",
        "ap-us-0001-v2.0",
        "exp-us-0001-v1.0",
        "mec-us-0001-v1.0",
    }


def test_ap_v1_is_replaced_and_v2_is_current(records):
    assert records["ap-us-0001-v1.0"].metadata["status"] == "replaced"
    assert records["ap-us-0001-v1.0"].metadata["superseded_by"] == "ap-us-0001-v2.0"
    assert records["ap-us-0001-v2.0"].metadata["status"] == "current"


def test_expense_title_comes_from_heading(records):
    expense = records["exp-us-0001-v1.0"]
    assert expense.title == "Employee Expense Reimbursement Procedure"
    assert expense.metadata["title"] == expense.title


def test_superseded_rule_keeps_full_authority(records):
    """AP v1 is out of date, not unauthoritative. Lineage and authority are separate."""
    v1 = records["ap-us-0001-v1.0"]
    approval = next(b for b in v1.blocks if b.section == "AP-5.1")
    assert approval.authority == NORMATIVE
    assert "$7,500" in approval.text
    assert v1.metadata["status"] == "replaced"


def test_faq_is_advisory_not_normative(records):
    faq = next(b for b in records["exp-us-0001-v1.0"].blocks if b.section == "EXP-8.1")
    assert faq.authority == ADVISORY
    assert faq.content_type == "faq"


def test_untrusted_blocks_all_sit_outside_the_hierarchy(records):
    untrusted = [
        (record_id, block)
        for record_id, record in records.items()
        for block in record.blocks
        if block.authority == UNTRUSTED
    ]
    assert {record_id for record_id, _ in untrusted} == {"mec-us-0001-v1.0"}
    assert all(b.authority_reason == "outside_heading_hierarchy" for _, b in untrusted)
    assert any(b.contains_pii for _, b in untrusted)


def test_wrapped_cross_reference_does_not_start_a_section(records):
    """A reference that wraps onto its own line reads as a heading and eats the
    sentence it belongs to. Both of these end mid-clause when it does."""
    by_section = {b.section: b for b in records["mec-us-0001-v1.0"].blocks}
    assert by_section["MEC-2.1"].text.rstrip().endswith("listed in Section\nMEC-4.1.")
    assert by_section["MEC-8.1"].text.rstrip().endswith(
        "MEC-7.1 stay with the close record."
    )


def test_section_ids_are_unique_within_a_record(records):
    for record_id, record in records.items():
        sections = [b.section for b in record.blocks if b.section]
        assert len(sections) == len(set(sections)), record_id


def test_ingest_logs_counts_not_payload(capsys, parse_log_lines):
    configure_logging()
    ingest_pdfs(CORPUS, ingest_run_id="log-run")
    stderr = capsys.readouterr().err
    assert "priya" not in stderr.lower()
    assert "EE-4419" not in stderr
    events = {row["event"]: row for row in parse_log_lines(stderr)}
    assert events["ingest.start"]["pdf_count"] == 4
    assert events["ingest.done"]["record_count"] == 4
    assert set(events["ingest.record"]["authority"]) == {NORMATIVE, ADVISORY, UNTRUSTED}


def test_exclusions_are_reported_as_counts_and_reasons(capsys, parse_log_lines):
    configure_logging()
    ingest_pdfs(CORPUS, ingest_run_id="drop-run")
    rows = [
        row
        for row in parse_log_lines(capsys.readouterr().err)
        if row["event"] == "ingest.chunk" and row["record_id"] == "mec-us-0001-v1.0"
    ]
    assert rows[0]["excluded"] == 2
    assert rows[0]["excluded_reasons"] == {"outside_heading_hierarchy": 2}


def test_empty_extract_fails(monkeypatch):
    monkeypatch.setattr(
        "src.rag.adapters.parser._extract_text", lambda path, pages=None: "   "
    )
    with pytest.raises(ValueError, match="empty extract"):
        PdfParser().parse(Path("missing.pdf"))


def test_missing_status_fails(monkeypatch):
    monkeypatch.setattr(
        "src.rag.adapters.parser._extract_text",
        lambda path, pages=None: (
            "doc_id: x\nrecord_id: x-v1\nfamily: f\nversion: v1.0\n"
            "effective_date: 2025-01-01\nsuperseded_by: none\nA Title\n"
        ),
    )
    with pytest.raises(ValueError, match="missing header fields"):
        PdfParser().parse(Path("no-status.pdf"))
