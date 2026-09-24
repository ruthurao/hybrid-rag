from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from src.rag.authority import annotate_blocks
from src.rag.config import AnnotationPolicy, default_policy
from src.rag.models import Block, Record

REQUIRED_FIELDS = (
    "doc_id",
    "record_id",
    "family",
    "version",
    "status",
    "effective_date",
    "superseded_by",
)

HEADER_KEYS = REQUIRED_FIELDS + ("title", "currency", "entity_types")

HEADER_LINE = re.compile(
    r"^(doc_id|record_id|title|family|version|effective_date|status|"
    r"superseded_by|currency|entity_types|field|value)\b",
    re.IGNORECASE,
)


class PdfParser:
    """Text layer only, OCR off. Extracts and segments; it does not judge."""

    def __init__(self, policy: AnnotationPolicy | None = None) -> None:
        self.policy = policy or default_policy()

    def parse(self, path: Path) -> Record:
        text = _extract_text(path)
        if not text.strip():
            raise ValueError(f"empty extract: {path}")
        metadata = _parse_header(text, self.policy)
        missing = [key for key in REQUIRED_FIELDS if not metadata.get(key)]
        if missing:
            raise ValueError(f"missing header fields {missing} in {path}")
        title = metadata.get("title") or _first_heading(text, self.policy)
        if not title:
            raise ValueError(f"missing title and heading in {path}")
        metadata["title"] = title
        blocks = segment_blocks(text, self.policy)
        annotate_blocks(blocks, metadata["record_id"], self.policy)
        return Record(path=path, title=title, metadata=metadata, blocks=blocks)


def _extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def segment_blocks(text: str, policy: AnnotationPolicy | None = None) -> list[Block]:
    """Split on the document's own numbered headings.

    Content that follows a thematic break without a heading becomes its own
    unheaded block, which is how residue is found without naming it.
    """
    policy = policy or default_policy()
    heading_re = re.compile(policy.section_heading)
    break_re = re.compile(policy.thematic_break)
    furniture = [re.compile(pattern) for pattern in policy.page_furniture]

    segments: list[dict] = []
    current: dict | None = None
    seen_heading = False
    offset = 0

    for raw in text.splitlines(keepends=True):
        start, offset = offset, offset + len(raw)
        line = raw.strip()
        if not line or any(f.match(line) for f in furniture):
            continue
        heading = heading_re.match(line)
        if heading:
            seen_heading = True
            current = {"section": heading.group(1), "heading": line, "lines": [], "start": start}
            segments.append(current)
            continue
        if break_re.match(line):
            current = {"section": None, "heading": "", "lines": [], "start": start}
            segments.append(current)
            continue
        if not seen_heading:
            continue  # front matter; the header parser already owns it
        if current is None:
            current = {"section": None, "heading": "", "lines": [], "start": start}
            segments.append(current)
        current["lines"].append(line)
        current["end"] = offset

    blocks: list[Block] = []
    for segment in segments:
        body = "\n".join(segment["lines"]).strip()
        if not body:
            continue
        text_parts = [segment["heading"], body] if segment["heading"] else [body]
        blocks.append(
            Block(
                section=segment["section"],
                heading=segment["heading"],
                text="\n".join(text_parts),
                start=segment["start"],
                end=segment.get("end", segment["start"]),
            )
        )
    return blocks


def _header_block(text: str, policy: AnnotationPolicy) -> str:
    match = re.search(policy.section_heading, text, flags=re.MULTILINE)
    return text[: match.start()] if match else text[:800]


def _parse_header(text: str, policy: AnnotationPolicy | None = None) -> dict[str, str]:
    policy = policy or default_policy()
    text = _header_block(text, policy)
    found: dict[str, str] = {}
    for key in HEADER_KEYS:
        colon = re.search(
            rf"(?:^|\n)\s*{re.escape(key)}\s*:\s*(\S[^\n]*)",
            text,
            flags=re.IGNORECASE,
        )
        if colon:
            found[key] = colon.group(1).strip()
            continue
        flat = re.search(
            rf"(?:^|\n)\s*{re.escape(key)}\s+(\S[^\n]*)",
            text,
            flags=re.IGNORECASE,
        )
        if flat:
            found[key] = flat.group(1).strip()
    return found


def _first_heading(text: str, policy: AnnotationPolicy | None = None) -> str:
    policy = policy or default_policy()
    furniture = [re.compile(pattern) for pattern in policy.page_furniture]
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if not stripped or "|" in stripped:
            continue
        if any(f.match(stripped) for f in furniture):
            continue
        if HEADER_LINE.match(stripped):
            continue
        return stripped
    return ""
