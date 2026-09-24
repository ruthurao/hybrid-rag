from __future__ import annotations

from collections import Counter
from pathlib import Path
from uuid import uuid4

from src.rag.adapters.ocr import RapidOcrAdapter
from src.rag.adapters.parser import PdfParser
from src.rag.authority import authority_counts
from src.rag.chunking import HeadingChunker
from src.rag.config import Settings, default_settings
from src.rag.logging import get_logger
from src.rag.models import Chunk, Record
from src.rag.ports.chunking import ChunkingStrategy
from src.rag.ports.parser import ParserAdapter


def _ocr_for(settings: Settings) -> RapidOcrAdapter | None:
    if not settings.ocr_enabled:
        return None
    return RapidOcrAdapter(
        min_confidence=settings.ocr_min_confidence,
        page_text_threshold=settings.ocr_page_text_threshold,
        page_aspect_tolerance=settings.ocr_page_aspect_tolerance,
    )


def ingest_pdfs(
    corpus_dir: Path,
    parser: ParserAdapter | None = None,
    ingest_run_id: str | None = None,
    chunker: ChunkingStrategy | None = None,
    settings: Settings | None = None,
) -> tuple[str, list[Record], list[Chunk]]:
    """Parse and chunk every PDF in corpus_dir. Does not embed or store."""
    settings = settings or default_settings()
    parser = parser or PdfParser(ocr=_ocr_for(settings))
    chunker = chunker or HeadingChunker(settings)
    run_id = ingest_run_id or uuid4().hex
    pdfs = sorted(corpus_dir.glob("*.pdf"))
    log = get_logger(ingest_run_id=run_id)
    log.info("ingest.start", pdf_count=len(pdfs), ocr_enabled=settings.ocr_enabled)

    records: list[Record] = []
    chunks: list[Chunk] = []
    for path in pdfs:
        record = parser.parse(path)
        records.append(record)
        record_id = record.metadata["record_id"]

        for asset in record.images:
            log.info(
                "ingest.asset",
                record_id=record_id,
                digest=asset.digest,
                pages=list(asset.pages),
                size=[asset.width, asset.height],
                role=asset.role,
                read=asset.text is not None,
                reason=asset.reason,
            )

        record_chunks = chunker.chunk(record, run_id, settings.embedding_model)
        chunks.extend(record_chunks)
        dropped = [
            block
            for block in record.blocks
            if block.authority_rank < settings.index_min_rank
        ]
        log.info(
            "ingest.record",
            record_id=record_id,
            status=record.metadata["status"],
            block_count=len(record.blocks),
            authority=authority_counts(record.blocks),
            pii_blocks=sum(1 for block in record.blocks if block.contains_pii),
            image_count=len(record.images),
        )
        log.info(
            "ingest.chunk",
            record_id=record_id,
            chunk_count=len(record_chunks),
            content_types=dict(Counter(c.metadata["content_type"] for c in record_chunks)),
            excluded=len(dropped),
            excluded_reasons=dict(Counter(block.authority_reason for block in dropped)),
        )

    log.info("ingest.done", record_count=len(records), chunk_count=len(chunks))
    return run_id, records, chunks
