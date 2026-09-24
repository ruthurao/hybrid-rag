from __future__ import annotations

from dataclasses import dataclass, field
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
    live_authority_rank: int = 2


def default_settings(root: Path | None = None) -> Settings:
    base = root or Path.cwd()
    return Settings(
        corpus_dir=base / "corpus",
        chroma_dir=base / "chroma",
    )


@dataclass(frozen=True)
class AnnotationPolicy:
    """Declarative rules for segmentation and authority.

    These are patterns, not instances: a new document is a config change,
    not a code change. Moves to YAML unchanged if the catalog grows.
    """

    section_heading: str = r"^([A-Z]{2,4}-\d+\.\d+)\b\s*(.*)$"
    thematic_break: str = r"^-{3,}$"
    page_furniture: tuple[str, ...] = (
        r"^Page\s+\d+$",
        r"^\S+-v\d+\.\d+\s*\|\s*status:\s*\w+$",
    )
    non_binding_phrases: tuple[str, ...] = (
        "do not replace",
        "does not replace",
        "not part of this procedure",
        "not part of this document",
        "for illustration",
        "example only",
        "non-binding",
    )
    faq_markers: tuple[str, ...] = ("Q:", "A:")
    pii_patterns: tuple[tuple[str, str], ...] = (
        ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        ("employee_id", r"\bEE-\d+\b"),
        ("card_last_four", r"last four\s+\d{3,4}"),
    )
    # (record_id, section) -> authority level. Beats every derived rule.
    overrides: dict[tuple[str, str], str] = field(default_factory=dict)


def default_policy() -> AnnotationPolicy:
    return AnnotationPolicy()
