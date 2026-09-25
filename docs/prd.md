# PRD: Policy Q&A RAG System

## 1. Overview

**Product.** Internal Q&A for finance staff. They ask in plain language and get answers grounded in **current** policy (AP, expenses, month-end close), with citations. Stale or conflicting versions must not win by default.

**This release.** Graded lab on a locked 4-document corpus. Architecture is the first slice of a production system: adapters, lineage on every chunk, one chunker, hybrid + RRF + rerank.

**Non-goals for v1.** Multi-tenant auth, UI, live document sync, multi-language, hosted API, semantic query cache, three live chunkers, a dedicated “injection filter” product, `as_of` date resolution.

---

## 2. Problem

People search PDFs by hand. Superseded files do not disappear. A naive search cannot tell `current` from `replaced` and will hand a clerk the wrong approval amount. The system has to solve **retrieval quality and data trustworthiness together**.

The lab instance of that bug: `ap-us-0001-v1.0` (AP-5.1 **$7,500**, 45 days) sitting next to `ap-us-0001-v2.0` (AP-5.1 **$10,000**, 30 days).

---

## 3. Users

AP clerks, finance managers, employees filing expenses.

**Later (not this lab):** auditors asking what applied on a past date. That would be an `as_of` path on the same `ask()` entry point. Today, diagnosis is `--scope diagnosis`.

---

## 4. Corpus (locked)

Index **PDFs only**. Do not also index `.md` twins.

| Doc | Family | File | Status | Role |
| --- | --- | --- | --- | --- |
| AP v1.0 | `ap_payment_procedure` | `ap-us-0001-v1.0.pdf` | `replaced` | **Graded plant.** Same sections as v2. AP-5.1 $7,500. AP-6.1 45 days. |
| AP v2.0 | `ap_payment_procedure` | `ap-us-0001-v2.0.pdf` | `current` | Live AP. AP-5.1 $10,000. AP-6.1 30 days. Replaces v1.0. |
| Expense v1.0 | `expense_reimbursement_procedure` | `exp-us-0001-v1.0.pdf` | `current` | No version conflict. Title from H1 (no `title` field). `EXP-4.1` $75/meal. EXP-8.1 FAQ (Q/A). |
| Close v1.0 | `month_end_close_procedure` | `mec-us-0001-v1.0.pdf` | `current` | MEC-5.1 table is the **only** place `6100` / `6100-TRAVEL` appears. MEC-8.2 is travel prose (vector decoy). MEC-8.3 lock schedule. SharePoint/PII paste after `---` is **not** the plant. |

**Chunking (one strategy).** Split on `##`. Do not split a markdown table. No overlap. A long section splits on sentences (`#part-N`).

**Not the plant (do not diagnose these in Part 6):** missing expense `title` field, close coding-card image, Priya/JIRA paste, PDF+MD copies.

---

## 5. Goals and success metrics

| Goal | v1 metric |
| --- | --- |
| Correct live answers | `status=current` and `authority_rank >= 2`, unless diagnosis/compare |
| Retrieval | Hybrid + RRF beats vector-only on the travel-code query (`6100` + travel) |
| Eval | ≥8 fixed cases; recall + answer contains the gold fact |
| Trust | 100% of answers cite `doc_id` + `version` + `section` |
| Diagnosability | Wrong answer traces to source, retrieval, or generation — not “unknown” |
| IDs | `chunk_id` = `{record_id}#{section}`. Survives re-ingest |
| Extensibility | Swap parser / embedder / store / chunker without rewriting `ask()` |

---

## 6. Architecture (scale spine, thin v1)

Pipeline talks only to ports:

- `ParserAdapter` — PDF → text + blocks. OCR is **on** for insets and empty pages; inset text is not segmented into headings.
- `ChunkingStrategy` — one registered strategy (`heading-split`, table-atomic). Untrusted blocks never become chunks.
- `EmbeddingAdapter` — `all-MiniLM-L6-v2` in scripts; lexical bag-of-words in pytest. Stamp `embedding_model` on chunks.
- `VectorStoreAdapter` — Chroma in scripts; in-memory store in pytest. Upsert by `chunk_id`.

**Orchestration never imports sentence-transformers or Chroma types outside adapters.**

---

## 7. Functional requirements

### 7.1 Ingest

1. Parse each of the four PDFs. Header table is lineage source of truth (`doc_id`, `record_id`, `version`, `status`, `effective_date`, `superseded_by`).
2. Expense: if `title` missing, set title from first heading.
3. Close: text after “not part of this procedure” / JIRA block → `untrusted`, `contains_pii=true`. Dropped at chunk (`index_min_rank=2`). Not stored.
4. Empty extract → fail ingest (loud). Missing `status` → fail ingest.
5. Stamp `ingest_run_id` on every chunk. New ingest = new run id.

### 7.2 Chunk

1. Dispatch via registry; this lab always heading-split.
2. One chunk per `##` section. MEC-5.1 = intro + **whole table** (so `6100` cannot leak into 8.2).
3. Every chunk: lineage fields, `section`, `content_type` (`prose` \| `table` \| `faq`), `authority`, `authority_rank`, `embedding_model`, `ingest_run_id`.
4. `chunk_id` = `{record_id}#{section}`. Untrusted never upserts.

### 7.3 Embed and store

1. Embed every remaining chunk. Same `chunk_id` overwrites on re-ingest.
2. Upsert into one Chroma collection by `chunk_id`.
3. Do not key by `doc_id` alone.

