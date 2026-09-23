# Observability

Lab-sized. JSON lines on stderr via `structlog`. Every answer also returns a `query_trace`. No Phoenix, Langfuse, or hosted SaaS.

Never log full chunk text. Never log the MEC SharePoint/PII paste (`priya.shah`, `EE-4419`, last-four).

## Logger

`src/rag/logging.py`

- `configure_logging()` — JSON to stderr (`timestamp`, `level`, `event`, …)
- `get_logger(**bind)` — bind `ingest_run_id` (ingest) or `request_id` (ask)

Smoke (Phase 1):

```bash
python -c "from src.rag.logging import configure_logging, get_logger; configure_logging(); get_logger(ingest_run_id='smoke').info('ingest.start', event='ingest.start')"
```

## Ingest events

| Event | Phase | Fields |
| --- | --- | --- |
| `ingest.start` | 3 | `ingest_run_id`, `pdf_count` |
| `ingest.record` | 3 | `record_id`, `status`, `junk_tagged` (bool only) |
| `ingest.chunk` | 4 | `record_id`, `section`, `chunk_id`, `content_type` |
| `ingest.upsert` | 5 | `chunk_count`, `embedding_model` |
| `ingest.done` | 3 | `record_count`, `chunk_count` |

## Query events

| Event | Phase | Fields |
| --- | --- | --- |
| `query.start` | 6 | `request_id`, `scope` |
| `query.retrieve` | 6 | `vector_ids`, `k` |
| `query.hybrid` | 7 | `vector_ids`, `keyword_ids`, `fused_ids` |
| `query.rerank` | 8 | `in_ids`, `out_ids`, `scores` |
| `query.generate` | 6 | `cited` (`doc_id`/`version`/`section` only) |
| `query.done` | 6 | `latency_ms` |

The question string may be logged. Retrieved **text** must not.

## `query_trace` (on every answer)

```json
{
  "request_id": "…",
  "scope": "current",
  "filter": {"status": "current"},
  "chunk_ids": ["ap-us-0001-v2.0::AP-5.1"],
  "scores": [0.81],
  "vector_ids": [],
  "keyword_ids": [],
  "fused_ids": [],
  "latencies_ms": {
    "retrieve": 0,
    "hybrid": 0,
    "rerank": 0,
    "generate": 0,
    "total": 0
  },
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "ingest_run_id": "…"
}
```

`filter` is `{"status": "current"}` in live mode and `{}` in diagnosis/history.

## How to read a trace

1. Check `scope` / `filter`. Live $10,000 vs diagnosis $7,500 is a filter difference, not a model failure.
2. `vector_ids` vs `keyword_ids` vs `fused_ids` — for `6100`, keyword should list the MEC-5.1 table; vector often lists MEC-8.2 travel prose; fused should promote the table.
3. `chunk_ids` after rerank are what generation saw (3–4).
4. `ingest_run_id` tells you which index built the answer. Re-ingest changes it.
