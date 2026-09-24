from __future__ import annotations

import hashlib
from pathlib import Path

from pypdf import PdfReader

from src.rag.models import PAGE, INSET, ImageAsset


class RapidOcrAdapter:
    """Reads embedded images with a pip-only OCR engine.

    The engine is imported on first use. When it is missing the images are
    still reported, unread, so a deployment without it loses content it can
    account for rather than crashing.
    """

    name = "rapidocr-onnxruntime"

    def __init__(
        self,
        min_confidence: float = 0.5,
        page_text_threshold: int = 50,
        page_aspect_tolerance: float = 0.15,
    ) -> None:
        self.min_confidence = min_confidence
        self.page_text_threshold = page_text_threshold
        self.page_aspect_tolerance = page_aspect_tolerance
        self._engine = None
        self._loaded = False

    def read(self, path: Path) -> list[ImageAsset]:
        found = self._collect(path)
        if not found:
            return []
        engine = self._load()
        for asset, image in found:
            if engine is None:
                asset.reason = "ocr_unavailable"
                continue
            asset.text, asset.reason = self._transcribe(engine, image)
        return [asset for asset, _ in found]

    def _collect(self, path: Path) -> list[tuple[ImageAsset, "object"]]:
        """One entry per distinct image, carrying every page it appears on."""
        by_digest: dict[str, ImageAsset] = {}
        pixels: dict[str, object] = {}
        for number, page in enumerate(PdfReader(str(path)).pages, start=1):
            layer = len((page.extract_text() or "").strip())
            page_aspect = float(page.mediabox.width) / float(page.mediabox.height)
            for embedded in page.images:
                image = embedded.image
                digest = hashlib.sha256(embedded.data).hexdigest()[:16]
                existing = by_digest.get(digest)
                if existing:
                    existing.pages = existing.pages + (number,)
                    continue
                width, height = image.size
                by_digest[digest] = ImageAsset(
                    digest=digest,
                    pages=(number,),
                    width=width,
                    height=height,
                    role=self._role(width / height, page_aspect, layer),
                )
                pixels[digest] = image
        return [(asset, pixels[digest]) for digest, asset in by_digest.items()]

    def _role(self, image_aspect: float, page_aspect: float, layer_chars: int) -> str:
        """Does this image carry the page, or decorate it?

        A scan is the page: nothing extractable underneath it and the same
        shape as the sheet. Anything else is an inset, and an inset has no
        place in the document's heading hierarchy however it is worded.
        """
        if layer_chars > self.page_text_threshold:
            return INSET
        off_shape = abs(image_aspect - page_aspect) / page_aspect
        return PAGE if off_shape <= self.page_aspect_tolerance else INSET

    def _load(self):
        if not self._loaded:
            self._loaded = True
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError:
                return None
            self._engine = RapidOCR()
        return self._engine

    def _transcribe(self, engine, image) -> tuple[str | None, str]:
        import numpy as np

        result, _ = engine(np.array(image.convert("RGB")))
        lines = [
            text.strip()
            for _, text, confidence in (result or [])
            if float(confidence) >= self.min_confidence and text.strip()
        ]
        if not lines:
            return None, "no_text_found"
        return "\n".join(lines), "ocr_read"
