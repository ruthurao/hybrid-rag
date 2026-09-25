from __future__ import annotations

from dataclasses import dataclass

from src.rag.query import SCOPE_COMPARE, SCOPE_DIAGNOSIS, SCOPE_LIVE

PII = ("EE-4419", "priya", "8821")


@dataclass(frozen=True)
class EvalCase:
    name: str
    query: str
    scope: str
    must_chunk_ids: tuple[str, ...] = ()
    must_record_ids: tuple[str, ...] = ()
    must_not_record_ids: tuple[str, ...] = ()
    must_contain: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()
    # (section, authority) pairs that must appear on a citation
    must_authority: tuple[tuple[str, str], ...] = ()


# First eight: unique questions, gold chunk + gold fact. Screenshot these.
RUBRIC_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        name="live_approval_is_current_v2",
        query="What is the invoice approval threshold?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-5.1",),
        must_record_ids=("ap-us-0001-v2.0",),
        must_not_record_ids=("ap-us-0001-v1.0",),
        must_contain=("$10,000",),
        must_not_contain=("$7,500",) + PII,
    ),
    EvalCase(
        name="diagnosis_surfaces_replaced_v1",
        query="What invoice amount needs finance manager approval?",
        scope=SCOPE_DIAGNOSIS,
        must_chunk_ids=("ap-us-0001-v1.0#AP-5.1",),
        must_record_ids=("ap-us-0001-v1.0",),
        must_contain=("$7,500",),
    ),
    EvalCase(
        name="live_6100_is_the_coding_table",
        query="What is account code 6100 used for at travel close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("6100",),
    ),
    EvalCase(
        name="live_lock_timing",
        query="When is the close period locked?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-3.2",),
        must_contain=("5th workday",),
    ),
    EvalCase(
        name="live_posting_job_ids_are_not_pii",
        query="Which job IDs may post records during close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-4.1",),
        must_contain=("US-0984",),
        must_not_contain=PII,
    ),
    EvalCase(
        name="live_expense_faq_is_cited",
        query="Does writing client lunch in the purpose box replace the slip?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-8.1",),
        must_contain=("does not replace the slip",),
        must_authority=(("EXP-8.1", "advisory"),),
    ),
    EvalCase(
        name="live_payment_window_is_30_days",
        query="How many days after the three-way match must an invoice be paid?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-6.1",),
        must_contain=("30 days",),
        must_not_contain=("45 days",),
        must_not_record_ids=("ap-us-0001-v1.0",),
    ),
    EvalCase(
        name="live_meal_cap",
        query="What is the reimbursable cap per meal?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-4.1",),
        must_contain=("$75",),
    ),
)

# Extra plants and decoys. Not required by the 15-pt line.
EXTRA_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        name="compare_cites_both_approval_rules",
        query="What changed in the invoice approval threshold?",
        scope=SCOPE_COMPARE,
        must_chunk_ids=("ap-us-0001-v1.0#AP-5.1", "ap-us-0001-v2.0#AP-5.1"),
        must_record_ids=("ap-us-0001-v1.0", "ap-us-0001-v2.0"),
        must_contain=("$7,500", "$10,000"),
    ),
    EvalCase(
        name="live_three_way_match",
        query="When may an invoice be paid relative to the purchase order and delivery record?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-3.1",),
        must_contain=("three-way match",),
        must_not_record_ids=("ap-us-0001-v1.0",),
    ),
    EvalCase(
        name="live_duplicate_payment_control",
        query="What happens if the same invoice number and vendor were already paid?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-4.2",),
        must_contain=("flags a potential duplicate",),
        must_not_record_ids=("ap-us-0001-v1.0",),
    ),
    EvalCase(
        name="compare_payment_window_both_versions",
        query="What changed in the invoice payment period after three-way match?",
        scope=SCOPE_COMPARE,
        must_chunk_ids=("ap-us-0001-v1.0#AP-6.1", "ap-us-0001-v2.0#AP-6.1"),
        must_contain=("45 days", "30 days"),
    ),
    EvalCase(
        name="diagnosis_old_payment_window_is_45_days",
        query="How many days was the invoice payment period in the replaced AP handbook?",
        scope=SCOPE_DIAGNOSIS,
        must_chunk_ids=("ap-us-0001-v1.0#AP-6.1",),
        must_contain=("45 days",),
    ),
    EvalCase(
        name="live_alcohol_is_not_reimbursable",
        query="Is alcohol reimbursable on an expense claim?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-4.2",),
        must_contain=("Alcohol is not reimbursable",),
    ),
    EvalCase(
        name="live_receipt_threshold",
        query="When must an employee attach a receipt to an expense?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-3.2",),
        must_contain=("$25",),
    ),
    EvalCase(
        name="live_post_lock_no_adjustments",
        query="Can anyone adjust records after the close period is locked?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-6.1",),
        must_contain=("no adjustments or new entries",),
    ),
    EvalCase(
        name="live_account_2100_stays_in_the_table",
        query="What is account code 2100-AP used for at close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("2100-AP",),
    ),
)

CASES: tuple[EvalCase, ...] = RUBRIC_CASES + EXTRA_CASES
