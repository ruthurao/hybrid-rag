from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.rag.models import Record


class ParserAdapter(Protocol):
    def parse(self, path: Path) -> Record:
        """PDF path → record with lineage metadata. Fail loud on empty text or missing status."""
