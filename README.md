# Hybrid RAG — policy Q&A

Internal Q&A for finance staff. Answers are grounded in **current** AP, expense, and month-end close policy, with citations. A superseded AP handbook stays in the index so diagnosis can find it; live answers must not use it.

`main` is the submission tip: corpus, pipeline, tests, CI, and these docs. `docs/living` is the docs-only branch.

## Corpus

Index the four PDFs in [`corpus/`](corpus/). Do not also index the `.md` twins.

| File | Status | Role |
| --- | --- | --- |
| `ap-us-0001-v1.0.pdf` | `replaced` | Plant: AP-5.1 **$7,500**, 45-day pay |
| `ap-us-0001-v2.0.pdf` | `current` | Live AP: AP-5.1 **$10,000**, 30-day pay |
| `exp-us-0001-v1.0.pdf` | `current` | Expenses; title from H1; EXP-4.1 $75/meal |
| `mec-us-0001-v1.0.pdf` | `current` | `6100` only in MEC-5.1 table |

See [docs/ingest.md](docs/ingest.md) for the ingest contract and [docs/prd.md](docs/prd.md) for the product spec.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Logger smoke:

```bash
python -c "from src.rag.logging import configure_logging, get_logger; configure_logging(); get_logger(ingest_run_id='smoke').info('ingest.start')"
```

Quick loop — screenshot the closer sentence winning:

```bash
python scripts/minimal_loop.py
```

## Commands

| Phase | Command | Notes |
| --- | --- | --- |
| 2 | `python scripts/minimal_loop.py` | Two-sentence MiniLM retrieve. Screenshot for 7 pts. |
| 5 | `python scripts/ingest.py` | Parse, chunk, embed, upsert four PDFs. |
| 6 | `python scripts/ask.py "What invoice amount needs finance manager approval?"` | Live filter `status=current`. |
| 6 | `python scripts/ask.py --scope diagnosis "What invoice amount needs finance manager approval?"` | Part 6; v1 $7,500 can appear. |
| 7 | `python scripts/demo_hybrid.py` | Vector-only vs RRF on `6100`. Screenshot for 12 pts. |
| 9 | `pytest` | 8-case harness + diagnosis. |
| 10 | GitHub Actions `ci.yml` | Same pytest. |

How to read a `query_trace`: [docs/observability.md](docs/observability.md).
