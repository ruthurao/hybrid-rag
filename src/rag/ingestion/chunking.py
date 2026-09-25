from __future__ import annotations

import re
from typing import Iterable

from src.rag.config import Settings, default_settings
from src.rag.models import ATOMIC_TYPES, Block, Chunk, Record

LINEAGE_FIELDS = (
    "doc_id",
    "record_id",
    "family",
    "version",
    "status",
    "effective_date",
    "superseded_by",
)


class HeadingChunker:
    """One chunk per numbered section.

    Sections are already the author's own unit of meaning, so there is nothing
    to merge and no overlap: overlap would copy the account codes out of the
    coding table and into the travel prose that deliberately omits them.
    """

    name = "heading-split"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings()

    def chunk(self, record: Record, ingest_run_id: str, embedding_model: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for block in indexable(record.blocks, self.settings.index_min_rank):
            base = {
                **{field: record.metadata.get(field, "") for field in LINEAGE_FIELDS},
                "title": record.title,
                "section": block.section,
                "heading": block.heading,
                "content_type": block.content_type,
                "authority": block.authority,
                "authority_rank": block.authority_rank,
                "authority_reason": block.authority_reason,
                "chunker": self.name,
                "ingest_run_id": ingest_run_id,
                "embedding_model": embedding_model,
            }
            record_id = record.metadata["record_id"]
            for part, text in enumerate(self._split(block), start=1):
                suffix = "" if part == 1 else f"#part-{part}"
                chunks.append(
                    Chunk(
                        chunk_id=f"{record_id}#{block.section}{suffix}",
                        text=text,
                        metadata={**base, "part": part},
                    )
                )
        return chunks

    def _split(self, block: Block) -> list[str]:
        if block.content_type in ATOMIC_TYPES:
            return [block.text]
        return split_on_sentences(block.text, self.settings.max_chunk_chars)


def indexable(blocks: Iterable[Block], min_rank: int) -> list[Block]:
    """Blocks allowed into the store.

    Untrusted content is dropped here rather than filtered at query time, so
    personal data found in a document is never written to disk.
    """
    return [b for b in blocks if b.authority_rank >= min_rank and b.section]


def split_on_sentences(text: str, budget: int) -> list[str]:
    if len(text) <= budget:
        return [text]
    parts: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > budget:
            parts.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts
