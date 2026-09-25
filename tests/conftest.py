from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.ingestion.ingest import ingest_pdfs

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture(scope="session")
def ingested():
    """Ingest the corpus once. OCR loads a model, so repeating it is slow."""
    return ingest_pdfs(CORPUS, ingest_run_id="test-run")


@pytest.fixture(scope="session")
def records(ingested):
    return {record.metadata["record_id"]: record for record in ingested[1]}


@pytest.fixture(scope="session")
def chunks(ingested):
    return ingested[2]


@pytest.fixture
def parse_log_lines():
    def _parse(stderr: str) -> list[dict]:
        lines = []
        for raw in stderr.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return lines

    return _parse
