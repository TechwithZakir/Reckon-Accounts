# Phase 1 upstream contracts

Source inspection completed 2026-09-13. These are inspected revisions, not a claim
that either version has passed installation or live reconciliation on this host.

| Project | Branch | Inspected revision |
| --- | --- | --- |
| Frappe | version-15 | `9f8ae9cd25b6735be345da6cc12e9f5a96050c68` |
| ERPNext | version-15 | `df8b7f9648c2ec4da12db8c4022edc8dd1018c6b` |
| Frappe | version-16 | `988e54f3c4c291e2077a83809663f123731abe76` |
| ERPNext | version-16 | `4048fb70e14d1843956fcdabb7c3cca75a1cbcdd` |

## Accounting

Reference modules:

- [ERPNext 15 General Ledger](https://github.com/frappe/erpnext/blob/df8b7f9648c2ec4da12db8c4022edc8dd1018c6b/erpnext/accounts/report/general_ledger/general_ledger.py)
- [ERPNext 16 General Ledger](https://github.com/frappe/erpnext/blob/4048fb70e14d1843956fcdabb7c3cca75a1cbcdd/erpnext/accounts/report/general_ledger/general_ledger.py)
- [GL Entry schema](https://github.com/frappe/erpnext/blob/df8b7f9648c2ec4da12db8c4022edc8dd1018c6b/erpnext/accounts/doctype/gl_entry/gl_entry.json)

Reckon implements its own bounded, authorized GL read instead of calling the
standard report's unrestricted name-enrichment queries. It compares against
`general_ledger.execute(filters)` in the opt-in integration suite.

The adapters exclude `is_cancelled` rows and retain Period Closing Vouchers.
Opening classification follows `get_accountwise_gle`; the candidate date window
follows `get_conditions`. Opening vouchers can enter the opening balance even
after To Date unless the site's ignore-opening-check setting excludes them. The
Show Opening Vouchers as Movement option changes their classification, while
pre-period entries remain opening. This is a ledger policy, not a financial
statement policy. Standard-report grouping/display may differ; reconciliation
compares matched account/party scopes, company currency and final numeric balances.

Finance Book logic includes blank/null entries with the selected book, or with
the company's default book when explicitly enabled. Selecting another book while
including a different company default is rejected. No selection defaults to blank
book entries. Disabled dimensions cannot be selected, but populated disabled
dimensions still participate in record permission checks.

The installed schema, versions and required setting are checked before querying.
Only matching major versions 15 or 16 are accepted. Minor-version compatibility
still needs integration testing. Amounts retain source precision for accumulation;
the installed `get_field_precision` and `flt` provide displayed balance rounding.

## Frappe interfaces

- [Frappe 15 query reports](https://github.com/frappe/frappe/blob/9f8ae9cd25b6735be345da6cc12e9f5a96050c68/frappe/desk/query_report.py): `get_report_doc` enforces report access; Script Reports return columns, data, message, chart, summary and skip-total-row.
- [Frappe 16 query adapter](https://github.com/frappe/frappe/blob/988e54f3c4c291e2077a83809663f123731abe76/frappe/model/qb_query.py): `get_list` uses the query-builder adapter with `limit`. Version 15 uses `limit_page_length`. Both are called with permissions enabled.
- [Frappe permissions](https://github.com/frappe/frappe/blob/988e54f3c4c291e2077a83809663f123731abe76/frappe/permissions.py): document read checks complement list visibility and permission-query conditions.
- [Report client](https://github.com/frappe/frappe/blob/9f8ae9cd25b6735be345da6cc12e9f5a96050c68/frappe/public/js/frappe/views/reports/query_report.js): report includes, asynchronous onload, filters, formatter, export and query-string route filters.

Financial queries never use `get_all`, raw SQL, `ignore_permissions=True`, or a
caller-selected user. Only Accounting Dimension configuration is read through
`get_all`. Master/source list queries preserve field-level visibility; full
documents are loaded only for document permission checks, not for enrichment.
Every request has a fresh permission cache. Restricted source documents remove
their GL rows before opening, movement, pagination and total calculations.

No upstream implementation has been copied into this app. The development
reference cache under `.cache/upstream` is excluded from distribution.
