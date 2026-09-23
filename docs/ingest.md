# Ingest contract

Ingest reads **PDFs only** from `corpus/`. Markdown twins are source notes, not index inputs.

Query filters `status`. Ingest does **not**. Both AP versions are stored so diagnosis can retrieve v1.

## Files

| PDF | `record_id` | `status` | `superseded_by` | Notes |
| --- | --- | --- | --- | --- |
| `ap-us-0001-v1.0.pdf` | `ap-us-0001-v1.0` | `replaced` | `ap-us-0001-v2.0` | Plant. AP-5.1 $7,500. AP-6.1 45 days. |
| `ap-us-0001-v2.0.pdf` | `ap-us-0001-v2.0` | `current` | `none` | Live AP. AP-5.1 $10,000. AP-6.1 30 days. |
| `exp-us-0001-v1.0.pdf` | `exp-us-0001-v1.0` | `current` | `none` | No `title` field. Title = first `#` heading. |
| `mec-us-0001-v1.0.pdf` | `mec-us-0001-v1.0` | `current` | `none` | Junk after the procedure separator is tagged, not the plant. |

Empty extract or missing `status` fails ingest (loud).

## Header lineage

The first markdown field table is the source of truth. Required on every record:

`doc_id`, `record_id`, `family`, `version`, `status`, `effective_date`, `superseded_by`

If `title` is absent, set it from the H1 (expense handbook).

## Junk

Text after “not part of this procedure” / the SharePoint-JIRA paste is tagged `content_type=export_junk`, `contains_pii=true`. It is **not** chunked, embedded, or sent to generation. Do not log the paste.

## Chunking (Phase 4)

One strategy: `section`.

- Split on `##` headings (`AP-5.1`, `EXP-4.1`, `MEC-5.1`).
- A markdown table stays inside its section. MEC-5.1 = intro sentence + the whole account table. `6100` / `6100-TRAVEL` must not appear in MEC-8.2.
- Overlap only when a section exceeds `max_section_chars`. Child ids are `record_id` + section + content hash.
- EXP-8.1 → `content_type=faq`. Sections with a table → `table`. Else `prose`.

## Upsert (Phase 5)

- `chunk_id` = `{record_id}::{section}` (plus `::{text_sha256[:8]}` if split).
- Stamp `embedding_model` and `ingest_run_id` on every chunk.
- Re-run ingest upserts the same ids. It does not duplicate vectors.
- Do not key by `doc_id` alone or v2 overwrites v1.

```bash
python scripts/ingest.py
```

## Live vs diagnosis

| Mode | In the index | At query |
| --- | --- | --- |
| Live (default) | v1 + v2 + expense + close | `status=current` → $10,000 |
| Diagnosis / history | same | no current-only filter → $7,500 from v1 AP-5.1 can appear |
