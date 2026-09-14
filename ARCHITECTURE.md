# Architecture

Reckon Accounts is a reusable reporting app targeting matching Frappe/ERPNext 15
and 16 installations. A customer's site is not a development prerequisite.

Call path: Script Report/export -> report authorization -> filter parsing -> runtime
metadata and selected-master checks -> permission-aware GL read -> source/master
authorization -> grouped ledger -> page or full CSV.

Implemented now:

- `reckon_accounts/hooks.py`: app registration and required ERPNext app.
- `reckon_accounts/accounting/filters.py`: strict structural parsing of company,
  explicit dates, account/party/voucher scope, currency, dimensions and pagination.
  Rejects unknown options and conflicting filters. Voucher restrictions carry a
  filtered-balance label and remain part of the shared calculation scope.
- `reckon_accounts/reckon_accounts`: Frappe module and minimal workspace metadata.
- `reckon_accounts/accounting/balances.py`: finite Decimal amounts and signed
  balance arithmetic without database dependencies or implicit rounding.
- `reckon_accounts/accounting/ledger.py`: in-memory pagination for a single
  preauthorized account/currency scope, with date/identity ordering, running
  balances, page carry-forward and full-period totals. Rejects duplicate identities
  and invalid pages; preserves signed reversal movements and source precision.
- `accounting/dimensions.py`: runtime identifier allowlists and permitted tree expansion.
- `accounting/permissions.py`: list visibility plus document read checks, with request-local caching.
- `accounting/adapters.py`: Frappe 15/16 query signatures, schema checks, opening and
  Finance Book policies, company/currency/fiscal validation and authorized postings.
- `accounting/party.py`: permitted names, voucher display labels and in-scope particulars.
- `accounting/service.py`: multi-section running balances, page carry-forward and detail-side totals.
- `accounting/reporting.py`: report columns, summaries, scope disclosure and full CSV rendering.
- `api.py`: permission-checked full export, metadata and selection searches.
- `public/js/report_filters.js`: shared filters, dimension dialog, safe formatting and drill-down.
- `reckon_accounts/report/`: three thin Script Report entry points and registration metadata.

The balance functions operate on an already filtered, authorized, single-currency
scope. They do not decide which records constitute an opening balance. Adapters
must apply installed-version accounting rules and precision before presentation.
The standalone pagination helper remains independently usable. The report service
adds pagination across sections. Both materialize their supplied rows; separate
requests do not provide snapshot consistency.

Filter parsing does not verify master existence, company ownership or permissions.
The adapter validates Fiscal Year, Finance Book, dimensions, group expansion and
account currency against runtime metadata. Optional link inputs must be omitted
or null when unselected. The parser is the input boundary;
constructing a filter dataclass directly is not validation or authorization.

Only Accounting Dimension configuration uses `get_all`. Financial/master/source
queries use `get_list` with permissions enabled and document checks. Full documents
are loaded only for authorization; enrichment uses field-filtered list results.
Required fields missing through field permissions cause a closed failure. Raw
`against` is not exposed because it can name excluded accounts. Source links use
the original DocType/name. Export separately requires GL export permission.

The first adapter caps candidate GL rows at 5,000 and referenced identities at
2,000. It batches master visibility in groups of 200, while document permission
hooks retain per-document reads. Limit errors never return partial balances.
Latency, query counts and large-scale performance have not been measured on a site.

Version-specific functions must be isolated behind adapters verified against pinned
upstream revisions. Never assume current upstream branches match every deployed
minor version. No broad core overrides, posting hooks, custom balance tables, or
global Desk assets are needed for the foundation.

Company, chart of accounts, party types, custom fields and dimensions are runtime
metadata. Workspace roles provide navigation visibility, not query authorization.

See [upstream contracts](UPSTREAM_CONTRACTS.md) and
[remaining validation gates](PHASE1_VALIDATION.md). Milestone 2 is not implemented.
