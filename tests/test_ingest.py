from __future__ import annotations

from pathlib import Path

import pytest

from src.rag.adapters.parser import PdfParser
from src.rag.authority import ADVISORY, NORMATIVE, UNTRUSTED, promptable
from src.rag.ingest import ingest_pdfs
from src.rag.logging import configure_logging

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"


def _by_record_id(records):
    return {r.metadata["record_id"]: r for r in records}


def test_ingest_extracts_four_records():
    run_id, records = ingest_pdfs(CORPUS, ingest_run_id="test-run")
    assert run_id == "test-run"
    assert len(records) == 4
    ids = {r.metadata["record_id"] for r in records}
    assert ids == {
        "ap-us-0001-v1.0",
        "ap-us-0001-v2.0",
        "exp-us-0001-v1.0",
        "mec-us-0001-v1.0",
    }


def test_ap_v1_is_replaced_and_v2_is_current():
    _, records = ingest_pdfs(CORPUS)
    by_id = _by_record_id(records)
    assert by_id["ap-us-0001-v1.0"].metadata["status"] == "replaced"
    assert by_id["ap-us-0001-v1.0"].metadata["superseded_by"] == "ap-us-0001-v2.0"
    assert by_id["ap-us-0001-v2.0"].metadata["status"] == "current"


def test_expense_title_comes_from_heading():
    _, records = ingest_pdfs(CORPUS)
    expense = _by_record_id(records)["exp-us-0001-v1.0"]
    assert expense.title == "Employee Expense Reimbursement Procedure"
    assert expense.metadata["title"] == expense.title


def test_superseded_rule_keeps_full_authority():
    """AP v1 is out of date, not unauthoritative. Lineage and authority are separate."""
    _, records = ingest_pdfs(CORPUS)
    v1 = _by_record_id(records)["ap-us-0001-v1.0"]
    approval = next(b for b in v1.blocks if b.section == "AP-5.1")
    assert approval.authority == NORMATIVE
    assert "$7,500" in approval.text
    assert v1.metadata["status"] == "replaced"


def test_faq_is_advisory_not_normative():
    _, records = ingest_pdfs(CORPUS)
    expense = _by_record_id(records)["exp-us-0001-v1.0"]
    faq = next(b for b in expense.blocks if b.section == "EXP-8.1")
    assert faq.authority == ADVISORY
    assert faq.content_type == "faq"


def test_close_export_residue_is_the_only_untrusted_block():
    _, records = ingest_pdfs(CORPUS)
    untrusted = [
        (r.metadata["record_id"], b)
        for r in records
        for b in r.blocks
        if b.authority == UNTRUSTED
    ]
    assert len(untrusted) == 1
    record_id, block = untrusted[0]
    assert record_id == "mec-us-0001-v1.0"
    assert block.authority_reason == "outside_heading_hierarchy"
    assert block.contains_pii is True


def test_personal_data_never_reaches_promptable_content():
    _, records = ingest_pdfs(CORPUS)
    for record in records:
        for block in promptable(record.blocks):
            assert "EE-4419" not in block.text
            assert "priya.shah" not in block.text.lower()


def test_account_code_stays_in_its_own_section():
    _, records = ingest_pdfs(CORPUS)
    close = _by_record_id(records)["mec-us-0001-v1.0"]
    with_code = [b.section for b in close.blocks if "6100" in b.text]
    assert with_code == ["MEC-5.1"]


def test_wrapped_cross_reference_does_not_start_a_section():
    """A reference that wraps onto its own line reads as a heading and eats the
    sentence it belongs to. Both of these end mid-clause when it does."""
    _, records = ingest_pdfs(CORPUS)
    close = _by_record_id(records)["mec-us-0001-v1.0"]
    by_section = {b.section: b for b in close.blocks}
    assert by_section["MEC-2.1"].text.rstrip().endswith("listed in Section\nMEC-4.1.")
    assert by_section["MEC-8.1"].text.rstrip().endswith(
        "MEC-7.1 stay with the close record."
    )


def test_section_ids_are_unique_within_a_record():
    _, records = ingest_pdfs(CORPUS)
    for record in records:
        sections = [b.section for b in record.blocks if b.section]
        assert len(sections) == len(set(sections)), record.metadata["record_id"]


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


def test_empty_extract_fails(monkeypatch):
    monkeypatch.setattr("src.rag.adapters.parser._extract_text", lambda path: "   ")
    with pytest.raises(ValueError, match="empty extract"):
        PdfParser().parse(Path("missing.pdf"))


def test_missing_status_fails(monkeypatch):
    monkeypatch.setattr(
        "src.rag.adapters.parser._extract_text",
        lambda path: (
            "doc_id: x\nrecord_id: x-v1\nfamily: f\nversion: v1.0\n"
            "effective_date: 2025-01-01\nsuperseded_by: none\nA Title\n"
        ),
    )
    with pytest.raises(ValueError, match="missing header fields"):
        PdfParser().parse(Path("no-status.pdf"))
