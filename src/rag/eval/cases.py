from __future__ import annotations

from dataclasses import dataclass

from src.rag.retrieval.query import SCOPE_COMPARE, SCOPE_DIAGNOSIS, SCOPE_LIVE

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
    # Declarative claims the retrieved policy text must entail. One per must_contain fact.
    must_entail: tuple[str, ...] = ()


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
        must_entail=("An invoice of $10,000 or more requires finance manager approval.",),
        must_not_contain=("$7,500",) + PII,
    ),
    EvalCase(
        name="diagnosis_surfaces_replaced_v1",
        query="What invoice amount needs finance manager approval?",
        scope=SCOPE_DIAGNOSIS,
        must_chunk_ids=("ap-us-0001-v1.0#AP-5.1",),
        must_record_ids=("ap-us-0001-v1.0",),
        must_contain=("$7,500",),
        must_entail=("An invoice of $7,500 or more requires finance manager approval.",),
    ),
    EvalCase(
        name="live_6100_is_the_coding_table",
        query="What is account code 6100 used for at travel close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("6100",),
        must_entail=("Account code 6100 is used for travel costs.",),
    ),
    EvalCase(
        name="live_lock_timing",
        query="When is the close period locked?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-3.2",),
        must_contain=("5th workday",),
        must_entail=("The close period is locked on the 5th workday.",),
    ),
    EvalCase(
        name="live_posting_job_ids_are_not_pii",
        query="Which job IDs may post records during close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-4.1",),
        must_contain=("US-0984",),
        must_entail=("US-0984 is authorized to post records during close.",),
        must_not_contain=PII,
    ),
    EvalCase(
        name="live_expense_faq_is_cited",
        query="Does writing client lunch in the purpose box replace the slip?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-8.1",),
        must_contain=("does not replace the slip",),
        must_entail=("Writing client lunch in the purpose box does not replace the slip.",),
        must_authority=(("EXP-8.1", "advisory"),),
    ),
    EvalCase(
        name="live_payment_window_is_30_days",
        query="How many days after the three-way match must an invoice be paid?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-6.1",),
        must_contain=("30 days",),
        must_entail=("An invoice must be paid within 30 days of the three-way match.",),
        must_not_contain=("45 days",),
        must_not_record_ids=("ap-us-0001-v1.0",),
    ),
    EvalCase(
        name="live_meal_cap",
        query="What is the reimbursable cap per meal?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-4.1",),
        must_contain=("$75",),
        must_entail=("A meal expense of $75 or less per meal is reimbursable.",),
    ),
)

# Extra plants and decoys.
EXTRA_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        name="compare_cites_both_approval_rules",
        query="What changed in the invoice approval threshold?",
        scope=SCOPE_COMPARE,
        must_chunk_ids=("ap-us-0001-v1.0#AP-5.1", "ap-us-0001-v2.0#AP-5.1"),
        must_record_ids=("ap-us-0001-v1.0", "ap-us-0001-v2.0"),
        must_contain=("$7,500", "$10,000"),
        must_entail=(
            "An invoice of $7,500 or more requires finance manager approval.",
            "An invoice of $10,000 or more requires finance manager approval.",
        ),
    ),
    EvalCase(
        name="live_three_way_match",
        query="When may an invoice be paid relative to the purchase order and delivery record?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-3.1",),
        must_contain=("three-way match",),
        must_entail=("A three-way match is required before an invoice proceeds to payment.",),
        must_not_record_ids=("ap-us-0001-v1.0",),
    ),
    EvalCase(
        name="live_duplicate_payment_control",
        query="What happens if the same invoice number and vendor were already paid?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-4.2",),
        must_contain=("flags a potential duplicate",),
        must_entail=("The payment system flags a potential duplicate when the same invoice was already paid.",),
        must_not_record_ids=("ap-us-0001-v1.0",),
    ),
    EvalCase(
        name="compare_payment_window_both_versions",
        query="What changed in the invoice payment period after three-way match?",
        scope=SCOPE_COMPARE,
        must_chunk_ids=("ap-us-0001-v1.0#AP-6.1", "ap-us-0001-v2.0#AP-6.1"),
        must_contain=("45 days", "30 days"),
        must_entail=(
            "An invoice had to be paid within 45 days of the three-way match.",
            "An invoice must be paid within 30 days of the three-way match.",
        ),
    ),
    EvalCase(
        name="diagnosis_old_payment_window_is_45_days",
        query="How many days was the invoice payment period in the replaced AP handbook?",
        scope=SCOPE_DIAGNOSIS,
        must_chunk_ids=("ap-us-0001-v1.0#AP-6.1",),
        must_contain=("45 days",),
        must_entail=("An invoice had to be paid within 45 days of the three-way match.",),
    ),
    EvalCase(
        name="live_alcohol_is_not_reimbursable",
        query="Is alcohol reimbursable on an expense claim?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-4.2",),
        must_contain=("Alcohol is not reimbursable",),
        must_entail=("Alcohol is not reimbursable.",),
    ),
    EvalCase(
        name="live_receipt_threshold",
        query="When must an employee attach a receipt to an expense?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-3.2",),
        must_contain=("$25",),
        must_entail=("An employee must attach a receipt for an expense exceeding $25.",),
    ),
    EvalCase(
        name="live_post_lock_no_adjustments",
        query="Can anyone adjust records after the close period is locked?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-6.1",),
        must_contain=("no adjustments or new entries",),
        must_entail=("No adjustments or new entries may be made after the close period is locked.",),
    ),
    EvalCase(
        name="live_account_2100_stays_in_the_table",
        query="What is account code 2100-AP used for at close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("2100-AP",),
        must_entail=("Account code 2100-AP is used for unpaid bills.",),
    ),
)

