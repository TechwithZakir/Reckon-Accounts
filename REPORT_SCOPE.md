# Reckon Accounts report scope

User direction, 2026-09-13: cover Tally accounting-report capabilities missing
from ERPNext; reuse standard ERPNext reports instead of rebuilding them.
This supersedes earlier lists proposing custom versions of every standard report.

## Reuse first

General Ledger, Trial Balance, Balance Sheet, Profit and Loss, Cash Flow,
Accounts Receivable and Accounts Payable are standard ERPNext capabilities.
Use their reports and filters. Outstanding/ageing, sales/purchase registers,
bank reconciliation, cost-centre and budget reporting require comparison with
the installed standard capabilities before proposing any custom report.

The three existing Reckon ledger implementations remain development code.
Review them for consolidation: retain only required Tally-specific presentation,
navigation or scope behavior; do not treat a renamed standard ledger as a gap.
No existing implementation has been removed by this scope update.

## Accounting capability checklist

Current source delivery is recorded in [the report catalog](REPORT_CATALOG.md).
This checklist compares presentation and navigation, not just names. Live
behavior and accounting equivalence still require validation on ERPNext 15/16.

| Report / view | Capability to compare |
| --- | --- |
| Day Book | Date-wise vouchers with complete permitted lines and voucher-level pagination |
| Cash Book | Cash ledger daily/monthly movement, opening/closing and voucher drill-down |
| Bank Book | Bank ledger movement and balances with source voucher details |
| Cash/Bank Summary | Account-wise opening, receipts, payments and closing |
| Ledger Monthly Summary | Month-wise movement and balance with transaction drill-down |
| Group Summary / Monthly Summary | Account-group hierarchy and period drill-down |
| Group Vouchers | Voucher activity across a selected account group |
| Receipt / Payment / Contra / Journal Registers | Tally-style voucher-type views using real ERPNext identities |
| Debit Note / Credit Note Registers | Return/adjustment views without fabricating posting types |
| Voucher Statistics | Counts by source type with permitted drill-down |
| Receipts and Payments Account | Cash/bank receipt-payment presentation; distinguish internal transfers |
| Funds Flow | Compare Tally funds-flow semantics with available ERPNext reporting |
| Cash Flow Projection | Forecast rather than historical cash-flow statement |
| Negative Cash / Ledger Exceptions | Date-wise exception analysis |
| Interest Calculation | Compare standard interest features and calculation policy |
| Ratio Analysis | Compare available ratios and required Tally presentation |

Transaction books, registers and summaries now have source implementations.
Standard reports remain linked rather than copied. Interest follows ERPNext
Dunning; Cash Flow Projection remains an explicit uncovered capability because
no standard report was found in the inspected version inventories.

## Coverage boundaries

This repository's current scope is accounting. Tally inventory, payroll,
manufacturing and country-specific statutory reporting need separate capability
inventories; they are not implicitly claimed as covered here. Tax reports must
be compared with the installed localization apps and jurisdiction requirements.

All reports use ERPNext source documents and ledgers. No parallel accounting
engine, duplicate masters, or direct GL posting is introduced. Missing reports
remain unimplemented until their source and validation are delivered.

## Reference starting points

- [Tally accounting and financial reports](https://help.tallysolutions.com/accounting-financial-reports-tally/)
- [ERPNext accounting reports](https://docs.frappe.io/erpnext/accounting-reports)
- [ERPNext General Ledger](https://docs.frappe.io/erpnext/general-ledger)

These references establish the reuse-first approach, not a completed version-by-version
gap audit. Installed ERPNext 15/16 and localization inventories remain to be verified.

## Ledger display convention

All Reckon reports display the permitted Account `account_name` in ledger columns,
headings, summaries and counter-account particulars. IDs remain hidden row keys
for grouping and drill-down; identical titles never merge accounts. Full CSV exports
include the title column and explicit technical ID columns for traceability. If a
title is missing or not readable, the permitted account ID is the fallback.
