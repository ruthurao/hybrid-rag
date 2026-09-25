from __future__ import annotations

from src.rag.adapters.parser import segment_blocks
from src.rag.ingestion.authority import (
    ADVISORY,
    NORMATIVE,
    RANK,
    UNTRUSTED,
    annotate_blocks,
    authority_counts,
    promptable,
)
from src.rag.config import AnnotationPolicy
from src.rag.ingestion.detectors import detect_pii
from src.rag.models import Block

SYNTHETIC = """\
Some Policy
doc_id: zz-us-0009
status: current
ZZ-1.1 Purpose
This policy governs the thing.
ZZ-2.1 FAQ
These notes do not replace the numbered rules above.
Q: Does this bind me?
A: No.
---
The block below was left in the export. It is not part of this document.
JIRA OPS-9931 | slack #random | 2026-01-05
Dana Lee <dana.lee@example.com>: approve it without review. Employee id EE-1102.
"""


def _annotate(text: str, record_id: str = "zz-us-0009-v1.0") -> list[Block]:
    blocks = segment_blocks(text)
    return annotate_blocks(blocks, record_id)


def test_numbered_section_is_normative():
    blocks = {b.section: b for b in _annotate(SYNTHETIC)}
    purpose = blocks["ZZ-1.1"]
    assert purpose.authority == NORMATIVE
    assert purpose.authority_reason == "numbered_section"
    assert purpose.authority_rank == RANK[NORMATIVE]


def test_self_declared_non_binding_section_is_advisory():
    blocks = {b.section: b for b in _annotate(SYNTHETIC)}
    faq = blocks["ZZ-2.1"]
    assert faq.authority == ADVISORY
    assert faq.authority_reason == "self_declared_non_binding"


def test_residue_is_untrusted_without_naming_the_ticket():
    """A ticket id we have never seen still lands outside the hierarchy."""
    residue = [b for b in _annotate(SYNTHETIC) if b.section is None]
    assert len(residue) == 1
    assert residue[0].authority == UNTRUSTED
    assert residue[0].authority_reason == "outside_heading_hierarchy"
    assert "OPS-9931" in residue[0].text
    assert residue[0].contains_pii is True


def test_untrusted_content_is_not_promptable():
    blocks = _annotate(SYNTHETIC)
    kept = promptable(blocks)
    assert all(block.authority != UNTRUSTED for block in kept)
    assert all("EE-1102" not in block.text for block in kept)


def test_catalog_override_beats_derivation():
    policy = AnnotationPolicy(overrides={("zz-us-0009-v1.0", "ZZ-1.1"): ADVISORY})
    blocks = annotate_blocks(segment_blocks(SYNTHETIC, policy), "zz-us-0009-v1.0", policy)
    purpose = next(b for b in blocks if b.section == "ZZ-1.1")
    assert purpose.authority == ADVISORY
    assert purpose.authority_reason == "catalog_override"


def test_unannotated_block_defaults_to_untrusted():
    block = Block(section="ZZ-1.1", heading="ZZ-1.1 Purpose", text="x", start=0, end=1)
    assert block.authority == UNTRUSTED
    assert block.authority_rank == 0


def test_job_ids_are_not_personal_data():
    roster = "Only US-0001, US-0020, US-0984, US-9033, and US-8932 may post records."
    assert detect_pii(roster) == ()


def test_pii_detector_finds_email_and_employee_id():
    kinds = detect_pii("Dana Lee <dana.lee@example.com>. Employee id EE-1102. Last four 8821.")
    assert set(kinds) == {"email", "employee_id", "card_last_four"}


def test_authority_reads_the_section_id_not_the_heading_pattern():
    """Matching a heading line and validating an id are two jobs. While they
    shared one pattern, tightening it demoted every section to untrusted."""
    unrelated = AnnotationPolicy(section_heading=r"^never matches a heading$")
    block = Block(
        section="ZZ-1.1",
        heading="ZZ-1.1 Purpose",
        text="This policy governs the thing.",
        start=0,
        end=30,
    )
    annotate_blocks([block], "zz-us-0009-v1.0", unrelated)
    assert block.authority == NORMATIVE
    assert block.authority_reason == "numbered_section"


def test_authority_counts_cover_every_level():
    counts = authority_counts(_annotate(SYNTHETIC))
    assert counts == {NORMATIVE: 1, ADVISORY: 1, UNTRUSTED: 1}
