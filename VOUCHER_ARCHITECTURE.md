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

Direct Expense and Direct Income vouchers create standard submitted ERPNext
`Journal Entry` documents. This avoids fake Customers or Suppliers and keeps
Expense and Income accounts out of Payable and Receivable settlement flows.

Supplier payments and Customer receipts remain standard `Payment Entry` documents.
The custom pages open a new Payment Entry with `payment_type = Pay` or
`payment_type = Receive` rather than duplicating ERPNext allocation, outstanding,
exchange-rate, Payment Ledger, advance and reconciliation behavior.

No code writes `GL Entry` directly. The Journal Entry controller calls ERPNext GL
posting, frozen/closed-period checks, budget checks, accounting dimension handling,
currency validation and cancellation rules.

## Account filtering and validation

Payment Voucher, Direct Expense:

- Paid From: selected company, non-group, `account_type in ("Cash", "Bank")`
- Expense Account: selected company, non-group, `root_type = "Expense"`
- Journal Entry rows: Expense debit, Cash/Bank credit

Receipt Voucher, Direct Income:

- Received To: selected company, non-group, `account_type in ("Cash", "Bank")`
- Income Account: selected company, non-group, `root_type = "Income"`
- Journal Entry rows: Cash/Bank debit, Income credit

Browser filters are for usability only. `reckon_accounts.accounting.voucher_service`
revalidates company, account class, non-group accounts, distinct debit/credit
accounts, positive amounts, Mode of Payment default account and accounting
dimensions server-side.

## Permissions and lifecycle

The service uses normal Frappe permissions and does not pass
`ignore_permissions=True`. A user must be able to create `Journal Entry` for direct
vouchers and create `Payment Entry` for party vouchers.

Submitted direct vouchers are submitted Journal Entries. Cancellation, amendment,
frozen period behavior, GL reversal and audit trail follow standard ERPNext
Journal Entry rules. The user is shown the generated Journal Entry number and can
open or print it from the success panel.

## Attachments

The Desk page upload control creates a File first. After successful submission, the
page resolves that File by `file_url` and attaches it to the generated Journal
Entry, keeping supporting bills and receipts traceable from the accounting
document.

## Upgrade safety

All code lives inside `reckon_accounts`. The implementation does not modify
ERPNext/Frappe source, monkey-patch accounting controllers, or relax Payment Entry
account filters to make Income or Expense accounts act like party accounts.

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
