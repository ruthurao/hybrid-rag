"""Entailment probability and a tau gate.

The premise is the retrieved sentence that contains the fact. The hypothesis
is a declarative claim. A fact passes the gate when P(entailment) is at least tau.
"""

from __future__ import annotations

import math
import re


def softmax(logits: list[float]) -> list[float]:
    peak = max(logits)
    exps = [math.exp(value - peak) for value in logits]
    total = sum(exps)
    return [value / total for value in exps]


def entailment_probability(logits: list[float], labels: list[str]) -> float:
    """P(entailment) from a 3-way NLI logit vector."""
    lowered = [label.lower() for label in labels]
    if "entailment" not in lowered:
        raise ValueError(f"entailment label missing from {labels}")
    if len(logits) != len(labels):
        raise ValueError(f"got {len(logits)} logits for labels {labels}")
    return softmax(logits)[lowered.index("entailment")]


def passes_tau(probability: float, tau: float) -> bool:
    return probability >= tau


def tau_gate(probabilities: list[float], tau: float) -> bool:
    """True when every fact clears tau. An empty list does not pass."""
    return bool(probabilities) and all(passes_tau(probability, tau) for probability in probabilities)


def supporting_sentence(text: str, fact: str) -> str:
    """The sentence in a retrieved chunk that contains the fact."""
    flat = re.sub(r"[ \t]*\n[ \t]*", " ", text).strip()
    for part in re.split(r"(?<=[.])\s+", flat):
        if fact in part:
            return part.strip()
    return flat


class EntailmentScorer:
    """Lazy cross-encoder NLI. Tests should call the pure functions above."""

    def __init__(self, model_name: str, tau: float) -> None:
        self.model_name = model_name
        self.tau = tau
        self._model = None
        self._labels: list[str] | None = None

    def probability(self, premise: str, hypothesis: str) -> float:
        return self.probabilities(premise, [hypothesis])[0]

    def probabilities(self, premise: str, hypotheses: list[str]) -> list[float]:
        return self.score_pairs([(premise, hypothesis) for hypothesis in hypotheses])

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        scores = [0.0] * len(pairs)
        live = [(index, premise, hypothesis) for index, (premise, hypothesis) in enumerate(pairs) if premise.strip()]
        if not live:
            return scores
        model = self._load()
        logits = model.predict(
            [(premise, hypothesis) for _, premise, hypothesis in live],
            show_progress_bar=False,
        )
        labels = self._labels or []
        for (index, _, _), row in zip(live, logits):
            scores[index] = entailment_probability([float(value) for value in row], labels)
        return scores

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(self.model_name)
            raw = model.config.id2label
            self._labels = [str(raw[key]) for key in sorted(raw, key=lambda key: int(key))]
            self._model = model
        return self._model
