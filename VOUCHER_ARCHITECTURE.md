# Payment and Receipt Voucher Architecture

## Discovery evidence

Inspected Reckon Accounts modules:

- `reckon_accounts/hooks.py`
- `reckon_accounts/api.py`
- `reckon_accounts/navigation.py`
- `reckon_accounts/access_control.py`
- `reckon_accounts/payment_entry_setup.py`
- `reckon_accounts/public/js/payment_entry.js`
- `reckon_accounts/reckon_accounts/page/voucher_entry/voucher_entry.js`
- `reckon_accounts/accounting/*`
- existing source tests under `reckon_accounts/tests`

Inspected ERPNext reference source:

- `D:\zakir\FrapeeProject\Reckon-HRPolicy\.reference\erpnext`
- branch `version-16`
- commit `4048fb70e14d1843956fcdabb7c3cca75a1cbcdd`
- `erpnext/accounts/doctype/payment_entry/payment_entry.py`
- `erpnext/accounts/doctype/journal_entry/journal_entry.py`
- `erpnext/accounts/general_ledger.py`

The reference is not a confirmed installed bench for this app. Live validation must
still inspect the actual target bench before release.

## Accounting decision

All payment flows use the standard ERPNext `Payment Entry` DocType. Party
settlements and contra entries retain the native ERPNext behavior. Direct Expense
uses `Voucher Subtype = Direct Expense` and `Payment Type = Pay`; Direct Income uses
`Voucher Subtype = Direct Income` and `Payment Type = Receive`.

ERPNext normally requires a party for Pay and Receive. The app's narrow Payment
Entry controller extension removes that requirement only for the two direct
subtypes, validates the selected accounts, and adds the expense or income GL leg
through the standard Payment Entry posting lifecycle. No code writes `GL Entry`
directly and no fake party is created.

## Account filtering and validation

Direct Expense:

- Paid From: selected company, non-group, `account_type in ("Cash", "Bank")`
- Expense Account: selected company, non-group, `root_type = "Expense"`
- Payment Entry rows: Expense debit, Cash/Bank credit

Direct Income:

- Received To: selected company, non-group, `account_type in ("Cash", "Bank")`
- Income Account: selected company, non-group, `root_type = "Income"`
- Payment Entry rows: Cash/Bank debit, Income credit

Browser filters are for usability only. The Payment Entry controller and the
compatibility API revalidate company, account class, non-group accounts, distinct
accounts, positive amounts, Mode of Payment and accounting dimensions server-side.

## Permissions and lifecycle

The service uses normal Frappe permissions and does not pass
`ignore_permissions=True`. A user must be able to create `Payment Entry`.

Submitted direct vouchers are submitted Payment Entries. Cancellation, amendment,
frozen period behavior, GL reversal and audit trail follow standard ERPNext Payment
Entry rules.

## Attachments

Attachments continue to use the standard Payment Entry form and document flow.

## Upgrade safety

All code lives inside `reckon_accounts`. The implementation does not modify
ERPNext/Frappe source; the controller override is limited to explicit direct
subtypes and never changes normal party settlement behavior.

## Validation still required on a bench

Source checks cover architecture and packaging. A real Frappe/ERPNext bench must
still run:

- `bench --site <site> migrate`
- `bench build --app reckon_accounts`
- live direct expense and direct income postings
- GL verification
- cancellation verification
- Mode of Payment default-account verification
- dynamic Accounting Dimension propagation
- restricted-user permission checks
