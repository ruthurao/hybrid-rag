from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from src.rag.config import AnnotationPolicy, default_policy
from src.rag.detectors import classify_content, detect_pii
from src.rag.models import FAQ, UNTYPED, Block

NORMATIVE = "normative"
ADVISORY = "advisory"
UNTRUSTED = "untrusted"

RANK = {NORMATIVE: 3, ADVISORY: 2, UNTRUSTED: 0}


def annotate_blocks(
    blocks: Iterable[Block],
    record_id: str,
    policy: AnnotationPolicy | None = None,
) -> list[Block]:
    policy = policy or default_policy()
    annotated: list[Block] = []
    for block in blocks:
        block.pii_kinds = detect_pii(block.text, policy)
        block.contains_pii = bool(block.pii_kinds)
        if block.content_type == UNTYPED:
            block.content_type = classify_content(block.text, policy)
        level, reason = _authority(block, record_id, policy)
        block.authority = level
        block.authority_rank = RANK[level]
        block.authority_reason = reason
        annotated.append(block)
    return annotated


def _authority(block: Block, record_id: str, policy: AnnotationPolicy) -> tuple[str, str]:
    override = policy.overrides.get((record_id, block.section or ""))
    if override:
        return override, "catalog_override"
    if block.section is None:
        # Sits outside the document's own heading hierarchy: no provenance,
        # so it carries no weight regardless of what it claims.
        return UNTRUSTED, "outside_heading_hierarchy"
    if _self_declared_non_binding(block.text, policy):
        return ADVISORY, "self_declared_non_binding"
    if block.content_type == FAQ:
        return ADVISORY, "faq_shape"
    if re.match(policy.section_id, block.section):
        return NORMATIVE, "numbered_section"
    return UNTRUSTED, "unrecognized_structure"


def _self_declared_non_binding(text: str, policy: AnnotationPolicy) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in policy.non_binding_phrases)


def authority_counts(blocks: Iterable[Block]) -> dict[str, int]:
    counts = Counter(block.authority for block in blocks)
    return {level: counts.get(level, 0) for level in (NORMATIVE, ADVISORY, UNTRUSTED)}


def promptable(blocks: Iterable[Block], min_rank: int = RANK[ADVISORY]) -> list[Block]:
    return [block for block in blocks if block.authority_rank >= min_rank]
