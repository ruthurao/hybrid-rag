# Observability

Lab-sized. JSON lines on stderr via `structlog`. Every answer also returns a `query_trace`. No Phoenix, Langfuse, or hosted SaaS.

Never log full chunk text. Never log the MEC SharePoint/PII paste (`priya.shah`, `EE-4419`, last-four).

Authority is logged as **counts per level**, never as payload. An unexpected distribution is the early warning that a derivation rule misfired and live answers are quietly missing content.

## Logger

`src/rag/logging.py`

- `configure_logging()` — JSON to stderr (`timestamp`, `level`, `event`, …)
- `get_logger(**bind)` — bind `ingest_run_id` (ingest) or `request_id` (ask)

Smoke:

```bash
python -c "from src.rag.logging import configure_logging, get_logger; configure_logging(); get_logger(ingest_run_id='smoke').info('ingest.start')"
```

## Ingest events

| Event | Fields |
| --- | --- |
| `ingest.start` | `ingest_run_id`, `pdf_count`, `ocr_enabled` |
| `ingest.asset` | `record_id`, `digest`, `pages`, `role`, `read`, `reason` (no image bytes) |
| `ingest.record` | `record_id`, `status`, `block_count`, `authority` (counts), `pii_blocks` (count), `image_count` |
| `ingest.chunk` | `record_id`, `chunk_count`, `content_types`, `excluded`, `excluded_reasons` |
| `ingest.upsert` | `chunk_count`, `embedding_model`, `store_count` |
| `ingest.done` | `record_count`, `chunk_count` |

`excluded` is the untrusted drop. Reasons are `authority_reason` values (this corpus: `outside_heading_hierarchy`).

## Query events

| Event | Fields |
| --- | --- |
| `query.start` | `request_id`, `scope`, `pipeline_id` |
| `query.hybrid` | `vector_ids`, `keyword_ids`, `fused_ids` |
| `query.rerank` | `model`, `hit_count`, `chunk_ids`, `scores` |
| `query.retrieve` | `hit_count`, `chunk_ids`, `scores` |
| `query.generate` | `citation_count`, `empty` |
| `query.done` | `cache_hit`, `citation_count` |

`scope` is `live`, `diagnosis`, or `compare`. The question string may be logged. Retrieved **text** must not.

`pipeline_id` is `rerank-v2`. Bump it when retrieve or generate changes so an old cache row cannot be served.

## `query_trace` (on every answer)

```json
{
  "request_id": "…",
  "ingest_run_id": "…",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "pipeline_id": "rerank-v2",
  "scope": "live",
  "cache_hit": false,
  "filter": {
    "$and": [
      {"status": {"$eq": "current"}},
      {"authority_rank": {"$gte": 2}}
    ]
  },
  "k": 10,
  "chunk_ids": ["ap-us-0001-v2.0#AP-5.1"],
  "scores": [8.42],
  "sources": ["rerank"],
  "latencies_ms": {
    "retrieve": 0,
    "generate": 0,
    "total": 0
  }
}
```

Live filter is `status=current` **and** `authority_rank >= 2`. Diagnosis and compare keep the rank floor and drop the status clause.

## How to read a trace

1. Check `scope` / `filter`. Live $10,000 vs diagnosis $7,500 is a filter difference, not a model failure.
2. `query.hybrid`: for `6100`, keyword should list the MEC-5.1 table; vector often lists MEC-8.2 travel prose; fused should promote the table.
3. `chunk_ids` after rerank are what generation saw (3–4).
4. `ingest_run_id` tells you which index built the answer. Re-ingest changes it.
