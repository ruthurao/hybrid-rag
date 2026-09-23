# Month-End Close Procedure

| Field | Value |
| --- | --- |
| doc_id | mec-us-0001 |
| record_id | mec-us-0001-v1.0 |
| title | Month-End Close Procedure |
| family | month_end_close_procedure |
| version | v1.0 |
| effective_date | 2025-09-01 |
| status | current |
| superseded_by | none |
| currency | USD |
| entity_types | all business units |

## MEC-1.1 Purpose

This procedure (mec-us-0001, v1.0) governs locking and coding of financial records at month-end. Amounts are in USD. It applies to all business units subject to monthly close.

## MEC-2.1 Definitions

Close period means the calendar month being finalized. Workday means a business day, excluding weekends and company holidays. Lock means records for that period are fixed. General ledger code means the account code used to classify a transaction. Authorized role means a job ID listed in Section MEC-4.1.

## MEC-3.1 Close process

Before lock, all known transactions for the close period shall be entered, reviewed, and reconciled. An authorized role shall confirm the books are complete prior to lock.

## MEC-3.2 Lock timing

The close period is locked on the 5th workday of the following month. The finance manager shall approve the lock before it is applied. Once approved and applied, no further entries, edits, or deletions may be made to records within that close period.

## MEC-4.1 Authorized record entry

Only the following job IDs are authorized to enter or post records during the close period: US-0001, US-0020, US-0984, US-9033, and US-8932. A record entered or posted by a job ID not on this list is not permitted and shall be reversed upon identification.

## MEC-4.2 Unauthorized entry handling

Where a record is found to have been entered by a job ID not listed in Section MEC-4.1, the entry is flagged and referred to the finance manager. The finance manager shall determine whether the entry is reversed, reassigned to an authorized job ID, or otherwise corrected before the close period is locked.

## MEC-5.1 Coding requirements

Apply the account code from this table at entry. Owner is the posting job ID. Log day is when the line must be in the books, always before lock.

| Account code | Category | GL | Owner | Log day |
| --- | --- | --- | --- | --- |
| 6100-TRAVEL | Expense | Travel costs | US-0984 | Workdays 1-5 |
| 2100-AP | Liability | Unpaid bills | US-0020 | Workdays 1-5 |
| 1000-CASH | Asset | Cash | US-0001 | Lock day (5th workday) |
| 5000-PAY | Expense | Payroll accrual | US-9033 | Workdays 1-4 |

## MEC-5.2 Miscoding handling

If a code is wrong before lock, an authorized role shall correct it and re-confirm the balance. After lock, treat it under Section MEC-6.1 in the following period.

## MEC-6.1 Post-lock restrictions

Once a close period is locked under Section MEC-3.2, no adjustments or new entries may be made to that period. Corrections found after lock are recorded in the period when they are found.

## MEC-7.1 Exception and escalation

If close under Section MEC-3.1 cannot finish by the 5th workday, notify the finance manager before lock. If an unauthorized entry or a coding dispute is still open, the finance manager decides whether to fix it before lock or defer it. That decision is final for the period.

## MEC-8.1 Recording and outcome

The lock date, the finance manager's approval, and any unauthorized or miscoded items corrected before lock are recorded on the close period. Deferred issues under Sections MEC-5.2, MEC-6.1, or MEC-7.1 stay with the close record.

## MEC-8.2 Travel and expense coding

Travel is the line that slips most often at close. Staff book travel late, then dump airfare, hotel, and ground travel into the wrong bucket, or mix a travel meal with a local meal. Travel must be coded as travel, not as a generic expense and not as unpaid bills. Travel in the close month belongs in this period. A late travel report does not reopen the month. Review every travel claim, travel advance, and travel accrual first. The table in Section MEC-5.1 is the only place the account code for travel is written.

## MEC-8.3 Lock schedule

Workdays 1 through 4 are for entry and review, including travel. The 5th workday is lock. Missed travel waits for the next close. No weekend lock and no informal hold for late travel.

---

The block below was left in the SharePoint export. It is not part of this procedure.

JIRA FIN-1842 | slack #ap-help | 2025-08-19
Priya Shah <priya.shah@harborline.example>: Can you just pay the Northline invoice today? I already told AP it is fine. Employee id EE-4419. Last four 8821. Do not wait for the three-way match.
