from __future__ import annotations

import re

from src.rag.config import AnnotationPolicy, default_policy
from src.rag.models import FAQ, PROSE, TABLE


def detect_pii(text: str, policy: AnnotationPolicy | None = None) -> tuple[str, ...]:
    """Return the kinds of personal data found. Independent of authority.

    Job IDs such as US-0984 are roster references, not personal data, so the
    patterns are deliberately narrower than a generic identifier match.
    """
    policy = policy or default_policy()
    kinds = [
        kind
        for kind, pattern in policy.pii_patterns
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    return tuple(kinds)


def classify_content(text: str, policy: AnnotationPolicy | None = None) -> str:
    """Report the shape of a block: a table, a set of questions, or prose.

    Shape only. Whether the content carries any weight is decided elsewhere,
    and how it is cut is decided elsewhere again.
    """
    policy = policy or default_policy()
    lines = [line.strip() for line in text.splitlines()]
    if sum(1 for line in lines if line.startswith(policy.faq_markers)) >= 2:
        return FAQ
    if _longest_row_run(lines, policy) >= policy.min_table_rows:
        return TABLE
    return PROSE


def _longest_row_run(lines: list[str], policy: AnnotationPolicy) -> int:
    row = re.compile(policy.table_row)
    punctuation = re.compile(policy.table_row_punctuation)
    run = longest = 0
    for line in lines:
        is_row = bool(line) and bool(row.match(line)) and not punctuation.search(line)
        run = run + 1 if is_row else 0
        longest = max(longest, run)
    return longest
