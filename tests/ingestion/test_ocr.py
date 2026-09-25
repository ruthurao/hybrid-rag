from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.rag.adapters.ocr import RapidOcrAdapter
from src.rag.adapters.parser import PdfParser
from src.rag.ingestion.authority import NORMATIVE, UNTRUSTED
from src.rag.config import default_policy
from src.rag.models import INSET, PAGE, ImageAsset

pytest.importorskip("rapidocr_onnxruntime")


class _StubOcr:
    """Returns text we choose, so the routing rule is tested on its own."""

    name = "stub"

    def __init__(self, text: str, role: str) -> None:
        self.asset = ImageAsset(
            digest="stub", pages=(1,), width=10, height=10,
            role=role, text=text, reason="ocr_read",
        )

    def read(self, path):
        return [self.asset]

ROOT = Path(__file__).resolve().parents[2]
CLOSE_PDF = ROOT / "corpus" / "mec-us-0001-v1.0.pdf"
APPROVAL_PDF = ROOT / "corpus" / "ap-us-0001-v1.0.pdf"

SCANNED_LINES = [
    "Scanned Claims Procedure",
    "doc_id: sc-us-0001",
    "record_id: sc-us-0001-v1.0",
    "family: claims",
    "version: v1.0",
    "status: current",
    "effective_date: 2026-01-01",
    "superseded_by: none",
    "SC-1.1 Purpose",
    "This procedure governs scanned records.",
    "SC-2.1 Approval",
    "A supervisor shall approve every scanned claim.",
]


@pytest.fixture(scope="module")
def close_assets():
    return RapidOcrAdapter().read(CLOSE_PDF)


@pytest.fixture(scope="module")
def scanned_pdf(tmp_path_factory):
    """A page with no text layer at all: the image is the document."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1224, 1584), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=40)
    for row, line in enumerate(SCANNED_LINES):
        draw.text((90, 120 + row * 105), line, fill="black", font=font)
    path = tmp_path_factory.mktemp("scan") / "sc-us-0001-v1.0.pdf"
    image.save(path, "PDF", resolution=150)
    return path


def test_repeated_placements_of_one_image_are_one_asset(close_assets):
    assert len(close_assets) == 1
    assert close_assets[0].pages == (1, 2)
    assert close_assets[0].reason == "ocr_read"


def test_a_document_without_images_reports_none():
    assert RapidOcrAdapter().read(APPROVAL_PDF) == []


def test_a_banner_on_a_readable_page_is_an_inset(close_assets):
    assert close_assets[0].role == INSET


def test_an_image_shaped_like_its_empty_page_carries_the_page(scanned_pdf):
    assets = RapidOcrAdapter().read(scanned_pdf)
    assert [a.role for a in assets] == [PAGE]


def test_inset_text_is_untrusted(close_assets):
    record = PdfParser(ocr=RapidOcrAdapter()).parse(CLOSE_PDF)
    from_image = [b for b in record.blocks if b.content_type == "image_text"]
    assert len(from_image) == 1
    assert from_image[0].section is None
    assert from_image[0].authority == UNTRUSTED
    assert from_image[0].authority_reason == "outside_heading_hierarchy"


def test_an_inset_claiming_a_section_heading_does_not_get_one():
    """A graphic can be worded as a heading. Whether the engine transcribes
    the spacing well enough to match the pattern is luck, so the defence is
    routing: inset text never reaches the segmenter."""
    heading = "MEC-5.1 Use the coding table"
    assert re.match(default_policy().section_heading, heading)

    record = PdfParser(ocr=_StubOcr(heading, INSET)).parse(CLOSE_PDF)
    assert [b.section for b in record.blocks].count("MEC-5.1") == 1
    planted = next(b for b in record.blocks if b.text == heading)
    assert planted.section is None
    assert planted.authority == UNTRUSTED


def test_a_scanned_page_yields_normative_sections(scanned_pdf):
    """When the image is the document, its headings are the document's
    headings, and the ordinary structural rule makes them normative. The
    authority model is untouched; only the routing before it differs."""
    record = PdfParser(ocr=RapidOcrAdapter()).parse(scanned_pdf)
    assert record.metadata["record_id"] == "sc-us-0001-v1.0"
    assert record.metadata["status"] == "current"

    by_section = {b.section: b for b in record.blocks}
    assert set(by_section) >= {"SC-1.1", "SC-2.1"}
    assert by_section["SC-1.1"].authority == NORMATIVE
    assert by_section["SC-1.1"].authority_reason == "numbered_section"
    assert not any(b.content_type == "image_text" for b in record.blocks)


def test_a_scanned_document_is_indexed_not_dropped(scanned_pdf):
    """The failure this guards against is silent: an image-only document that
    parses, excludes everything and reports nothing worth storing."""
    from src.rag.ingestion.chunking import HeadingChunker

    record = PdfParser(ocr=RapidOcrAdapter()).parse(scanned_pdf)
    chunks = HeadingChunker().chunk(record, "run", "model")
    assert [c.chunk_id for c in chunks] == [
        "sc-us-0001-v1.0#SC-1.1",
        "sc-us-0001-v1.0#SC-2.1",
    ]


def test_the_card_carries_no_account_code(close_assets):
    assert "6100" not in close_assets[0].text


def test_a_missing_engine_reports_the_images_unread(monkeypatch):
    adapter = RapidOcrAdapter()
    monkeypatch.setattr(adapter, "_load", lambda: None)
    assets = adapter.read(CLOSE_PDF)
    assert len(assets) == 1
    assert assets[0].text is None
    assert assets[0].reason == "ocr_unavailable"
