"""Fixed cases, retrieval recall, and the entailment tau gate."""

from src.rag.eval.cases import CASES, RUBRIC_CASES, STRESS_CASES
from src.rag.eval.entailment import EntailmentScorer, tau_gate
from src.rag.eval.record import golden_document, record_document

__all__ = [
    "CASES",
    "EntailmentScorer",
    "RUBRIC_CASES",
    "STRESS_CASES",
    "golden_document",
    "record_document",
    "tau_gate",
]
