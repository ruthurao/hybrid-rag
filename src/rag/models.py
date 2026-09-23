from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Record:
    path: Path
    text: str
    body: str
    title: str
    metadata: dict[str, Any]
    junk: str | None = None
    junk_tagged: bool = False


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
