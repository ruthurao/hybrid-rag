from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.rag.adapters.parser import PdfParser
from src.rag.authority import authority_counts
from src.rag.logging import get_logger
from src.rag.models import Record
from src.rag.ports.parser import ParserAdapter


def ingest_pdfs(
    corpus_dir: Path,
    parser: ParserAdapter | None = None,
    ingest_run_id: str | None = None,
) -> tuple[str, list[Record]]:
    """Parse every PDF in corpus_dir. Does not chunk, embed, or filter status."""
    parser = parser or PdfParser()
    run_id = ingest_run_id or uuid4().hex
    pdfs = sorted(corpus_dir.glob("*.pdf"))
    log = get_logger(ingest_run_id=run_id)
    log.info("ingest.start", pdf_count=len(pdfs))
    records: list[Record] = []
    for path in pdfs:
        record = parser.parse(path)
        records.append(record)
        counts = authority_counts(record.blocks)
        log.info(
            "ingest.record",
            record_id=record.metadata["record_id"],
            status=record.metadata["status"],
            block_count=len(record.blocks),
            authority=counts,
            pii_blocks=sum(1 for block in record.blocks if block.contains_pii),
        )
    log.info("ingest.done", record_count=len(records), chunk_count=0)
    return run_id, records
