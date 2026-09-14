# Reckon Accounts — Phase 0 discovery

Historical Phase 0 findings. Updated status (2026-09-13): the user authorized
continuing all Phase 1 tasks. Source implementation now includes all three ledgers
and their shared adapters/services. Installed-site discovery and live acceptance
remain pending a disposable bench. See [PHASE1_VALIDATION.md](PHASE1_VALIDATION.md)
and [UPSTREAM_CONTRACTS.md](UPSTREAM_CONTRACTS.md) for current evidence and gates.

Inspection date: 2026-09-12. Scope: read-only local environment checks plus documentation changes. No production data was accessed or changed. No app was generated, installed, migrated, built, or restarted.

## 1. Verified environment findings

| Item | Evidence / result |
| --- | --- |
| Repository | `D:\zakir\FrapeeProject\Reckon-Accounts` |
| Initial contents | `.git`, `.gitattributes`, and an 80-byte `README.md` |
| Initial working tree | `git status --short` returned no changes |
| Existing reckon_accounts implementation | None in this repository |
| Applicable AGENTS.md | None found in repository or checked ancestors (`D:\`, `D:\zakir`, `D:\zakir\FrapeeProject`) |
| Bench/site | Not identified in the bounded project-directory search |
| Bench command | Not available on this PowerShell PATH |
| Frappe / ERPNext versions | Unverified; no installed source/site located |
| Python | `python` not available on this PATH; runtime elsewhere remains possible |
| Node | Host `node --version`: `v24.14.1`; not evidence of the target bench runtime or compatibility |
| Database | `mariadb` / `mysql` commands unavailable on PATH; server/version unknown |
| Docker | Command unavailable on PATH; does not establish whether a remote container exists |
| WSL | `wsl --list --quiet` reports Windows Subsystem for Linux is not installed |
| Installed custom apps | Unknown; neighboring repositories do not prove site installation |

Searched under `D:\zakir\FrapeeProject` for `apps.txt`, `common_site_config.json`, `site_config.json`, key accounting schema JSON files, hooks, and compose manifests. Found neighboring custom-app hooks but no bench/site markers or requested accounting schemas. Also listed directories in `C:\Users\User\Documents\ChatGPT`; this was not an exhaustive machine-wide search. No site configuration secrets were read.

## 2. Nearby custom-app observations

Potential compatibility review candidates, not confirmed installed conflicts:

- `Reckon-Easy-ERP/reckon_easy_erp/hooks.py`: requires ERPNext and HRMS; install/migrate handlers; fixtures for Easy ERP roles, custom fields, and Custom DocPerm; global CSS/JS; Sales Invoice and Payment Entry list scripts; permission hooks for its own Easy ERP User Access DocType.
- `Reckon-Export-Import/reckon_export_import/hooks.py`: requires ERPNext; install/migrate workspace synchronization and fixtures.
- `naidapa_theme/naidapa_theme/hooks.py`: global assets and Workspace form script.
- `financial_ai_agent/financial_ai_agent/hooks.py`: fixtures and permission hooks. Their effective installed behavior was not assessed.
- Other neighboring repositories include CRM and Salesforce integrations. No claim of full code audit is made.

On the target site, inspect installed app order, effective merged hooks, workspace routes, Custom Fields, Property Setters, Custom DocPerm, Client/Server Scripts, and role/user restrictions. Review hook implementations only for apps actually installed. Do not change other apps during discovery.

## 3. Schema and behavior verification still required

Every field below is a candidate to inspect, not a verified field contract.

| DocTypes | Required inspection |
| --- | --- |
| GL Entry | Company, dates, account, party, voucher identifiers, debit/credit in company/account currency, opening/cancellation markers, Finance Book, dimensions, ordering fields, indexes |
| Payment Ledger Entry | Allocation references, amounts/currencies, effective dates, delinking/cancellation treatment, historical outstanding behavior |
| Account, Company | Account hierarchy, root/type/currency, company ownership, defaults, default Finance Book |
| Payment Entry, Payment Entry Reference | Party-type options, accounts, payment type, references, allocation and exchange fields, remarks |
| Journal Entry, Journal Entry Account | Entry types, opening entries, account/party fields, references, dimensions, remarks |
| Sales/Purchase Invoice and item tables | Return identity, dates, amounts/currencies, current outstanding/status, dimensions and narration |
| Customer, Supplier, Employee, Shareholder | Availability, display-name fields, configured account mappings, supported posting behavior |
| Bank Account, Mode of Payment, Mode of Payment Account | Company bank GL mappings, defaults and reference metadata |
| Cost Center, Project, Accounting Dimension | Installed dimensions, generated fields, hierarchy, mandatory rules, restrictions |
| Finance Book, Fiscal Year, Currency | Default/blank-book semantics, fiscal scope, precision |
| Asset, Asset Category, Budget | Later-phase relevance and availability; no new posting logic |

Party types, accounting dimensions, custom fields, cancellation representation, party-account resolution, and historical outstanding are currently UNVERIFIED. Inspect metadata through the target site's supported read APIs and installed source. Do not infer support solely from the master prompt.

## 4. Standard report reuse investigation

No exact installed helper function or signature has been verified. Discovery must inspect:

| Standard report | Determine |
| --- | --- |
| General Ledger | Query scope, permission handling, ordering, opening/cancellation/currency/Finance Book options |
| Trial Balance | Account tree aggregation, opening and period-closing treatment |
| Accounts Receivable / Accounts Payable | Shared implementation, Payment Ledger use, cutoff/allocation/ageing semantics |
| Profit and Loss / Balance Sheet | Shared financial-statement functions, fiscal periods, retained earnings, precision and sign presentation |
| Cash Flow | Applicable cash-account and statement helpers; investigation only, not an extra deliverable |
| Bank Reconciliation Statement | Book balance versus reconciliation/clearance date behavior |

Record installed commit/version, exact module/function, signature, expected filters, result structure, permission assumptions, and test coverage for each chosen reuse point. Use a narrow compatibility adapter rather than copying standard reports or promising unverified APIs.

## 5. Permissions and performance

Permission policy must cover company, report/DocType access, User Permissions, applicable account/dimension restrictions, and source-document enrichment. Check the installed standard report's behavior and ensure Reckon does not broaden access. Parameterized values do not supply row permissions; metadata identifiers need allowlisting.

Database indexes and query plans could not be inspected. Once connected, inspect existing GL indexes and representative filtered query plans without changing indexes. Avoid unbounded production scans. Establish a staging dataset, latency targets, default/max page sizes, export limits, and bounded enrichment query counts. Measure before proposing schema changes.

## 6. Proposed Milestone 1 structure

Final module registration and generated scaffold depend on the verified Frappe version:

```text
<repository>/
  pyproject.toml
  reckon_accounts/
    __init__.py
    hooks.py
    modules.txt
    patches.txt
    accounting/
      filters.py
      permissions.py
      dimensions.py
      balances.py
      ledger.py
      party.py
      adapters.py
    public/
      js/report_filters.js
      js/report_formatters.js
      css/reckon_accounts.css
    reckon_accounts/                 # Frappe module
      report/
        party_ledger/
        account_ledger/
        general_ledger_custom/
      workspace/reckon_accounts/
    tests/
      test_balances.py
      test_party_ledger.py
      test_account_ledger.py
      test_general_ledger.py
      test_permissions.py
```

Add a custom page/API only if the installed report framework cannot meet pagination and heading requirements cleanly. Avoid generating all future reports, unused APIs, or optional Settings prematurely. Declare ERPNext as a dependency using the verified version's supported mechanism.

## 7. Exact proposed Milestone 1 work order

1. Finish installed-site discovery and freeze the verified version/filter contract. Resolve addendum deviations against installed standard reports.
2. After the milestone gate, generate the supported app scaffold on a development bench. Preserve the repository documentation. Do not install on production as part of development.
3. Implement validated report scope and permission enforcement before ledger access. Include company/account/party compatibility, dates, dynamic dimensions and Finance Book.
4. Implement company-currency balance services with verified opening/cancellation semantics, stable ordering, grouped balances, page carry-forward and full-scope totals.
5. Implement batch party names and voucher enrichment under the same permission policy. Preserve source identities independently of Tally display labels.
6. Deliver Party Ledger first: mandatory party/account heading, multiple-account sections, Other account view, numeric debit/credit, Dr/Cr balance, narration and source links.
7. Build Account Ledger and General Ledger over the same services. Register the minimal workspace with distinct routes and permitted links.
8. Validate supported screen pagination and full export paths; preserve filter context in drill-downs.
9. Run controlled posting fixtures on a development/test site using standard transactions only. Reconcile to the installed General Ledger plus independent expected balances.
10. Produce the milestone completion report with files, tests, reconciliation, assumptions and unresolved issues. Stop for approval before Milestone 2.

Minimum acceptance cases: opening/debit/credit/zero/closing; same-day ordering; multiple pages; multi-account party; supported party types; Other behavior; cancellation/amendment; opening and period-close boundaries; foreign-currency account shown in company currency; Finance Book blank/default behavior; dynamic dimensions; restricted users; filtered balance labels; voucher links; screen/export parity. Unsupported capabilities must be explicit failures or documented limits, never silently omitted.

## 8. Risks and gate status

Blocking: target bench/site and access method unknown; installed versions, schemas, functions, permissions, dimensions and indexes unverified. Therefore live reconciliation and accounting integration tests were not run.

Other risks: substantial full-release scope; ambiguity resolved only provisionally by the addendum; internal ERPNext helper compatibility; report pagination/export integration; historical allocation versus snapshot expectations; possible global UI and permission customizations from installed neighboring apps.

Needed input: target local bench path, or server/site address and available access method. Do not place passwords or private keys in this document. Once available, continue Phase 0 with read-only inspection and replace unverified entries with evidence.

## 9. Discovery summary

- FRAPPE VERSION: unverified.
- ERPNEXT VERSION: unverified.
- SITE: not identified.
- CUSTOM APPS: installed list unverified; local candidate repositories noted above.
- ACCOUNTING DIMENSIONS: unverified.
- PARTY TYPES: unverified.
- KEY STANDARD FUNCTIONS TO REUSE: investigation targets listed; none verified yet.
- RISKS: missing environment access and installed accounting contracts.
- RECOMMENDED MILESTONE-1 STRUCTURE: shared reporting services, three ledger reports, minimal workspace, version adapter and integration tests.
- INITIAL RESULT: local discovery documented; installed-site discovery was incomplete.
  Phase 1 source has since been implemented under the user's subsequent instruction;
  live milestone acceptance is still pending.
