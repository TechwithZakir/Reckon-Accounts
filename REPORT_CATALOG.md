# Delivered report catalog

Updated 2026-09-14. Source implementations, pending live ERPNext 15/16 acceptance.

All 23 custom Report records use module **Reckon Accounts**, with prefix-free names.
General Ledger Custom retains the existing Tally-oriented ledger presentation
without taking the name of the standard ERPNext General Ledger.

## Custom views

- Party Ledger
- Account Ledger
- General Ledger Custom
- Day Book
- Cash Book
- Bank Book
- Cash Bank Summary
- Bank Summary
- Ledger Monthly Summary
- Group Summary
- Group Monthly Summary
- Group Vouchers
- Receipt Register
- Payment Register
- Contra Register
- Journal Register
- Debit Note Register
- Credit Note Register
- Voucher Statistics
- Receipts and Payments
- Negative Cash
- Ledger Exceptions
- Funds Flow

## Standard reuse and remaining gap

The workspace links ERPNext General Ledger, Trial Balance, Balance Sheet, Profit
and Loss Statement, Cash Flow, Financial Ratios, Accounts Receivable, Accounts
Payable and Bank Reconciliation Statement. Their implementations stay in ERPNext.

Interest uses ERPNext Dunning and its configured rules; no independent interest
engine is implemented. A general Tally interest report is not claimed equivalent.
Cash Flow Projection is not delivered: no standard projection report was found
in the inspected ERPNext 15/16 inventories. Historical Cash Flow is not a forecast.

## Accounting and release limits

Only Company and the date range are required to open any custom report.
Funds Flow displays a calculation notice until current-asset and current-liability
groups are selected; with mappings it reports changes in working capital. Voucher views show permitted
source lines and disclose that voucher completeness is not asserted. Receipts
and Payments discloses internal-transfer treatment. Exceptions use account root
types rather than treating all credit balances as errors.

All calculations use permission-approved ERPNext records. Scopes are bounded
to 5,000 candidate GL rows and 2,000 referenced identities. Local tests do not
replace live reconciliation, permissions testing or performance acceptance.

Report folder and script names were renamed together. No installed site was
updated by this change; previously installed development Report records require
a site migration review before deployment.
