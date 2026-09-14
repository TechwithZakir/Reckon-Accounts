# Reckon Accounts — accounting rules addendum

Status: proposed implementation defaults following prompt review. Installed-version behavior must be verified during discovery. These decisions refine the master prompt; they do not authorize production changes or Milestone 1.

## 1. Release scope

The master prompt describes the complete reporting release. The first usable delivery comprises a minimal workspace, shared reporting services, Party Ledger, Account Ledger, and General Ledger. Preserve the original milestone numbering and approval gates. Dashboard and migration remain later work.

Reconciliation tests start with the first ledger implementation. Milestone 9 delivers the consolidated reconciliation interface, not the first correctness checks.

## 2. Ledger arithmetic

- Raw signed balance = debit minus credit. Positive is Dr, negative is Cr, and zero has no required Dr/Cr suffix.
- Account nature never reverses raw ledger arithmetic. Financial-statement presentation follows the installed standard report.
- Opening and closing debit/credit columns represent the positive/negative sides of the net balance, not lifetime gross turnover. Period debit/credit represent gross movement.
- At account/party detail level: closing = opening + period debit - period credit.
- Aggregate debit/credit balance columns sum the detail-side amounts; do not silently net different parties together.
- Use installed currency precision and consistent rounding. Preserve numeric values for export; Dr/Cr is display formatting.

Opening-voucher, period-closing-voucher, fiscal-year, and cancellation treatments must match each installed reference report. A universal pre-date sum must not be reused as the financial-statement policy. Document any opening entries classified into opening rather than period movement.

## 3. Filter semantics

Balance-scope filters include company, account/group, party type/party, currency mode, Finance Book, and accounting dimensions. Apply the same scope to opening, movement, closing, exports, and reconciliation.

For Milestone 1, Voucher Type, Voucher No, and Payment Type restrict the calculation scope as well as rows. When used, label balances as filtered balances and show active filters prominently. They must never be presented as the unrestricted party/account balance. This avoids an implicit mixture of full opening and partial movement.

Date precedence: explicit From/To Dates define the period. A selected Fiscal Year must be compatible with that period; reject contradictory input rather than silently replacing dates. As-of reports use To Date independently of period movement.

Define group descendants, disabled dimensions, blank values, multiple selections, and company ownership using verified metadata. Finance Book blank/default inclusion must be an explicit option consistent with the installed report. Do not silently ignore unsupported filters.

## 4. Accounts, parties, and particulars

- The header always places the party name immediately above the ledger account. No setting may hide this mandatory layout.
- Ledger Account means the account on the selected GL row. Counterparty Account/Particulars means the other side(s) of the voucher. Keep these distinct.
- Multi-account parties receive separate account sections and running balances. Optional combined totals use company currency only.
- Historical account selection comes from posted activity; current party defaults are selection aids only.
- Proposed Other behavior: an account-ledger view including all posted rows for the selected account. Offer an explicit Only Entries Without Party filter if needed. Never create a synthetic party. This resolves the master prompt's conflicting descriptions in favor of a reconcilable full account view.
- Supported party types are discovered from the installed site. Unsupported Employee/Shareholder capabilities must be reported, not fabricated.
- A voucher may have multiple counterpart accounts. Show Multiple Accounts with a permitted detail view rather than choosing an arbitrary account or inventing pairwise allocations.
- Keep source DocType/name separate from display labels such as Receipt, Credit Note, and Debit Note. Drill-down uses the real source identity.

## 5. Currency and outstanding

Milestone 1 defaults to company currency. Account currency is available only for a compatible single-currency scope. Arbitrary presentation-currency conversion is deferred until an exchange-rate policy is specified.

Outstanding reports follow the installed ERPNext as-of report using the currently recorded allocations and its cutoff semantics. Reproducing exactly what the database showed at a historical point in time is a separate audit/snapshot requirement and is not promised.

Show GL closing balance and allocated outstanding as distinct measures. Explain differences from advances, unallocated payments, adjustments, exchange effects, and report scope where applicable. Never use current invoice outstanding as a substitute for historical outstanding.

Ageing defaults: Current = due today or later; overdue buckets = 1–30, 31–60, 61–90, 91–120, 121+ calendar days. Default basis is due date. Missing-date fallback and treatment of credits/advances must match and be documented against the installed reference report. If posting-date ageing is offered, label it explicitly.

Sales/Purchase registers must label current outstanding/status as Current. An As Of variant requires historical calculation and must not reuse current status fields silently.

## 6. Books and registers

Day Book filters select matching vouchers, then show complete permitted voucher lines. If permission scope prevents showing a complete voucher, identify the result as restricted; never expose excluded lines or claim the visible subset balances. Paginate by voucher so a voucher is not split unnecessarily.

Contra classification must distinguish transfer principal, charges, and exchange differences. Do not infer one From/To pair for a many-to-many voucher. Keep the source voucher and line details available. Cash/bank receipts and payments are account movements; aggregated internal transfers must not be mislabelled as external cash flow.

Bank Account master and bank GL Account are separate concepts. Define their mapping after inspecting the site; do not assume a one-to-one mapping.

## 7. Pagination and exports

Choose a stable order based on posting date and a verified unique tie-breaker. Return full-scope opening, full-period totals, full-scope closing, page carry-forward, and pagination metadata separately from page rows. Page 2 starts from its carry-forward balance.

Recalculate on refresh; define behavior for concurrent backdated postings. Do not promise snapshot consistency without implementing it. For multi-page exports, use one consistent dataset/cutoff mechanism supported by the environment.

Proposed default page size: 100, maximum: 500. These are product defaults, not measured performance claims. Full exports must be explicit, permission-checked, and server-generated; large exports may need background execution. Never silently export only the displayed page as the full report.

Do not sum running-balance or opening/closing rows with generic report totals. Export formatting must preserve numeric debit/credit values and the mandatory heading layout.

## 8. Security and reconciliation

All report entry points share server-side filter validation and an explicit row/aggregate permission scope. Whitelisting, parameterized SQL, and DocType-level permission checks alone do not establish full row authorization. Validate metadata-derived SQL identifiers against trusted allowlists.

Apply equivalent protection to summaries, name searches, narration enrichment, drill-down, and exports. A missing permission must not become an unrestricted query. Test a restricted user and an authorized accountant; verify company and account/dimension restrictions, including inference through totals.

Reconciliation uses identical dates, scope, currency, opening treatment, and Finance Book options. Compare account/party groups as well as final totals using installed precision. Explain intentional display differences. A self-comparison through the same Reckon function is not sufficient: include independently specified expected balances and standard ERPNext outputs.

## 9. Structure and completion corrections

- Workspace owns the preferred reckon-accounts route; use a distinct dashboard/custom-page route if required by the installed routing model.
- Preserve the generated Frappe package structure; public assets belong at the app package level.
- Add Bank Summary to the directory inventory and definition of done.
- Add reconciliation interface and dashboard to later milestone inventories explicitly.
- Wrap reused ERPNext internal functions behind version-specific adapters and test supported versions.
- Set measurable latency, dataset, query-count, and export-size targets during environment discovery. Do not advertise million-row performance without a representative benchmark.

## Reference context

These references informed the prompt review but do not establish the installed site's behavior:

- Frappe Database API: https://docs.frappe.io/framework/user/en/api/database
- ERPNext Immutable Ledger: https://docs.frappe.io/erpnext/immutable-ledger-in-erpnext
- ERPNext Payment Ledger: https://docs.frappe.io/erpnext/payment_ledger
