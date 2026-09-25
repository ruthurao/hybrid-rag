# Ingest contract

Ingest reads **PDFs only** from `corpus/`. Markdown twins are source notes, not index inputs.

Query filters `status`. Ingest does **not**. Both AP versions are stored so diagnosis can retrieve v1.

## Files

| PDF | `record_id` | `status` | `superseded_by` | Notes |
| --- | --- | --- | --- | --- |
| `ap-us-0001-v1.0.pdf` | `ap-us-0001-v1.0` | `replaced` | `ap-us-0001-v2.0` | Plant. AP-5.1 $7,500. AP-6.1 45 days. |
| `ap-us-0001-v2.0.pdf` | `ap-us-0001-v2.0` | `current` | `none` | Live AP. AP-5.1 $10,000. AP-6.1 30 days. |
| `exp-us-0001-v1.0.pdf` | `exp-us-0001-v1.0` | `current` | `none` | No `title` field. Title = first `#` heading. |
| `mec-us-0001-v1.0.pdf` | `mec-us-0001-v1.0` | `current` | `none` | Export residue after the separator is `untrusted`, not the plant. |

Empty extract or missing `status` fails ingest (loud).

## Header lineage

The first markdown field table is the source of truth. Required on every record:

`doc_id`, `record_id`, `family`, `version`, `status`, `effective_date`, `superseded_by`

If `title` is absent, set it from the H1 (expense handbook).

`superseded_by` and `effective_date` are stamped on every chunk. Query does **not** walk the pointer or apply `as_of`. Live vs diagnosis is a `status` filter.

## Authority

Authority answers “is this a rule?”. Lineage (`status`, `effective_date`, `superseded_by`) answers “is the rule in force?”. They are separate axes, and the plant proves why: AP v1 `AP-5.1` is a genuine rule (`normative`) that is out of date (`replaced`).

| `authority` | `authority_rank` | What it is |
| --- | --- | --- |
| `normative` | 3 | Numbered procedure sections and the tables they own |
| `advisory` | 2 | FAQ, notes, examples — supports an answer, is not the rule |
| `untrusted` | 0 | Content outside the document’s own heading hierarchy |

The rank is numeric because Chroma filters with `{"authority_rank": {"$gte": 2}}`; string levels give no ordering.

Derivation is structural, evaluated in order, and every block records an `authority_reason`:

1. Catalog override for `(record_id, section)` → `catalog_override`
2. No section heading (sits outside the hierarchy) → `outside_heading_hierarchy`
3. Self-declares non-binding, or Q/A shape → `self_declared_non_binding` / `faq_shape`
4. Under a numbered heading matching the scheme → `numbered_section`

The close-export paste is caught by rule 2 — it follows a thematic break under no heading — not by matching its ticket id. Patterns live in `AnnotationPolicy` in `src/rag/config.py`.

Blocks default to `untrusted` when unannotated. `index_min_rank` is 2, so untrusted blocks are **dropped at chunk time**. They stay on the `Record` for ingest logs. They never reach Chroma, retrieval, or the prompt. There is no audit scope that brings them back.

`contains_pii` is a separate flag (email, `EE-\d+`, card last-four). Job IDs such as `US-0984` are not matched. PII on this corpus lives only in the untrusted export paste, so dropping that paste is what keeps personal data off disk.

Current distribution: **46 blocks** (43 normative, 1 advisory `EXP-8.1`, 2 untrusted on the close export). **44 chunks** are stored. The two untrusted blocks are the only PII.

## Images / OCR

`ocr_enabled` defaults **on**. Inset figures (the close coding card) may be read; that text is **not** split into its own section. A heading inside an inset must not mint a second `MEC-5.1`. Page-shaped scans with no text layer become the page text.

## Chunking

One strategy: heading-split.

- Split on `##` headings (`AP-5.1`, `EXP-4.1`, `MEC-5.1`).
- A markdown table stays inside its section. MEC-5.1 = intro + the whole account table. `6100` must not appear in MEC-8.2.
- A section over `max_chunk_chars` (1000) splits on sentences. Extra parts use `chunk_id` suffix `#part-N`. No overlap (overlap would leak `6100` into travel prose).
- EXP-8.1 → `content_type=faq`. Sections with a table → `table`. Else `prose`. Untrusted never becomes a chunk, so `export_junk` is not an indexed type.

## Upsert

- `chunk_id` = `{record_id}#{section}` (plus `#part-N` if split).
- Stamp `embedding_model`, `ingest_run_id`, `authority`, and lineage on every chunk.
- Re-run ingest upserts the same ids. It does not duplicate vectors.
- Do not key by `doc_id` alone or v2 overwrites v1.

```bash
python scripts/ingest.py
```

## Live vs diagnosis

| Mode | How | Status filter | Authority filter | Result |
| --- | --- | --- | --- | --- |
| Live (default) | `ask.py` | `status=current` | `rank >= 2` | $10,000 from v2 AP-5.1 |
| Diagnosis | `ask.py --scope diagnosis` | none | `rank >= 2` | $7,500 from v1 AP-5.1 can appear |
| Compare | `--scope compare` or “what changed” | none | `rank >= 2` | both versions, grouped |

There is no audit mode. Diagnosis relaxes lineage only. The authority floor stays, and untrusted was never indexed, so the export paste cannot surface.
