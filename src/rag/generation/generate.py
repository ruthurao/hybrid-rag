from __future__ import annotations

from src.rag.models import Hit

CITATION_FIELDS = ("doc_id", "version", "section", "record_id", "status", "authority")

NO_HIT = "No current policy answers this question."
NO_COMPARE = "No versions of this policy were found."


class ExtractiveGenerator:
    """Pastes chunk text. The default so ask() never calls an API."""

    model_name = "extractive"

    def generate(
        self, query: str, hits: list[Hit], *, compare: bool = False
    ) -> tuple[str, list[dict]]:
        del query
        return generate(hits, compare=compare)


def generate(hits: list[Hit], *, compare: bool = False) -> tuple[str, list[dict]]:
    """Build an extractive answer and its citations. No model call."""
    if not hits:
        return (NO_COMPARE if compare else NO_HIT), []
    citations = _citations(hits)
    if compare:
        return _compare_text(hits), citations
    parts = []
    for hit in hits:
        cite = hit.chunk.metadata
        label = f"{cite.get('doc_id')} {cite.get('version')} {cite.get('section')}"
        parts.append(f"{label}\n{hit.chunk.text}")
    return "\n\n".join(parts), citations


def _compare_text(hits: list[Hit]) -> str:
    groups: dict[str, list[Hit]] = {"current": [], "replaced": []}
    for hit in hits:
        status = hit.chunk.metadata.get("status")
        if status in groups:
            groups[status].append(hit)
    parts: list[str] = []
    for status, heading in (
        ("current", "Current"),
        ("replaced", "Previous (replaced)"),
    ):
        if not groups[status]:
            continue
        parts.append(heading)
        for hit in groups[status]:
            cite = hit.chunk.metadata
            label = f"{cite.get('doc_id')} {cite.get('version')} {cite.get('section')}"
            parts.append(f"{label}\n{hit.chunk.text}")
    return "\n\n".join(parts)


def _citations(hits: list[Hit]) -> list[dict]:
    seen: set[tuple] = set()
    citations: list[dict] = []
    for hit in hits:
        row = {field: hit.chunk.metadata.get(field, "") for field in CITATION_FIELDS}
        key = tuple(row[field] for field in CITATION_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        citations.append(row)
    return citations
