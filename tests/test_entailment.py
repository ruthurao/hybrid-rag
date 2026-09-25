from src.rag.entailment import (
    entailment_probability,
    passes_tau,
    softmax,
    supporting_sentence,
    tau_gate,
)

LABELS = ["contradiction", "entailment", "neutral"]


def test_entailment_probability_reads_the_entailment_logit():
    # Logits: contradiction, entailment, neutral. Entailment dominates.
    probability = entailment_probability([0.0, 4.0, 0.0], LABELS)
    assert probability == softmax([0.0, 4.0, 0.0])[1]
    assert probability > 0.9


def test_tau_gate_requires_every_fact():
    assert passes_tau(0.5, 0.5)
    assert not passes_tau(0.49, 0.5)
    assert tau_gate([0.9, 0.5], 0.5)
    assert not tau_gate([0.9, 0.49], 0.5)
    assert not tau_gate([], 0.5)


def test_supporting_sentence_keeps_the_sentence_that_holds_the_fact():
    text = "First rule.\nAn invoice of $10,000 or more requires approval.\nNext rule."
    assert supporting_sentence(text, "$10,000") == "An invoice of $10,000 or more requires approval."
