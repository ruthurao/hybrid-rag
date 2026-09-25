from __future__ import annotations

from src.rag.ingestion.authority import ADVISORY, NORMATIVE, RANK, UNTRUSTED, annotate_blocks
from src.rag.ingestion.chunking import (
    LINEAGE_FIELDS,
    HeadingChunker,
    indexable,
    split_on_sentences,
)
from src.rag.ingestion.detectors import classify_content
from src.rag.models import PROSE, TABLE, Block, Record


def _by_id(chunks):
    return {chunk.chunk_id: chunk for chunk in chunks}


def test_account_code_lives_in_one_chunk(chunks):
    """Vector search reaches the travel prose; only keyword search reaches the
    table. Copying the code across that boundary would erase the difference."""
    with_code = [c.chunk_id for c in chunks if "6100" in c.text]
    assert with_code == ["mec-us-0001-v1.0#MEC-5.1"]

    travel = _by_id(chunks)["mec-us-0001-v1.0#MEC-8.2"]
    assert travel.text.lower().count("travel") >= 8
    assert "6100" not in travel.text


def test_coding_table_is_one_atomic_chunk(chunks):
    table = _by_id(chunks)["mec-us-0001-v1.0#MEC-5.1"]
    assert table.metadata["content_type"] == "table"
    for code in ("6100-TRAVEL", "2100-AP", "1000-CASH", "5000-PAY"):
        assert code in table.text


def test_both_ap_versions_keep_their_own_approval_rule(chunks):
    by_id = _by_id(chunks)
    v1 = by_id["ap-us-0001-v1.0#AP-5.1"]
    v2 = by_id["ap-us-0001-v2.0#AP-5.1"]
    assert "$7,500" in v1.text and v1.metadata["status"] == "replaced"
    assert "$10,000" in v2.text and v2.metadata["status"] == "current"


def test_untrusted_content_is_never_chunked(chunks):
    for chunk in chunks:
        assert chunk.metadata["authority"] != UNTRUSTED
        assert chunk.metadata["authority_rank"] >= RANK[ADVISORY]


def test_personal_data_is_not_written_to_any_chunk(chunks):
    """Dropped at chunk time, not filtered at query time: it never reaches disk."""
    for chunk in chunks:
        lowered = chunk.text.lower()
        assert "ee-4419" not in lowered
        assert "priya" not in lowered
        assert "8821" not in lowered


def test_faq_stays_whole_so_its_disclaimer_travels_with_it(chunks):
    faq = _by_id(chunks)["exp-us-0001-v1.0#EXP-8.1"]
    assert faq.metadata["content_type"] == "faq"
    assert faq.metadata["authority"] == ADVISORY
    assert "do not replace the numbered rules" in faq.text.lower()
    assert faq.text.count("Q:") == 4


def test_every_chunk_carries_its_lineage(chunks):
    for chunk in chunks:
        for field in LINEAGE_FIELDS:
            assert chunk.metadata[field], (chunk.chunk_id, field)
        assert chunk.metadata["ingest_run_id"] == "test-run"
        assert chunk.metadata["chunker"] == "heading-split"


def test_chunk_ids_are_unique_and_stable(chunks):
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_rechunking_the_same_record_yields_the_same_ids(ingested):
    _, records, chunks = ingested
    chunker = HeadingChunker()
    again = [
        c.chunk_id
        for record in records
        for c in chunker.chunk(record, "test-run", "model")
    ]
    assert again == [c.chunk_id for c in chunks]


# --- rules proven on content the corpus does not contain -------------------


def _block(text: str, section: str = "ZZ-1.1") -> Block:
    return Block(
        section=section,
        heading=f"{section} Heading",
        text=text,
        start=0,
        end=len(text),
    )


def _record(blocks: list[Block]) -> Record:
    """Annotated the way ingest annotates, so typing is not faked here."""
    metadata = {field: "x" for field in LINEAGE_FIELDS}
    metadata["record_id"] = "zz-us-0009-v1.0"
    annotate_blocks(blocks, metadata["record_id"])
    return Record(path=None, title="T", metadata=metadata, blocks=blocks)


def test_oversized_prose_splits_on_sentence_bounds():
    sentence = "This clause restates the obligation in full. "
    long_text = sentence * 40
    parts = split_on_sentences(long_text, 1000)
    assert len(parts) > 1
    assert all(len(part) <= 1000 for part in parts)
    assert all(part.endswith(".") for part in parts)
    assert "".join(part.replace(" ", "") for part in parts) == long_text.replace(" ", "")


def test_a_long_table_is_never_split_mid_row():
    rows = "\n".join(f"{n}000-CODE Expense Cell{n} US-000{n} Workday {n}" for n in range(1, 60))
    block = _block(f"ZZ-1.1 Codes\n{rows}")
    chunks = HeadingChunker().chunk(_record([block]), "run", "model")
    assert len(chunks) == 1
    assert len(chunks[0].text) > 1000
    assert chunks[0].metadata["content_type"] == TABLE


def test_wrapped_prose_is_not_mistaken_for_a_table():
    wrapped = (
        "Travel is the line that slips most often at close, and staff book it late\n"
        "then dump airfare, hotel, and ground travel into the wrong bucket here\n"
        "or mix a travel meal with a local meal before the close period ends."
    )
    assert classify_content(wrapped) == PROSE


def test_the_chunker_does_not_retype_its_input():
    """Typing happens once, before anything judges or cuts. A chunker that
    reclassifies would let the two answers drift apart."""
    block = _block("ZZ-1.1 Heading\nJust a sentence of prose here.")
    record = _record([block])
    HeadingChunker().chunk(record, "run", "model")
    assert block.content_type == PROSE


def test_indexable_drops_by_rank_not_by_recognising_content():
    kept = _block("A numbered rule.")
    kept.authority_rank = RANK[NORMATIVE]
    unheaded = Block(section=None, heading="", text="anything at all", start=0, end=3)
    assert indexable([kept, unheaded], min_rank=RANK[ADVISORY]) == [kept]
