# Phase 1 validation and handoff

Updated 2026-09-14. Phase 1 source implementation is available; full milestone
acceptance remains pending live installation and reconciliation on both supported
major versions. No production installation or accounting changes were performed.

## Delivered source

- 23 custom Script Reports and workspace links; see [report catalog](REPORT_CATALOG.md).
- Prefix-free report names; General Ledger Custom avoids the standard report name.
- Strict filters for explicit dates, Fiscal Year, company, accounts/groups, parties,
  vouchers, payment type, Finance Book, dimensions, currency and pagination.
- Runtime metadata checks and permission-scoped tree expansion; disabled or unknown
  dimensions fail explicitly. Multi-selection and blank dimension values are supported.
- Company currency by default; account currency requires one non-group account.
- Account/party sections, mandatory party-above-account headings, stable
  date/creation/name ordering, opening, movement, closing and page carry-forward.
- Permission-aware master and source enrichment, real voucher identities,
  scope-preserving account drill-down, narration, and receipt/return display labels.
- Full server-generated CSV with permission checks, numeric amounts, section
  headings, filter context and formula-safe text cells.
- Source tests, client control tests, opt-in posting/reconciliation tests, and a
  source-check CI workflow for Python 3.12/3.14. CI has not been dispatched.

## Scope and operational limits

This first implementation materializes at most 5,000 candidate GL records and
checks at most 2,000 referenced master/source identities. Exceeding a bound raises
an error; it never returns a partial ledger. Date bounds preserve required opening
history, so reducing the period may not reduce the candidate set. Narrow account
or party scope instead. Finance Book/dimension matching happens after the bounded
GL read, before permission-approved rows are aggregated.

Master visibility is queried in batches of up to 200 names. Document permission
hooks still require per-document reads. Latency and SQL query counts have not been
benchmarked on a site; these bounds are not performance claims. Large background
exports and database-level aggregate pagination remain future optimization work.

Each full export uses one materialized GL result, without re-querying separate
pages. Separate refresh/page requests can change after backdated postings; no
cross-request snapshot is promised. Standard framework export/printing is marked
as a page view; the report's Export action invokes the full CSV export.

Particulars show other permitted accounts only within the report scope. They are
labelled accordingly. The source voucher supplies full permitted details; no
pairwise allocations are inferred. Restricted totals can intentionally differ
from a more permissive standard report, and this restriction is always disclosed.

## Local checks

Latest local result (2026-09-14): 90 Python tests passed; 8 live integration tests
skipped because Frappe is not installed. All 6 JavaScript control tests passed.
These are local source checks, not a live installation or reconciliation result.

Run from the repository with Python 3.12 or 3.14 and Node available:

```sh
python -m unittest discover -s reckon_accounts/tests -v
node --test reckon_accounts/tests/test_report_controls.cjs
ruff check reckon_accounts
python -m build --no-isolation
git diff --check
```

Build dependencies: `build` and `flit_core>=3.4,<4`. Runtime Frappe/ERPNext is
supplied by Bench. The integration suite skips when Frappe is unavailable; a
successful source run must not be reported as successful live reconciliation.

## Disposable bench gate (run for each major version)

Use separate Linux benches with matching ERPNext/Frappe majors. The current
Windows host has no usable Bench, Docker or WSL environment. A real customer site
is not required. Record the exact commits and installed app list for each test.

From the development bench, replace the placeholders:

```sh
bench get-app /absolute/path/to/Reckon-Accounts
bench --site <disposable-site> install-app reckon_accounts
bench build --app reckon_accounts
bench --site <disposable-site> set-config allow_tests true
bench --site <disposable-site> set-config reckon_accounts_test_site true
bench --site <disposable-site> run-tests --app reckon_accounts --module reckon_accounts.tests.integration.test_phase1
bench --site <disposable-site> migrate
```

The opt-in tests create isolated companies, accounts, customers, Journal Entries,
Payment Entries and a restricted user through standard document APIs, then roll
back. They never insert GL Entry rows directly. They compare independently specified
balances and the standard ERPNext General Ledger. Run only on a disposable site.

Additional live acceptance checks remain required:

1. Open each report, change filters, page through multi-account parties, use Other
   with/without blank-party filtering, and verify party/account headings in print.
2. Exercise available Employee/Shareholder and custom Party Types; verify unsupported
   types fail and historical accounts come from posted activity.
3. Post Finance Book, Cost Center, Project and custom-dimension examples; verify
   group descendants, disabled dimensions, blank/multiple selections and permissions.
4. Reconcile opening boundaries, opening vouchers beyond To Date, fiscal periods,
   cancellations/amendments and Period Closing Vouchers with the installed GL.
5. Test account/dimension/company restrictions, source-document and field-level
   restrictions, searches, narration, links, summaries and full export under restricted
   users. Confirm export denial separately from report read access.
6. Compare every exported entry and section total with a full permitted reference
   dataset, including account currency and concurrent backdated refreshes.
7. Measure report latency and SQL count on a representative bounded dataset. Verify
   limit errors disclose no excluded record names or counts.
8. Verify migration and clean uninstall on the disposable site. Do not publish a
   release until these gates pass and distribution licensing is decided.

## Milestone gate

Phase 1 is **not yet accepted**: both live version runs, browser QA, performance
measurement and uninstall checks remain unexecuted. Continue these gates when a
disposable bench is available. Milestone 2 has not been started.
