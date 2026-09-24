from __future__ import annotations

import re

from src.rag.config import AnnotationPolicy, default_policy


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
