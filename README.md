# Reckon Accounts

A reusable Frappe app providing Tally-oriented accounting reports and navigation
over ERPNext. App name: `reckon_accounts`.

Targets: Frappe/ERPNext **15 and 16**, using matching major versions.

## Current status

Scope direction: implement Tally accounting capabilities missing from ERPNext and
reuse existing standard reports. See [report scope and gap checklist](REPORT_SCOPE.md).

Source implementation now includes 23 custom report views: three ledger views and
20 transaction books, registers, summaries and exception/funds-flow views. See
[the delivered report catalog](REPORT_CATALOG.md). All belong to **Reckon Accounts**;
report names omit the app prefix. **General Ledger Custom** distinguishes the
Tally presentation from the standard ERPNext General Ledger. Shared services
provide permission checks, dimensions, pagination and full CSV export.

Local unit and report-control tests pass. Live installation, browser verification,
ERPNext reconciliation and performance tests on both versions remain pending.
This is a development build, not an accepted production release. See
[Phase 1 validation and remaining gates](PHASE1_VALIDATION.md).

The app does not create a second accounting engine, duplicate accounting masters,
modify ERPNext core, or directly post GL entries.

## Development

[DEVELOPMENT.md](DEVELOPMENT.md) for the dual-version development plan and
installation workflow. Distribution licensing must be decided before publication;
this development build does not grant a new license.

## Specifications

- [Accounting rules](ACCOUNTING_RULES_ADDENDUM.md)
- [Discovery and Milestone 1 plan](RECKON_ACCOUNTS_PHASE1_DISCOVERY.md)
- [Architecture](ARCHITECTURE.md)
- [Inspected upstream contracts](UPSTREAM_CONTRACTS.md)

## Report use

Open **Reckon Accounts** in Desk and choose a report. Only Company, From Date
and To Date are mandatory. Leave account, party and group filters blank for all
permitted records in scope. Group Summary without a group shows account-level
summaries; selecting a group enables its hierarchy rollup. Funds Flow opens
without group selections and explains that figures cannot be calculated until
both working-capital groups are supplied. Optional filters still validate their
linked identities, company ownership and currency compatibility.

Use **Dimensions** for multiple selections and explicit blank values. Selecting
a voucher or payment type restricts balances as well as rows. **Export Full Ledger**
exports every permitted entry in one bounded result, including headings and filter
context. The initial adapter rejects scopes above 5,000 candidate GL rows instead
of returning incomplete balances.
