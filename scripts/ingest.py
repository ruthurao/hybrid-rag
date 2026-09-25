from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.config import default_settings  # noqa: E402
from src.rag.ingestion.index import build_index  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402


def main() -> None:
    configure_logging()
    settings = default_settings(ROOT)
    run_id, _, chunks = build_index(settings=settings)
    print(f"ingest_run_id={run_id} chunks={len(chunks)} chroma={settings.chroma_dir}")


if __name__ == "__main__":
    main()
