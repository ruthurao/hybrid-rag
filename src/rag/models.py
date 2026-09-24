from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

UNASSIGNED_AUTHORITY = "untrusted"
UNASSIGNED_RANK = 0


@dataclass
class Block:
    """One segment of a document, with its position and its annotations.

    Authority defaults to untrusted so a block that never reaches the
    annotator is excluded rather than silently admitted.
    """

    section: str | None
    heading: str
    text: str
    start: int
    end: int
    content_type: str = "prose"
    authority: str = UNASSIGNED_AUTHORITY
    authority_rank: int = UNASSIGNED_RANK
    authority_reason: str = "unassigned"
    contains_pii: bool = False
    pii_kinds: tuple[str, ...] = ()


@dataclass
class Record:
    path: Path
    title: str
    metadata: dict[str, Any]
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Chunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass
class Hit:
    chunk: Chunk
    score: float
    source: str = "vector"