# Harder questions. Kept off CASES so the lexical pytest suite stays the
# regression set. scripts/score_eval.py scores these on MiniLM.
STRESS_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        name="stress_live_wording_of_the_replaced_rule",
        query="What invoice amount needs finance manager approval?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-5.1",),
        must_record_ids=("ap-us-0001-v2.0",),
        must_not_record_ids=("ap-us-0001-v1.0",),
        must_contain=("$10,000",),
        must_not_contain=("$7,500",) + PII,
        must_entail=("An invoice of $10,000 or more requires finance manager approval.",),
    ),
    EvalCase(
        name="stress_ten_thousand_paraphrase",
        query="Who has to sign off before we pay a vendor bill of ten thousand dollars or more?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-5.1",),
        must_not_record_ids=("ap-us-0001-v1.0",),
        must_contain=("$10,000",),
        must_not_contain=("$7,500",),
        must_entail=("An invoice of $10,000 or more requires finance manager approval.",),
    ),
    EvalCase(
        name="stress_clerk_can_release_under_the_limit",
        query="Can the AP clerk release an invoice below the approval threshold without the finance manager?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-5.1",),
        must_contain=("without further approval",),
        must_entail=("An invoice below this threshold may be released by the AP clerk without further approval.",),
    ),
    EvalCase(
        name="stress_hold_does_not_start_the_clock",
        query="Does an invoice on hold start the payment countdown?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-3.2",),
        must_contain=("does not begin the payment period",),
        must_entail=("An invoice on hold does not begin the payment period until the discrepancy is resolved.",),
    ),
    EvalCase(
        name="stress_no_po_is_unmatched",
        query="What happens to an invoice that arrives with no purchase order?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-4.1",),
        must_contain=("recorded as unmatched",),
        must_entail=("An invoice received without an associated purchase order is recorded as unmatched.",),
    ),
    EvalCase(
        name="stress_send_back_to_vendor",
        query="Who can send an invoice back to the vendor when approval is still missing near the payment deadline?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-7.1",),
        must_contain=("returned to the vendor",),
        must_entail=("The finance manager may direct that the invoice be returned to the vendor.",),
    ),
    EvalCase(
        name="stress_current_version_is_the_payment_rule",
        query="Which accounts payable version is the current rule for payment decisions?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v2.0#AP-1.1",),
        must_not_record_ids=("ap-us-0001-v1.0",),
        must_contain=("current rule for payment decisions",),
        must_not_contain=("$7,500",),
        must_entail=("This version is the current rule for payment decisions.",),
    ),
    EvalCase(
        name="stress_retired_amount",
        query="Before the current handbook, how large did an invoice have to be before a finance manager approved it?",
        scope=SCOPE_DIAGNOSIS,
        must_chunk_ids=("ap-us-0001-v1.0#AP-5.1",),
        must_record_ids=("ap-us-0001-v1.0",),
        must_contain=("$7,500",),
        must_entail=("An invoice of $7,500 or more requires finance manager approval.",),
    ),
    EvalCase(
        name="stress_pay_window_old_and_new",
        query="What changed in the old and new deadline to pay an invoice after the match?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("ap-us-0001-v1.0#AP-6.1", "ap-us-0001-v2.0#AP-6.1"),
        must_contain=("45 days", "30 days"),
        must_entail=(
            "An invoice had to be paid within 45 days of the three-way match.",
            "An invoice must be paid within 30 days of the three-way match.",
        ),
    ),
    EvalCase(
        name="stress_meal_over_cap_needs_supervisor",
        query="What approval is required when a meal costs more than the reimbursable cap?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-4.3",),
        must_contain=("requires the approval of the employee's supervisor",),
        must_entail=("A meal expense exceeding $75 requires the approval of the employee's supervisor.",),
    ),
    EvalCase(
        name="stress_cap_is_not_a_daily_total",
        query="Does the meal cap apply to the whole day or to each meal?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-4.1",),
        must_contain=("not to an employee's total daily meal spend",),
        must_entail=("The meal cap applies per individual meal, not to the total daily meal spend.",),
    ),
    EvalCase(
        name="stress_expense_clock_is_from_the_incurred_date",
        query="How many days does an employee have to submit a claim after spending the money?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-5.1",),
        must_contain=("30 days of the date the expense was incurred",),
        must_not_contain=("three-way match",),
        must_entail=("An employee shall submit an expense claim within 30 days of the date the expense was incurred.",),
    ),
    EvalCase(
        name="stress_late_claim_needs_supervisor",
        query="What if an employee files an expense after the submission window?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-5.1",),
        must_contain=("A claim submitted after this period",),
        must_entail=("A claim submitted after this period requires the approval of the employee's supervisor.",),
    ),
    EvalCase(
        name="stress_missing_purpose_is_returned",
        query="What happens to an expense claim that has no business purpose?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-3.1",),
        must_contain=("returned to the employee",),
        must_entail=("A claim missing an itemized business purpose is returned to the employee.",),
    ),
    EvalCase(
        name="stress_meals_cannot_be_pooled",
        query="Can three meals on a travel day be claimed as one pile?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-8.1",),
        must_contain=("Each meal stands alone",),
        must_authority=(("EXP-8.1", "advisory"),),
        must_entail=("Each meal stands alone.",),
    ),
    EvalCase(
        name="stress_drink_comes_off_the_bill",
        query="Can a drink stay on the bill if the employee mostly ate food?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-8.1",),
        must_contain=("Take the drink off",),
        must_authority=(("EXP-8.1", "advisory"),),
        must_entail=("Take the drink off before you submit or the whole claim comes back.",),
    ),
    EvalCase(
        name="stress_close_does_not_reopen_expenses",
        query="Can a late expense claim from last month ride along with this month's close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("exp-us-0001-v1.0#EXP-8.1",),
        must_contain=("does not reopen an expense window",),
        must_entail=("Close does not reopen an expense window.",),
    ),
    EvalCase(
        name="stress_cash_code_is_not_the_travel_code",
        query="What account code is cash at close, and which job posts it?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("1000-CASH", "US-0001"),
        must_entail=(
            "Account code 1000-CASH is cash.",
            "US-0001 posts the cash account.",
        ),
    ),
    EvalCase(
        name="stress_payroll_must_log_before_lock_day",
        query="When must the payroll accrual be in the books at close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("5000-PAY",),
        must_entail=("Account code 5000-PAY is the payroll accrual.",),
    ),
    EvalCase(
        name="stress_airfare_code_lives_in_the_table",
        query="Staff keep booking airfare late. Where is the account code for that travel written?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.1",),
        must_contain=("6100",),
        must_entail=("Account code 6100 is used for travel costs.",),
    ),
    EvalCase(
        name="stress_late_travel_does_not_reopen_the_month",
        query="Does a late travel report reopen the close month?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-8.2",),
        must_contain=("does not reopen the month",),
        must_entail=("A late travel report does not reopen the month.",),
    ),
    EvalCase(
        name="stress_no_weekend_lock",
        query="Can month-end lock happen on a weekend?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-8.3",),
        must_contain=("No weekend lock",),
        must_entail=("There is no weekend lock.",),
    ),
    EvalCase(
        name="stress_bad_job_id_is_reversed",
        query="What happens when someone not on the job ID list posts during close?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-4.1",),
        must_contain=("shall be reversed",),
        must_entail=("A record posted by a job ID that is not authorized shall be reversed.",),
    ),
    EvalCase(
        name="stress_miscode_after_lock_waits",
        query="If an account code is wrong after the period is locked, when is it fixed?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-5.2",),
        must_contain=("following period",),
        must_entail=("After lock, a wrong code is treated in the following period.",),
    ),
    EvalCase(
        name="stress_lock_itself_needs_finance_manager",
        query="Who must approve the close lock before it is applied?",
        scope=SCOPE_LIVE,
        must_chunk_ids=("mec-us-0001-v1.0#MEC-3.2",),
        must_contain=("finance manager shall approve the lock",),
        must_entail=("The finance manager shall approve the lock before it is applied.",),
    ),
    EvalCase(
        name="stress_pii_is_not_in_the_answer",
        query="What is Priya Shah's employee id and card last four?",
        scope=SCOPE_LIVE,
        must_not_contain=PII,
    ),
)

CASES: tuple[EvalCase, ...] = RUBRIC_CASES + EXTRA_CASES