### 7.4 Query

1. `ask(..., scope=)` → `live` (default), `diagnosis`, or `compare`.
   - **Live:** `status=current` and `authority_rank >= 2`.
   - **Diagnosis / `--scope diagnosis`:** rank floor only, so v1 can appear (Part 6).
   - **Compare:** `--scope compare`, or phrases like “what changed”. Intent overwrites the caller. Per-version retrieve, not reranked.
2. Embed the question with the same model used at ingest (MiniLM in scripts).
3. Vector ANN top-k **and** keyword retrieve (token overlap + IDF; codes like `6100` are boosted).
4. Fuse with **RRF**. Equal RRF scores break toward the keyword rank.
5. Cross-encoder rerank → 3–4 chunks (Identity reranker in pytest).
6. Untrusted never entered the store, so it cannot enter the prompt.

### 7.5 Trust / current resolution

Live is a metadata filter: `status=current` and `authority_rank >= 2`. `effective_date` and `superseded_by` are on the chunk and unused at query time. Diagnosis drops the status clause so AP-5.1 $7,500 can surface.

### 7.6 Generation

- Extractive: the answer is the retrieved chunk text. No model call.
- Cite every used source: `doc_id` + `version` + `section` (plus `record_id`, `status`, `authority` on the citation object).
- Compare groups current vs previous. Live never cites `replaced` AP.

### 7.7 Hybrid demo (12 pts)

Query like: *What is account code 6100 used for at travel close?*

- Vector-only: MEC-8.2 (travel prose) high; table low or missing (`6100` only in MEC-5.1).
- Keyword: `6100` ranks the table first (IDF + digit-token boost).
- Hybrid RRF: table chunk rises. Screenshot vector-only vs RRF.

Backup token if needed: `EXP-4.1`.

### 7.8 Evaluation and Part 6

- ≥8 pytest cases: retrieval recall (gold `record_id` + `section`) and answer contains the gold fact.
- One **executable** diagnosis test: question without current-only filter; $7,500 is attributed to `ap-us-0001-v1.0` AP-5.1, not to “the model failed.”
- Part 6 writeup uses that test, not Priya, not the image, not the FAQ.

### 7.9 Attribution

Every printed answer lists the sections used.

---

## 8. Non-functional

- Local-first: `pypdf` or `pdfplumber` + MiniLM + Chroma. Swappable via config.
- Each stage independently testable.
- Fail loud at ingest, not silent at query.
- SOLID/DRY via the four adapters only.

---

## 9. Out of scope (and why)

| Deferred | Why |
| --- | --- |
| Semantic query cache | String cache already keys on `pipeline_id|scope|ingest_run_id|query`. Empty answers are not stored. |
| LLM historical-intent model | Compare-intent phrases + `--scope`; `as_of` later |
| Multi-collection | Metadata filter does isolation |
| Server / UI / auth | Terminal + screenshots satisfy the lab |
| 768-d embeddings | Failure modes are structural (lineage, `6100` vs prose), not dim size |
| OCR text as its own section | Would mint a second MEC-5.1 and copy `6100` into travel |
| Second/third chunker | Registry is the scale hook; one strategy ships |
| Directive-filter product | Untrusted-reference prompt + don’t index junk |

---

## 10. Rubric map

| Item | Pts | Satisfied by |
| --- | --- | --- |
| Planted DQ issue | 8 | AP v1 vs v2, AP-5.1 $7,500 vs $10,000 |
| Minimal embed–store–retrieve | 7 | Two sentences, MiniLM, Chroma, before full ingest |
| Chunk / embed / store at scale | 10 | Heading-split + atomic table, MiniLM, Chroma upsert |
| Basic RAG E2E | 10 | `scripts/ask.py` → `ask()` |
| Hybrid beats vector-only | 12 | `6100` + travel, RRF |
| Rerank | 8 | CrossEncoder on fused candidates |
| Eval 8+ | 15 | pytest recall + accuracy |
| Diagnosis → source data | 15 | Executable test + writeup on v1 AP-5.1 |
| Attribution | 5 | `doc_id` + version + section |
| CI / passing run | 10 | pytest in pipeline |

---

## 11. Build order (do not skip 1)

1. Two-sentence embed–store–retrieve (screenshot).
2. Ingest 4 PDFs + metadata + junk tag.
3. One chunker; persist Chroma.
4. Query: vector top-k → generate.
5. Keyword + RRF; `6100` demo.
6. CrossEncoder.
7. 8-case harness + diagnosis test.
8. Citations + CI.

---

## 12. Open questions (decided for v1)

| Question | v1 decision | Later |
| --- | --- | --- |
| When does Chroma die? | Not on 4 PDFs. Stay. | Many concurrent writers, or tight filters over a huge set, or you already run Postgres → `VectorStoreAdapter` → pgvector. |
| Historical mode? | `--scope diagnosis` (and compare intent). | `as_of` date on the same `ask()`. |
| Cache TTL vs `effective_date`? | Key includes `ingest_run_id` and `pipeline_id`. | Still not date TTL. |

---

## 13. Scale later (not this grade)

- `ingest_run_id` already on chunks → eval as regression when a fifth PDF lands.
- Context budget (max tokens into the LLM).
- Second `ChunkingStrategy` when a new family is only FAQ or only forms.
- Honor `superseded_by` and `effective_date` at query time; fail loud on two current rows.

**One line.** Ship the lab on this slice. Keep the ports. Do not implement the whole PRD before the two-sentence loop.
