from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from src.rag.generate import NO_COMPARE, NO_HIT, _citations
from src.rag.models import Hit

Messages = list[dict[str, str]]
Complete = Callable[[Messages], str]


class OllamaGenerator:
    """Local chat call to Ollama. Citations are copied from chunk metadata.

    `complete` replaces the HTTP call in tests. An empty excerpt list never
    calls it, and an empty model reply raises so the caller does not cache it.
    """

    def __init__(
        self,
        model_name: str = "llama3.2:3b",
        base_url: str = "http://127.0.0.1:11434",
        complete: Complete | None = None,
    ) -> None:
        self.model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._complete = complete or self._post

    def generate(
        self, query: str, hits: list[Hit], *, compare: bool
    ) -> tuple[str, list[dict]]:
        if not hits:
            return (NO_COMPARE if compare else NO_HIT), []
        text = (self._complete(_messages(query, hits, compare)) or "").strip()
        if not text:
            raise RuntimeError("LLM returned an empty answer")
        return text, _citations(hits)

    def _post(self, messages: Messages) -> str:
        body = json.dumps(
            {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0},
            }
        ).encode()
        request = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama is not running at {self._base_url}") from exc
        try:
            content = payload["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama response had no answer text") from exc
        return content or ""


def _messages(query: str, hits: list[Hit], compare: bool) -> Messages:
    system = (
        "Answer only from the policy excerpts. "
        "If they do not contain the answer, say so. "
        "Quote amounts, account codes, and day counts exactly as written. "
        "Do not use outside knowledge."
    )
    if compare:
        system += (
            " The excerpts may include a current version and a replaced version. "
            "Name which is current and which is replaced, and state both."
        )
    blocks = []
    for hit in hits:
        meta = hit.chunk.metadata
        label = (
            f"{meta.get('doc_id')} {meta.get('version')} {meta.get('section')} "
            f"status={meta.get('status')}"
        )
        blocks.append(f"[{label}]\n{hit.chunk.text}")
    user = f"Question: {query}\n\nExcerpts:\n\n" + "\n\n".join(blocks)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
