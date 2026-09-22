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

This procedure (mec-us-0001, v1.0) governs the finalization, locking, and coding of financial records at month-end. Amounts stated in this procedure are in USD. This procedure applies to all business units maintaining financial records subject to monthly close.

## MEC-2.1 Definitions

Close period means the calendar month for which financial records are finalized. Workday means a business day on which the company is open for normal operations, excluding weekends and company holidays. Lock means the point at which a close period's records become fixed and no further entries or edits may be made. General ledger code means the numeric code assigned to a transaction to classify it within the company's chart of accounts. Authorized role means a job ID permitted under Section MEC-4.1 to enter or post records during the close period.

## MEC-3.1 Close process

Before lock, all transactions for the close period shall be entered, reviewed, and reconciled so that account balances reflect the complete and accurate financial position for that period. An authorized role shall confirm that all known transactions for the period have been recorded prior to lock.

## MEC-3.2 Lock timing

The close period is locked on the 5th workday of the following month. The finance manager shall approve the lock before it is applied. Once approved and applied, no further entries, edits, or deletions may be made to records within that close period.

## MEC-4.1 Authorized record entry

Only the following job IDs are authorized to enter or post records during the close period: US-0001, US-0020, US-0984, US-9033, and US-8932. A record entered or posted by a job ID not on this list is not permitted and shall be reversed upon identification.

## MEC-4.2 Unauthorized entry handling

Where a record is found to have been entered by a job ID not listed in Section MEC-4.1, the entry is flagged and referred to the finance manager. The finance manager shall determine whether the entry is reversed, reassigned to an authorized job ID, or otherwise corrected before the close period is locked.

## MEC-5.1 Coding requirements

Travel costs shall be recorded under general ledger code 6100-TRAVEL. Unpaid bills shall be recorded under general ledger code 2100-AP. An authorized role shall apply the correct code to each transaction at the time of entry.

## MEC-5.2 Miscoding handling

Where a transaction is found to be coded incorrectly before lock, an authorized role shall correct the code and re-confirm the balance affected. Where a miscoded transaction is identified after lock, it is treated under Section MEC-6.1 and may not be corrected within the locked period; it shall instead be addressed in the following close period's records.

## MEC-6.1 Post-lock restrictions

Once a close period is locked under Section MEC-3.2, no adjustments, corrections, or new entries may be made to that period's records, regardless of the reason identified. Any correction required as a result of an error discovered after lock shall be recorded in the close period in which it is discovered, not in the locked period.

## MEC-7.1 Exception and escalation

Where the close process under Section MEC-3.1 cannot be completed in time for lock on the 5th workday, an authorized role shall notify the finance manager before the lock deadline. Where an unauthorized entry under Section MEC-4.2 or a coding dispute under Section MEC-5.2 remains unresolved as the lock deadline approaches, the finance manager shall determine whether to resolve the issue before lock or note it for treatment in the following period. The finance manager's decision on the lock, on unauthorized entries, and on unresolved coding disputes is final for that close period.

## MEC-8.1 Recording and outcome

The date of lock, the finance manager's approval, and any unauthorized entries or miscoded transactions identified and corrected prior to lock are recorded against the close period. A record of any issue deferred to the following period under Sections MEC-5.2, MEC-6.1, or MEC-7.1 is retained with the close period record for audit purposes.
