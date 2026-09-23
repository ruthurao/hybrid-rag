from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    corpus_dir: Path
    chroma_dir: Path
    collection_name: str = "policy_chunks"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    max_section_chars: int = 4000
    overlap_chars: int = 200
    vector_top_k: int = 10
    keyword_top_k: int = 10
    rrf_k: int = 60
    rerank_top_n: int = 4
    live_status: str = "current"


def default_settings(root: Path | None = None) -> Settings:
    base = root or Path.cwd()
    return Settings(
        corpus_dir=base / "corpus",
        chroma_dir=base / "chroma",
    )
