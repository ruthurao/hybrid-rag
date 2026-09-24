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

Empty extract or missing `status` fails ingest (loud). Phase 3 stops at records: four PDFs parsed and segmented into annotated blocks, no chunks yet.

## Header lineage

The first markdown field table is the source of truth. Required on every record:

`doc_id`, `record_id`, `family`, `version`, `status`, `effective_date`, `superseded_by`

If `title` is absent, set it from the H1 (expense handbook).

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

The close-export paste is caught by rule 2 — it follows a thematic break under no heading — not by matching its ticket id. A different document with a different ticket is caught by the same rule. Patterns live in `AnnotationPolicy` in `src/rag/config.py`, so a fifth document is a config row rather than a code change.

Blocks default to `untrusted` when unannotated, so a gap in the pipeline excludes content instead of admitting it.

`contains_pii` is a separate flag with its own detectors (email, `EE-\d+`, card last-four). Job IDs such as `US-0984` are roster references and are deliberately not matched. A normative section can legitimately contain a name, so PII drives redaction and the do-not-embed rule, never authority.

Nothing is deleted. Untrusted content keeps its block and offsets for audit; it is excluded at embed, retrieval, and prompt time.

Current distribution: 45 blocks, of which 43 normative, 1 advisory (`EXP-8.1`), 1 untrusted (the close export residue, which is also the only block with PII).

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

| Mode | Status filter | Authority filter | Result |
| --- | --- | --- | --- |
| Live (default) | current as-of today | `rank >= 2` | $10,000 from v2 AP-5.1 |
| History / diagnosis | none | `rank >= 2` | $7,500 from v1 AP-5.1 can appear |
| Audit (explicit) | none | none | Untrusted residue retrievable for the DQ writeup |

Diagnosis relaxes lineage only. The authority floor stays, so the export paste never surfaces as an answer. At generation, `normative` is citable as policy, `advisory` must be labelled as guidance, and `untrusted` never enters the prompt — which is also how directives planted inside documents are refused.
