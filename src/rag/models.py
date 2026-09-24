from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

UNASSIGNED_AUTHORITY = "untrusted"
UNASSIGNED_RANK = 0

# Shape of a block's content. UNTYPED means nobody has looked yet, which is
# not the same answer as PROSE and must not be spelled the same way.
UNTYPED = "untyped"
PROSE = "prose"
TABLE = "table"
FAQ = "faq"
IMAGE_TEXT = "image_text"
ATOMIC_TYPES = (TABLE, FAQ)


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
    content_type: str = UNTYPED
    authority: str = UNASSIGNED_AUTHORITY
    authority_rank: int = UNASSIGNED_RANK
    authority_reason: str = "unassigned"
    contains_pii: bool = False
    pii_kinds: tuple[str, ...] = ()


PAGE = "page"
INSET = "inset"


@dataclass
class ImageAsset:
    """An embedded image and what we managed to read from it.

    One asset per distinct image, however many pages it is placed on.
    text stays None when nothing was read, and reason says why. role says
    whether the image carries its page or merely sits on it, which decides
    whether the text it holds is part of the document or an annotation of it.
    """

    digest: str
    pages: tuple[int, ...]
    width: int
    height: int
    role: str = INSET
    text: str | None = None
    reason: str = "ocr_disabled"


@dataclass
class Record:
    path: Path
    title: str
    metadata: dict[str, Any]
    blocks: list[Block] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)


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


@dataclass
class QueryTrace:
    request_id: str
    ingest_run_id: str
    embedding_model: str
    pipeline_id: str
    scope: str
    cache_hit: bool
    filter: dict
    k: int
    chunk_ids: list[str]
    scores: list[float]
    sources: list[str]
    latencies_ms: dict[str, float]


@dataclass
class Answer:
    text: str
    citations: list[dict]
    query_trace: QueryTrace
