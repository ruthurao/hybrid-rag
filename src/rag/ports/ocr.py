from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.rag.models import ImageAsset


class OcrAdapter(Protocol):
    name: str

    def read(self, path: Path) -> list[ImageAsset]:
        """Return one asset per distinct embedded image, text included if read.

        Repeated placements of the same image are one asset. An adapter that
        cannot read reports the asset with text None and a reason, so an
        unread image is a recorded fact rather than a silent gap.
        """
