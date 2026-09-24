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
    max_chunk_chars: int = 1000
    # Below this rank a block never reaches the store. Untrusted content is
    # reported at ingest and dropped, so personal data is not held at rest.
    index_min_rank: int = 2
    vector_top_k: int = 10
    keyword_top_k: int = 10
    rrf_k: int = 60
    rerank_top_n: int = 4
    live_status: str = "current"
    live_authority_rank: int = 2
    # Bump when the miss path changes (hybrid, rerank, a new generator)
    # so a Phase 6 answer cannot be served as a Phase 7 hit.
    pipeline_id: str = "rerank-v1"
    compare_k_per_version: int = 5
    # Phrases that mean "retrieve every version", not "current only".
    # "how does" is omitted: it matches ordinary how-to questions.
    comparison_signals: tuple[str, ...] = (
        "difference between",
        "compare",
        "compared to",
        " vs ",
        "versus",
        "changed from",
        "what changed",
        "old vs new",
        "old and new",
        "previous vs",
    )
    ocr_enabled: bool = True
    ocr_min_confidence: float = 0.5
    # A page with less text than this has no usable text layer, and an image
    # shaped like the sheet on such a page is the page rather than an inset.
    ocr_page_text_threshold: int = 50
    ocr_page_aspect_tolerance: float = 0.15


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

    # A heading carries a capitalised title and no sentence punctuation. A
    # cross-reference that wraps onto its own line ("MEC-7.1 stay with the
    # close record.") looks like a heading without this and steals the text.
    section_heading: str = r"^([A-Z]{2,4}-\d+\.\d+)[ \t]+([A-Z][^.\n]*)$"
    section_id: str = r"^[A-Z]{2,4}-\d+\.\d+$"
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
    # A grid row carries cells, not a sentence: several fields and none of the
    # punctuation prose runs on. Wrapped prose lines otherwise read as rows.
    table_row: str = r"^\S+(?:[ \t]+\S+){2,}$"
    table_row_punctuation: str = r"[.,;]"
    min_table_rows: int = 3
    pii_patterns: tuple[tuple[str, str], ...] = (
        ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        ("employee_id", r"\bEE-\d+\b"),
        ("card_last_four", r"last four\s+\d{3,4}"),
    )
    # (record_id, section) -> authority level. Beats every derived rule.
    overrides: dict[tuple[str, str], str] = field(default_factory=dict)


def default_policy() -> AnnotationPolicy:
    return AnnotationPolicy()
