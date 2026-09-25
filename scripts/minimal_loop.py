from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.logging import configure_logging, get_logger  # noqa: E402
from src.rag.retrieval.minimal_loop import QUERY, SENTENCE_A, SENTENCE_B, run_minimal_loop  # noqa: E402


def main() -> None:
    configure_logging()
    log = get_logger(request_id="minimal-loop")
    store = ChromaVectorStore(ROOT / "chroma" / "minimal", "minimal_loop")
    ranked = run_minimal_loop(store=store, use_minilm=True)
    print("Query:", QUERY)
    print("1.", ranked[0])
    print("2.", ranked[1])
    print("Closer sentence wins:", ranked[0] == SENTENCE_A)
    print("Decoy:", SENTENCE_B)
    log.info("minimal.done", winner=ranked[0][:48])


if __name__ == "__main__":
    main()
