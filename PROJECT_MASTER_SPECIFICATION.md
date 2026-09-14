# ============================================================
# PROJECT MASTER PROMPT
# RECKON ACCOUNTS
# TALLY-ORIENTED ACCOUNTING & REPORTING APP FOR FRAPPE/ERPNEXT
# ============================================================

PROJECT NAME:
Reckon Accounts

FRAPPE APP NAME:
reckon_accounts

PRODUCT BRANDING:
ReckonERP / Reckon Accounts

PRIMARY OBJECTIVE:
Build a custom accounting user experience and advanced accounting reporting application on top of the existing ERPNext/Frappe accounting engine.

The application must provide a Tally-oriented accounting experience for accountants while continuing to use standard ERPNext accounting documents, posting logic, GL Entry, Payment Ledger Entry, Account, Party, Sales Invoice, Purchase Invoice, Payment Entry, Journal Entry, assets and accounting dimensions.

DO NOT create a second accounting engine.

DO NOT duplicate ERPNext accounting data.

DO NOT modify ERPNext core.

DO NOT write directly to GL Entry except through normal ERPNext accounting transactions.

DO NOT break existing ERPNext reports or workflows.

The custom application should function as:

1. Accounting UX layer
2. Tally-style reporting layer
3. Advanced ledger/reporting engine
4. Financial analysis layer
5. Drill-down layer
6. Migration layer in later phases

All accounting transactions must continue to use standard ERPNext accounting functionality.

# ============================================================
# 1. IMPORTANT DEVELOPMENT PRINCIPLES
# ============================================================

The following rules are mandatory.

1. Inspect the installed Frappe and ERPNext versions before coding.

2. Never assume fields exist without checking the installed DocTypes.

3. Never modify ERPNext core Python, JavaScript, JSON, reports or DocTypes.

4. Use hooks, custom pages, Script Reports, Query Reports, whitelisted APIs,
   custom DocTypes where genuinely required and custom workspace/navigation.

5. Continue using ERPNext standard DocTypes including:

   Company
   Account
   Customer
   Supplier
   Employee
   Shareholder
   Payment Entry
   Payment Entry Reference
   Journal Entry
   Journal Entry Account
   Sales Invoice
   Sales Invoice Item
   Purchase Invoice
   Purchase Invoice Item
   GL Entry
   Payment Ledger Entry
   Bank Account
   Mode of Payment
   Mode of Payment Account
   Cost Center
   Project
   Fiscal Year
   Currency
   Finance Book
   Accounting Dimension
   Asset
   Asset Category
   Budget

6. GL Entry must be considered the primary source of truth for posted ledger
   transactions unless a particular ERPNext report intentionally uses another
   standard accounting source such as Payment Ledger Entry.

7. Submitted documents must remain immutable according to ERPNext rules.

8. Cancelled GL Entries must not be treated as active transactions.

9. Reports must respect:
   - Company
   - Fiscal Year
   - Currency
   - Finance Book
   - Cost Center
   - Project
   - Custom Accounting Dimensions
   - User permissions

10. Reports must reconcile against ERPNext standard accounting reports.

11. Every report must use shared accounting services instead of implementing
    independent balance formulas.

12. All server-side queries must be parameterized and safe.

13. Do not load thousands of GL Entries into the browser.

14. Use efficient server-side aggregation, filtering and pagination.

15. Write automated tests for all important accounting calculations.

# ============================================================
# 2. PHASE 0 - DISCOVERY
# ============================================================

DO NOT START PRODUCTION IMPLEMENTATION BEFORE DISCOVERY.

First inspect the installed site.

Determine:

- Frappe version
- ERPNext version
- Python version
- Node version
- MariaDB/MySQL version if accessible
- Installed custom apps
- Existing accounting customizations
- Existing hooks that affect accounting
- Custom Fields on accounting DocTypes
- Accounting Dimensions
- Party Types supported by Payment Entry
- Existing reports that can be reused safely

Inspect schemas for:

GL Entry
Payment Ledger Entry
Account
Payment Entry
Payment Entry Reference
Journal Entry
Journal Entry Account
Sales Invoice
Purchase Invoice
Customer
Supplier
Employee
Shareholder
Bank Account
Mode of Payment
Cost Center
Project
Finance Book

Inspect ERPNext standard reports:

General Ledger
Trial Balance
Accounts Receivable
Accounts Payable
Balance Sheet
Profit and Loss Statement
Cash Flow
Bank Reconciliation Statement

Document findings in:

RECKON_ACCOUNTS_PHASE1_DISCOVERY.md

The discovery file must contain:

1. Installed versions
2. Relevant DocTypes
3. Relevant fields
4. Current ERPNext reporting functions that can be reused
5. Existing accounting dimensions
6. Permission considerations
7. Performance considerations
8. Custom app conflicts
9. Recommended implementation structure
10. Risks
11. Final Phase-1 implementation plan

DO NOT modify production accounting data during discovery.

# ============================================================
# 3. APP STRUCTURE
# ============================================================

Create or use:

apps/reckon_accounts/

Recommended structure:

reckon_accounts/
    hooks.py
    modules.txt
    patches.txt

    reckon_accounts/

        accounting/
            __init__.py
            ledger.py
            balances.py
            party.py
            vouchers.py
            cash_bank.py
            outstanding.py
            ageing.py
            financial_statements.py
            permissions.py
            dimensions.py
            utils.py
            reconciliation.py

        api/
            accounting.py
            reports.py
            dashboard.py

        report/
            reckon_party_ledger/
            reckon_account_ledger/
            reckon_party_summary/
            reckon_account_head_party_ledger/
            reckon_general_ledger/
            reckon_day_book/
            reckon_cash_book/
            reckon_bank_book/
            reckon_receipt_register/
            reckon_payment_register/
            reckon_contra_register/
            reckon_journal_register/
            reckon_sales_register/
            reckon_purchase_register/
            reckon_receivable_summary/
            reckon_payable_summary/
            reckon_bill_wise_receivable/
            reckon_bill_wise_payable/
            reckon_receivable_ageing/
            reckon_payable_ageing/
            reckon_trial_balance/
            reckon_profit_and_loss/
            reckon_balance_sheet/

        page/
            reckon_accounts/
            reckon_accounts_dashboard/

        doctype/
            reckon_accounts_settings/

        public/
            js/
            css/

        tests/
            test_balances.py
            test_party_ledger.py
            test_general_ledger.py
            test_cash_book.py
            test_bank_book.py
            test_trial_balance.py
            test_receivable.py
            test_payable.py
            test_financial_statements.py

# ============================================================
# 4. RECKON ACCOUNTS WORKSPACE
# ============================================================

Create a dedicated workspace:

Reckon Accounts

URL or route should preferably be:

/app/reckon-accounts

The workspace must be simpler than the standard ERPNext accounting workspace.

Sections:

DASHBOARD

TRANSACTIONS
- Day Book
- Receipt Register
- Payment Register
- Contra Register
- Journal Register
- Sales Register
- Purchase Register

LEDGERS
- Party Ledger
- Account Ledger
- Account Head Wise Party Ledger
- Party Summary
- General Ledger

CASH & BANK
- Cash Book
- Bank Book
- Bank Summary

RECEIVABLES
- Customer Ledger
- Receivable Summary
- Bill Wise Receivable
- Receivable Ageing

PAYABLES
- Supplier Ledger
- Payable Summary
- Bill Wise Payable
- Payable Ageing

FINANCIAL STATEMENTS
- Trial Balance
- Profit & Loss
- Balance Sheet

TOOLS
- Accounting Reconciliation

Use the branding:

Reckon Accounts

Do not expose "ERPNext" unnecessarily in user-facing titles.

# ============================================================
# 5. COMMON REPORT FILTERS
# ============================================================

Develop reusable report filter helpers.

Standard filters should include as applicable:

Company
From Date
To Date
Fiscal Year
Account
Account Group
Party Type
Party
Payment Type
Voucher Type
Voucher No
Cost Center
Project
Finance Book
Currency

Also dynamically include installed Accounting Dimensions.

Examples may include:

Branch
Department
Business Unit
Region

Do not hardcode only known dimensions.

Use ERPNext/Frappe accounting-dimension metadata where possible.

# ============================================================
# 6. PARTY TYPES
# ============================================================

Party Ledger should support at minimum:

Customer
Supplier
Employee
Shareholder
Other

IMPORTANT:

Do not modify ERPNext Payment Entry merely to support "Other".

Existing standard party types should continue to use standard ERPNext party
fields.

For "Other", provide account-head-based ledger reporting.

Examples:

Electricity Expense
Rent Expense
Director Loan
Advance Account
Employee Advance
Other Receivable
Other Payable
Miscellaneous Account

"Other" is primarily a reporting concept in Phase 1.

Do not create artificial party records unnecessarily.

# ============================================================
# 7. PARTY LEDGER
# ============================================================

Create:

Reckon Party Ledger

This is one of the primary reports of the application.

FILTERS:

Company
From Date
To Date
Party Type
Party
Account Head
Payment Type
Voucher Type
Cost Center
Project
Finance Book
Currency
Accounting Dimensions

Optional:

Include Opening Balance
Include Zero Balance
Show Narration
Group By

PARTY TYPE:

Customer
Supplier
Employee
Shareholder
Other

Party field must change dynamically based on Party Type.

Example:

Party Type = Customer
Party link -> Customer

Party Type = Supplier
Party link -> Supplier

Party Type = Employee
Party link -> Employee

Party Type = Shareholder
Party link -> Shareholder

When Party Type = Other:

Allow account-head-based selection/reporting.

# ============================================================
# 8. PARTY LEDGER HEADER
# ============================================================

The report heading should clearly display:

Reckon Accounts

PARTY LEDGER

Company:
Period:
Party Type:
Party:
Account Head:
Currency:

Then prominently display:

PARTY NAME

Below it:

Account Head: <party account>

Example:

ABC Trading Ltd.
Accounts Receivable - RTL

The user specifically requires:

Party Name
then underneath
Account Head

This layout is mandatory.

# ============================================================
# 9. PARTY LEDGER COLUMNS
# ============================================================

Columns:

Date
Particulars
Voucher Type
Voucher No
Account Head
Payment Type
Debit
Credit
Balance
Remarks

Additional technical fields may be hidden:

Party Type
Party
Against
Against Voucher Type
Against Voucher
Cost Center
Project
Finance Book
Currency

Display voucher number as clickable.

Clicking the voucher must open the source ERPNext document.

Examples:

Payment Entry
Journal Entry
Sales Invoice
Purchase Invoice
Credit Note
Debit Note

# ============================================================
# 10. PARTY LEDGER BALANCE RULES
# ============================================================

Calculate:

Opening Debit
Opening Credit
Opening Balance

Period Debit
Period Credit

Closing Debit
Closing Credit
Closing Balance

Opening Balance:

All valid posted GL Entries before from_date
using the exact same:

Company
Account
Party Type
Party
Finance Book
Dimensions

filters.

Period transactions:

posting_date >= from_date
and
posting_date <= to_date

Closing:

Opening + Period Movement

Handle debit and credit balances properly.

Display:

50,000 Dr

or:

20,000 Cr

instead of ambiguous signed values where practical.

Create reusable function:

format_dr_cr_balance()

# ============================================================
# 11. PARTY LEDGER ROW DESIGN
# ============================================================

Rows should support Tally-like presentation.

Example:

01-09-2026
Sales Invoice
SINV-00031
Sales - RTL
Debit: 20,000
Balance: 70,000 Dr
Remarks: Annual software service

05-09-2026
Receipt
ACC-PAY-2026-0024
Dutch Bangla Bank - RTL
Credit: 15,000
Balance: 55,000 Dr
Remarks: Payment received

At bottom:

Opening Balance
Period Debit
Period Credit
Closing Balance

# ============================================================
# 12. ACCOUNT LEDGER
# ============================================================

Create:

Reckon Account Ledger

Filters:

Company
Account
From Date
To Date
Party Type
Party
Voucher Type
Cost Center
Project
Finance Book
Accounting Dimensions

Columns:

Date
Particulars
Voucher Type
Voucher No
Party
Against Account
Debit
Credit
Balance
Remarks

Show:

Opening Balance
Total Debit
Total Credit
Closing Balance

Use GL Entry as the source.

# ============================================================
# 13. ACCOUNT HEAD WISE PARTY LEDGER
# ============================================================

Create:

Account Head Wise Party Ledger

Filters:

Company
From Date
To Date
Account Head
Party Type
Party
Cost Center
Project
Dimensions

Columns:

Party Type
Party
Account Head
Opening
Debit
Credit
Closing

Example:

Account:
Accounts Receivable - RTL

ABC Ltd.
Opening 50,000
Debit 20,000
Credit 15,000
Closing 55,000 Dr

XYZ Ltd.
Opening 10,000
Debit 15,000
Credit 5,000
Closing 20,000 Dr

Clicking Party should open Reckon Party Ledger with:

Company
From Date
To Date
Party Type
Party
Account Head

already populated.

# ============================================================
# 14. PARTY SUMMARY
# ============================================================

Create:

Reckon Party Summary

Columns:

Party Type
Party
Account Head
Opening Debit
Opening Credit
Period Debit
Period Credit
Closing Debit
Closing Credit
Receivable
Payable

Filters:

Company
Period
Party Type
Account
Customer Group
Supplier Group
Territory
Cost Center
Project
Accounting Dimensions

Allow grouping by:

Party Type
Account Head
Customer Group
Supplier Group
Territory

# ============================================================
# 15. GENERAL LEDGER
# ============================================================

Create:

Reckon General Ledger

Do not simply embed the standard ERPNext report.

Use shared Reckon ledger services.

Filters:

Company
From Date
To Date
Account
Party Type
Party
Voucher Type
Cost Center
Project
Finance Book
Accounting Dimensions

Columns:

Date
Voucher Type
Voucher No
Particulars
Party
Against Account
Debit
Credit
Running Balance
Remarks

Display:

Opening Balance
Period Debit
Period Credit
Closing Balance

Support grouping by account.

Click account -> Account Ledger.

Click voucher -> source document.

# ============================================================
# 16. DAY BOOK
# ============================================================

Create:

Reckon Day Book

Purpose:

Provide Tally-style chronological presentation of all accounting vouchers.

Filters:

Company
Date
From Date
To Date
Voucher Type
Party Type
Party
Account
Cost Center
Project
User
Accounting Dimensions

Group entries by voucher.

Show:

Date
Voucher Type
Voucher Number
Party
Particulars
Debit Account
Credit Account
Debit
Credit
Remarks

Example:

12-09-2026

Receipt Voucher
ACC-PAY-2026-0021

Cash - RTL                 Dr     25,000
    ABC Customer           Cr     25,000

Being payment received from ABC Customer.

For multi-line Journal Entry:

show all debit and credit lines under the same voucher.

Voucher click must open original document.

Do not duplicate one voucher unnecessarily simply because it has multiple GL rows.

# ============================================================
# 17. CASH BOOK
# ============================================================

Create:

Reckon Cash Book

Automatically identify cash accounts.

Prefer standard Account metadata such as:

account_type = Cash

and inspect ERPNext's actual implementation.

Filters:

Company
From Date
To Date
Cash Account
Party Type
Party
Cost Center
Project
Dimensions

Columns:

Date
Voucher Type
Voucher Number
Party
Particulars
Account Head
Receipt
Payment
Balance
Remarks

Header summary:

Opening Cash
Total Receipts
Total Payments
Closing Cash

Calculation:

Receipt = cash account debit
Payment = cash account credit

But do not hardcode without accounting for opening entries,
currency and ERPNext behavior.

Support:

All Cash Accounts

or a particular cash account.

If All Cash Accounts selected:

allow account-level grouping.

# ============================================================
# 18. BANK BOOK
# ============================================================

Create:

Reckon Bank Book

Automatically identify bank accounts from Account metadata.

Filters:

Company
From Date
To Date
Bank Account
Party Type
Party
Mode of Payment
Reference Number
Cost Center
Project
Accounting Dimensions

Columns:

Date
Voucher Type
Voucher Number
Cheque / Reference
Party
Particulars
Receipt
Payment
Balance
Remarks

Summary:

Opening Bank Balance
Total Deposits
Total Withdrawals
Closing Book Balance

Receipt:

debit to bank

Payment:

credit to bank

Support:

All Bank Accounts

or a specific bank account.

# ============================================================
# 19. BANK SUMMARY
# ============================================================

Create:

Reckon Bank Summary

Columns:

Bank Account
Bank
Opening
Deposits
Withdrawals
Closing

Allow clicking a bank account to open Bank Book.

# ============================================================
# 20. RECEIPT REGISTER
# ============================================================

Create:

Reckon Receipt Register

Use primarily:

Payment Entry
payment_type = Receive

Also account for legitimate receipts through Journal Entry if required,
but clearly distinguish voucher source.

Filters:

Company
Period
Party Type
Party
Received Into
Mode of Payment
Reference Number
Cost Center

Columns:

Date
Receipt Number
Party Type
Party
Account Head
Received Into
Mode of Payment
Reference Number
Amount
Remarks

Click Receipt Number -> Payment Entry.

# ============================================================
# 21. PAYMENT REGISTER
# ============================================================

Create:

Reckon Payment Register

Use primarily:

Payment Entry
payment_type = Pay

Filters:

Company
Period
Party Type
Party
Paid From
Mode of Payment
Reference Number
Cost Center

Columns:

Date
Payment Number
Party Type
Party
Account Head
Paid From
Mode of Payment
Reference Number
Amount
Remarks

# ============================================================
# 22. CONTRA REGISTER
# ============================================================

Create:

Reckon Contra Register

Purpose:

Display transfers involving cash/bank accounts.

Examples:

Cash -> Bank
Bank -> Cash
Bank A -> Bank B
Cash A -> Cash B

Potential source documents:

Payment Entry
Journal Entry

Determine contra transactions from the actual accounting entries.

Columns:

Date
Voucher
From Account
To Account
Amount
Reference
Remarks

Do not create special accounting postings solely for the report.

# ============================================================
# 23. JOURNAL REGISTER
# ============================================================

Create:

Reckon Journal Register

Use submitted Journal Entry.

Filters:

Company
Period
Entry Type
Account
Party Type
Party
Cost Center
Project

Display voucher grouped.

Columns:

Date
Journal Number
Entry Type
Account
Party
Debit
Credit
Reference
Remarks

Click voucher -> Journal Entry.

# ============================================================
# 24. SALES REGISTER
# ============================================================

Create:

Reckon Sales Register

Use submitted Sales Invoice.

Filters:

Company
From Date
To Date
Customer
Customer Group
Territory
Sales Person
Cost Center
Project
Status

Columns:

Posting Date
Invoice
Customer
Customer Name
Net Total
Tax
Grand Total
Paid Amount
Outstanding Amount
Status

Optional later:

Gross Profit
Cost
Margin

Click Invoice -> Sales Invoice.

# ============================================================
# 25. PURCHASE REGISTER
# ============================================================

Create:

Reckon Purchase Register

Use submitted Purchase Invoice.

Filters:

Company
Period
Supplier
Supplier Group
Cost Center
Project
Status

Columns:

Posting Date
Purchase Invoice
Supplier
Supplier Name
Supplier Invoice No
Net Total
Tax
Grand Total
Paid
Outstanding
Status

# ============================================================
# 26. RECEIVABLE SUMMARY
# ============================================================

Create:

Reckon Receivable Summary

Use standard ERPNext receivable logic wherever practical.

Do not invent outstanding calculations if ERPNext already provides
reusable functions.

Columns:

Customer
Customer Name
Receivable Account
Opening
Invoices
Receipts
Credit Notes
Adjustments
Closing
Outstanding

Filters:

Company
Period
Customer
Customer Group
Territory
Receivable Account
Cost Center
Project
Dimensions

Click Customer -> Party Ledger.

# ============================================================
# 27. PAYABLE SUMMARY
# ============================================================

Create:

Reckon Payable Summary

Columns:

Supplier
Supplier Name
Payable Account
Opening
Purchases
Payments
Debit Notes
Adjustments
Closing
Outstanding

Click Supplier -> Party Ledger.

# ============================================================
# 28. BILL-WISE RECEIVABLE
# ============================================================

Create:

Reckon Bill Wise Receivable

Columns:

Customer
Invoice
Invoice Date
Due Date
Invoice Amount
Received
Credit Note
Adjustment
Outstanding
Age Days

Use standard Payment Ledger Entry/outstanding logic where applicable.

Do not calculate outstanding simply from Sales Invoice outstanding_amount
without understanding report cutoff date.

Historical reports must work correctly as of To Date.

# ============================================================
# 29. BILL-WISE PAYABLE
# ============================================================

Create:

Reckon Bill Wise Payable

Columns:

Supplier
Invoice
Supplier Invoice Number
Invoice Date
Due Date
Invoice Amount
Paid
Debit Note
Adjustment
Outstanding
Age Days

Historical cutoff date must be respected.

# ============================================================
# 30. RECEIVABLE AGEING
# ============================================================

Create:

Reckon Receivable Ageing

Default buckets:

Current
1-30
31-60
61-90
91-120
120+

Filters:

Company
As On Date
Customer
Customer Group
Receivable Account

Columns:

Customer
Total Outstanding
Current
1-30
31-60
61-90
91-120
120+

Allow drill-down to bill-wise receivable.

# ============================================================
# 31. PAYABLE AGEING
# ============================================================

Create:

Reckon Payable Ageing

Same design as Receivable Ageing.

Supplier
Total Outstanding
Current
1-30
31-60
61-90
91-120
120+

# ============================================================
# 32. TRIAL BALANCE
# ============================================================

Create:

Reckon Trial Balance

Columns:

Account
Opening Debit
Opening Credit
Period Debit
Period Credit
Closing Debit
Closing Credit

Respect account hierarchy.

Example:

Assets
    Current Assets
        Cash
        Bank
        Accounts Receivable

Support group expand/collapse if technically practical.

Filters:

Company
Fiscal Year
From Date
To Date
Finance Book
Cost Center
Project
Accounting Dimensions

Reconcile with ERPNext Trial Balance.

# ============================================================
# 33. PROFIT & LOSS
# ============================================================

Create:

Reckon Profit & Loss

Use ERPNext accounting hierarchy and accounting-period logic.

Display:

Income
Expenses
Net Profit / Loss

Columns:

Current Period
Previous Period
Variance
Variance %

Support:

Monthly
Quarterly
Yearly

if reasonable in Phase 1.

Filters:

Company
Fiscal Year
From Date
To Date
Cost Center
Project
Finance Book
Accounting Dimensions

Allow account drill-down.

Account -> Account Ledger.

Reconcile with ERPNext Profit and Loss.

# ============================================================
# 34. BALANCE SHEET
# ============================================================

Create:

Reckon Balance Sheet

Display:

Assets
Liabilities
Equity

Columns:

Current Period
Previous Period
Variance
Variance %

Support account hierarchy.

Drill-down:

Balance Sheet
 -> Account
 -> Account Ledger
 -> Voucher

Reconcile with standard ERPNext Balance Sheet.

# ============================================================
# 35. SHARED ACCOUNTING ENGINE
# ============================================================

Create reusable services.

Do NOT repeat accounting calculations inside each report.

Recommended functions:

get_gl_entries()

get_opening_balance()

get_period_balance()

get_closing_balance()

get_account_balance()

get_party_balance()

get_party_ledger()

get_account_ledger()

get_party_summary()

get_day_book()

get_cash_accounts()

get_bank_accounts()

get_cash_book()

get_bank_book()

get_receivable_summary()

get_payable_summary()

get_bill_wise_receivable()

get_bill_wise_payable()

get_receivable_ageing()

get_payable_ageing()

get_trial_balance()

get_profit_and_loss()

get_balance_sheet()

get_voucher_details()

get_against_accounts()

get_accounting_dimensions()

format_dr_cr_balance()

# ============================================================
# 36. STANDARD RESULT STRUCTURE
# ============================================================

Where practical, shared ledger functions should return structured data such as:

{
    "opening": {
        "debit": 0,
        "credit": 0,
        "balance": 0,
        "balance_type": "Dr"
    },

    "transactions": [],

    "period": {
        "debit": 0,
        "credit": 0
    },

    "closing": {
        "debit": 0,
        "credit": 0,
        "balance": 0,
        "balance_type": "Dr"
    }
}

Avoid embedding presentation logic deeply inside query functions.

# ============================================================
# 37. RUNNING BALANCE
# ============================================================

Ledger running balance must be deterministic.

Sort using proper sequence such as:

posting_date
creation / posting timestamp where relevant
voucher_type
voucher_no
GL Entry creation/name

Inspect ERPNext standard GL ordering.

Do not create unstable balances when multiple transactions share the same date.

# ============================================================
# 38. ACCOUNT NATURE
# ============================================================

Do not simply assume every positive balance is debit.

Respect account nature and standard accounting rules.

Assets / Expenses are normally debit-nature.

Liabilities / Equity / Income are normally credit-nature.

However raw ledger output must remain mathematically correct.

Create common helpers for:

net_balance
debit_amount
credit_amount
balance_type
formatted_balance

# ============================================================
# 39. PARTY NAME RESOLUTION
# ============================================================

Create reusable helper:

get_party_display_name(party_type, party)

Customer:
use customer_name

Supplier:
use supplier_name

Employee:
use employee_name

Shareholder:
use shareholder_name or appropriate installed field

Fallback:
party ID

Avoid repeated database queries.

Batch load names.

# ============================================================
# 40. PARTY ACCOUNT RESOLUTION
# ============================================================

Resolve party account using standard ERPNext settings where possible.

Examples:

Customer -> Receivable account

Supplier -> Payable account

Employee -> configured account where applicable

Shareholder -> relevant GL account based on entry

Do not assume a party always has exactly one account.

Support transactions involving different receivable/payable accounts.

Party Ledger should allow:

Account Head = All

or a specific account.

# ============================================================
# 41. REMARKS / NARRATION
# ============================================================

Reports should show useful remarks.

Resolve from source voucher where possible.

Possible sources:

Payment Entry remarks
Journal Entry user_remark
Sales Invoice remarks
Purchase Invoice remarks

Avoid doing one database query per ledger row.

Use batch loading.

# ============================================================
# 42. PAYMENT TYPE
# ============================================================

Party Ledger must show Payment Type where applicable.

Examples:

Receive
Pay
Internal Transfer
Journal
Sales
Purchase
Credit Note
Debit Note

Create readable mapping from voucher data.

Do not force every GL Entry into Payment Entry terminology.

# ============================================================
# 43. DRILL-DOWN ENGINE
# ============================================================

Create reusable drill-down utilities.

Required navigation:

Party Summary
 -> Party Ledger
 -> Voucher

Account Head Wise Party Ledger
 -> Party Ledger
 -> Voucher

General Ledger
 -> Account Ledger
 -> Voucher

Trial Balance
 -> Account Ledger
 -> Voucher

Profit & Loss
 -> Account Ledger
 -> Voucher

Balance Sheet
 -> Account Ledger
 -> Voucher

Cash Book
 -> Voucher

Bank Book
 -> Voucher

Day Book
 -> Voucher

Voucher routes must use standard Frappe route conventions.

# ============================================================
# 44. ACCOUNTING DIMENSIONS
# ============================================================

Support dynamic accounting dimensions.

Do not hardcode only:

Cost Center
Project

Read configured accounting dimensions.

Add them to report filters where practical.

Apply the exact dimensions to opening, movement and closing queries.

Otherwise opening and closing balances will mismatch.

# ============================================================
# 45. MULTI-COMPANY
# ============================================================

Every accounting report must require Company.

No cross-company GL mixing.

Respect company default currency.

Company filter must be part of every accounting query.

# ============================================================
# 46. MULTI-CURRENCY
# ============================================================

Do not incorrectly sum mixed currencies.

Understand:

account_currency
company_currency
debit
credit
debit_in_account_currency
credit_in_account_currency

For first implementation:

Default reporting should use Company Currency.

Where account-specific currency is appropriate, clearly indicate it.

Do not add mixed account-currency balances together.

Document currency behavior.

# ============================================================
# 47. OPENING ENTRIES
# ============================================================

Handle opening entries correctly.

Inspect:

is_opening

and ERPNext's standard report treatment.

Opening balance should correctly include:

previous fiscal periods
opening vouchers
opening journal entries

without double counting.

# ============================================================
# 48. CANCELLED ENTRIES
# ============================================================

Exclude cancelled accounting entries.

Use the appropriate installed GL Entry cancellation field.

Typically:

is_cancelled = 0

but inspect the installed version.

# ============================================================
# 49. SECURITY
# ============================================================

All report APIs must validate permissions server-side.

Never rely only on browser filters.

Check:

Company access
DocType read permissions
User Permissions
Account restrictions where applicable

Use:

frappe.has_permission()

or standard ERPNext permission utilities where appropriate.

Do not expose restricted financial data.

# ============================================================
# 50. PERFORMANCE
# ============================================================

Reports may run against millions of GL rows.

Mandatory:

Server-side filtering

Avoid SELECT *

Select only needed fields

Use indexed filtering

Avoid N+1 queries

Batch resolve:

Parties
Voucher remarks
Account names
Party names

Use Frappe Query Builder or parameterized SQL.

Candidate fields commonly used:

company
posting_date
account
party_type
party
voucher_type
voucher_no
against_voucher_type
against_voucher
cost_center
project
finance_book
is_cancelled

Inspect database indexes before adding any.

Do not blindly add duplicate indexes.

# ============================================================
# 51. PAGINATION
# ============================================================

Large transaction reports must support pagination or reasonable limits.

Especially:

General Ledger
Party Ledger
Day Book
Cash Book
Bank Book

Summary reports may return aggregated results without row pagination.

Provide sensible default limits.

# ============================================================
# 52. EXPORT
# ============================================================

Reports should support:

Print
PDF
Excel/XLSX
CSV

Use standard Frappe report export functionality where possible.

Printed heading:

Reckon Accounts

Report Name

Company

Period

Generated Date

Filters

Do not display unnecessary development metadata.

# ============================================================
# 53. TALLY-ORIENTED UI
# ============================================================

The target user is an accountant familiar with Tally.

Use clear terminology:

Day Book
Cash Book
Bank Book
Party Ledger
Account Ledger
Receipt Register
Payment Register
Journal Register
Sales Register
Purchase Register
Trial Balance
Profit & Loss
Balance Sheet

Keep UI dense but readable.

Focus on keyboard-friendly navigation.

Phase 1 primarily concerns reports.

Do not unnecessarily rebuild the entire Desk.

# ============================================================
# 54. REPORT TOTALS
# ============================================================

All applicable reports must include clear totals.

Example Party Ledger:

Opening Balance         50,000 Dr

Period Debit            25,000
Period Credit           15,000

Closing Balance         60,000 Dr

Example Cash Book:

Opening Cash           100,000

Receipts                75,000
Payments                30,000

Closing Cash           145,000

Totals must reconcile mathematically.

# ============================================================
# 55. DATE HANDLING
# ============================================================

Use posting_date for accounting reports.

Do not use creation date as the accounting date.

Creation may be used only for deterministic secondary sorting if needed.

Respect To Date cutoffs.

Historical outstanding reports must reconstruct position as of the selected date.

# ============================================================
# 56. REPORT RECONCILIATION
# ============================================================

Build:

Accounting Reconciliation

Purpose:

Compare Reckon Accounts reports with standard ERPNext reports.

Minimum checks:

Reckon General Ledger
vs
ERPNext General Ledger

Reckon Trial Balance
vs
ERPNext Trial Balance

Reckon Receivable
vs
ERPNext Accounts Receivable

Reckon Payable
vs
ERPNext Accounts Payable

Reckon Profit & Loss
vs
ERPNext Profit and Loss

Reckon Balance Sheet
vs
ERPNext Balance Sheet

Create test datasets and automated reconciliation tests.

Tolerance for currency comparison:

Use ERPNext currency precision.

Do not use arbitrary floating-point comparisons.

# ============================================================
# 57. TESTING REQUIREMENTS
# ============================================================

Write automated tests for:

Opening balance

Debit transaction

Credit transaction

Running balance

Closing balance

Customer ledger

Supplier ledger

Employee ledger

Shareholder ledger where supported

Account ledger

Cash receipt

Cash payment

Bank receipt

Bank payment

Bank transfer

Cash-to-bank transfer

Journal Entry

Sales Invoice

Purchase Invoice

Credit Note

Debit Note

Opening Journal Entry

Cancelled voucher

Cost Center filter

Project filter

Accounting Dimension filter

Multiple companies

Multiple currencies where feasible

Receivable allocation

Partial receipt

Overpayment

Advance payment

Credit note

Payable allocation

Partial supplier payment

Ageing bucket calculation

Trial Balance reconciliation

P&L reconciliation

Balance Sheet reconciliation

# ============================================================
# 58. TEST DATA
# ============================================================

Build automated fixtures where possible.

Example Company:

Reckon Test Company

Accounts:

Cash - RTC
Bank - RTC
Debtors - RTC
Creditors - RTC
Sales - RTC
Purchases - RTC
Rent Expense - RTC
Capital - RTC

Customer:

Test Customer

Supplier:

Test Supplier

Generate a controlled sequence:

1. Opening cash
2. Sales invoice
3. Customer receipt
4. Purchase invoice
5. Supplier payment
6. Expense payment
7. Journal adjustment
8. Bank transfer
9. Credit note
10. Debit note

Verify every report.

# ============================================================
# 59. REPORT ACCEPTANCE TEST
# ============================================================

For every report confirm:

1. Correct filters
2. Correct company
3. Correct opening
4. Correct debit
5. Correct credit
6. Correct closing
7. Correct currency
8. Correct party name
9. Correct account head
10. Correct remarks
11. Correct voucher link
12. Correct permissions
13. Correct totals
14. Correct export
15. Correct pagination
16. No N+1 query issue
17. Reconciles with ERPNext

# ============================================================
# 60. RECKON ACCOUNTS SETTINGS
# ============================================================

Create a minimal Single DocType only if useful:

Reckon Accounts Settings

Possible fields:

Enable Reckon Accounts

Default Report Page Size

Show Party Account Under Party Name

Show Narration

Show Cost Center

Show Project

Use Tally Terminology

Ageing Bucket 1

Ageing Bucket 2

Ageing Bucket 3

Ageing Bucket 4

Ageing Bucket 5

Do not store accounting balances in this DocType.

# ============================================================
# 61. DO NOT CREATE DUPLICATE MASTERS
# ============================================================

Do not create:

Reckon Customer

Reckon Supplier

Reckon Account

Reckon Payment

Reckon Journal

Reckon Invoice

Reckon GL Entry

Continue using standard ERPNext records.

# ============================================================
# 62. DO NOT COPY GL DATA
# ============================================================

Never create a custom table that duplicates all GL Entry rows merely to
power reports.

Reports must query accounting source data.

Caching may be considered later only after correctness is proven.

# ============================================================
# 63. NO DIRECT POSTING
# ============================================================

Reckon Accounts Phase 1 is primarily a reporting module.

Do not add direct ledger posting methods.

Future voucher UI must create standard:

Payment Entry
Journal Entry
Sales Invoice
Purchase Invoice

which will then generate normal ERPNext GL entries.

# ============================================================
# 64. ERROR HANDLING
# ============================================================

Reports should fail gracefully.

Examples:

No Company selected
No permission
Invalid date range
Invalid Account
Invalid Party
Company mismatch
Unsupported Party Type

Use clear user-facing messages.

Log actual exceptions server-side.

Do not expose stack traces to regular users.

# ============================================================
# 65. CODING STANDARDS
# ============================================================

Follow current Frappe conventions.

Python:

PEP8
Type hints where practical
Docstrings for shared functions
No giant functions
No duplicated SQL

JavaScript:

Use standard Frappe report APIs
Avoid global pollution
Reusable filter helpers
Clear formatter functions

Do not introduce unnecessary dependencies.

# ============================================================
# 66. REPORT NAMING
# ============================================================

Use internal report names:

Reckon Party Ledger
Reckon Account Ledger
Reckon Account Head Wise Party Ledger
Reckon Party Summary
Reckon General Ledger
Reckon Day Book
Reckon Cash Book
Reckon Bank Book
Reckon Bank Summary
Reckon Receipt Register
Reckon Payment Register
Reckon Contra Register
Reckon Journal Register
Reckon Sales Register
Reckon Purchase Register
Reckon Receivable Summary
Reckon Payable Summary
Reckon Bill Wise Receivable
Reckon Bill Wise Payable
Reckon Receivable Ageing
Reckon Payable Ageing
Reckon Trial Balance
Reckon Profit and Loss
Reckon Balance Sheet

User-facing labels may omit "Reckon" inside the Reckon Accounts workspace.

# ============================================================
# 67. DOCUMENTATION
# ============================================================

Create:

README.md

ARCHITECTURE.md

ACCOUNTING_MAPPING.md

REPORT_SPECIFICATION.md

DEVELOPMENT.md

INSTALLATION.md

TESTING.md

SECURITY.md

RECONCILIATION.md

Document every report:

Source DocTypes
Filters
Balance formula
Permission strategy
Drill-down
Currency behavior

# ============================================================
# 68. PHASE-1 DEVELOPMENT ORDER
# ============================================================

Do not attempt all reports in one uncontrolled implementation.

MILESTONE 0
Discovery

Deliver:

RECKON_ACCOUNTS_PHASE1_DISCOVERY.md

No production accounting changes.


MILESTONE 1
Shared accounting report engine

Implement:

balances.py
ledger.py
party.py
dimensions.py
permissions.py

Then:

Reckon Party Ledger
Reckon Account Ledger
Reckon General Ledger

Validate all three.


MILESTONE 2

Implement:

Reckon Account Head Wise Party Ledger
Reckon Party Summary

Validate opening/closing balances.


MILESTONE 3

Implement:

Reckon Day Book
Reckon Cash Book
Reckon Bank Book
Reckon Bank Summary

Validate cash and bank closing balances against GL.


MILESTONE 4

Implement:

Receipt Register
Payment Register
Contra Register
Journal Register

Validate source voucher links.


MILESTONE 5

Implement:

Sales Register
Purchase Register


MILESTONE 6

Implement:

Receivable Summary
Payable Summary
Bill Wise Receivable
Bill Wise Payable
Receivable Ageing
Payable Ageing

Reconcile with standard ERPNext AR/AP.


MILESTONE 7

Implement:

Reckon Trial Balance

Validate against ERPNext Trial Balance.


MILESTONE 8

Implement:

Reckon Profit and Loss
Reckon Balance Sheet

Validate against ERPNext financial statements.


MILESTONE 9

Implement:

Accounting Reconciliation

Add final automated tests.

# ============================================================
# 69. MILESTONE GATE RULE
# ============================================================

DO NOT automatically continue from one major milestone to another.

After completing each milestone:

1. Run tests.
2. Run reconciliation.
3. Document files changed.
4. Document assumptions.
5. Document remaining issues.
6. Provide a concise completion report.
7. Stop and wait for approval before beginning the next major milestone.

Exception:

Small fixes required to make the current milestone pass are allowed.

# ============================================================
# 70. FIRST IMPLEMENTATION PRIORITY
# ============================================================

The highest-priority report is:

Reckon Party Ledger

It must support:

Customer
Supplier
Employee
Shareholder
Other/account-head-based reporting

It must show prominently:

Party Name

and immediately underneath:

Account Head

It must display:

Date
Particulars
Voucher Type
Voucher No
Account Head
Payment Type
Debit
Credit
Running Balance
Remarks

It must show:

Opening
Period Debit
Period Credit
Closing

The report must reconcile with GL Entry.

# ============================================================
# 71. PARTY LEDGER EXAMPLE
# ============================================================

Expected presentation:

------------------------------------------------------------
RECKON ACCOUNTS
PARTY LEDGER

Company: Reckon Technologies Ltd.
Period: 01-09-2026 to 30-09-2026

ABC Trading Ltd.
Accounts Receivable - RTL
------------------------------------------------------------

Opening Balance                              50,000 Dr

01-09-2026
Sales Invoice
SINV-00031
Sales - RTL
Debit                         20,000
Balance                       70,000 Dr
Annual software service

05-09-2026
Receipt
ACC-PAY-2026-0024
Dutch Bangla Bank - RTL
Credit                        15,000
Balance                       55,000 Dr
Payment received

10-09-2026
Journal
JV-0032
Adjustment Account - RTL
Debit                          5,000
Balance                       60,000 Dr

------------------------------------------------------------
Period Debit                  25,000
Period Credit                 15,000

Closing Balance               60,000 Dr
------------------------------------------------------------

# ============================================================
# 72. DAY BOOK EXAMPLE
# ============================================================

12-09-2026

Receipt Voucher
ACC-PAY-2026-0021

Cash - RTL                         Dr 25,000
    ABC Customer                   Cr 25,000

Remarks:
Being cash received from ABC Customer.

--------------------------------------------

Payment Voucher
ACC-PAY-2026-0022

Electricity Expense - RTL          Dr 10,000
    Cash - RTL                     Cr 10,000

Remarks:
Office electricity bill.

# ============================================================
# 73. CASH BOOK EXAMPLE
# ============================================================

Reckon Cash Book

Cash Account:
Cash - RTL

Opening Cash: 100,000

Date        Particulars          Receipt    Payment     Balance

01-09       ABC Customer          25,000                 125,000
02-09       Electricity                       10,000      115,000
03-09       Office Rent                       20,000       95,000

Total Receipt                     25,000
Total Payment                     30,000

Closing Cash                                  95,000

# ============================================================
# 74. BANK BOOK EXAMPLE
# ============================================================

Bank:
Dutch Bangla Bank - RTL

Opening Balance:
500,000

Date        Particulars        Deposit     Withdrawal    Balance

01-09       ABC Customer       100,000                    600,000
02-09       Vendor Payment                  50,000        550,000
03-09       Bank Charge                      1,000        549,000

Closing Bank Balance:
549,000

# ============================================================
# 75. PARTY ACCOUNT GROUPING
# ============================================================

A party may have ledger activity across different accounts.

Do not assume one party = one account forever.

When Account Head filter is blank:

show all relevant party accounts.

When Account Head is selected:

restrict calculations to that account.

If multiple accounts exist, presentation may group:

ABC Customer

Accounts Receivable - RTL
transactions...

Advance From Customers - RTL
transactions...

# ============================================================
# 76. "OTHER" LEDGER DESIGN
# ============================================================

For Phase 1:

"Other" means account-based ledger analysis for transactions not tied to
a Customer/Supplier/Employee/Shareholder party.

Example:

Electricity Expense - RTL

Opening
Transactions
Closing

Allow Account Head selection.

Do not pretend an expense account is an ERPNext Party.

Later, if business requirements demand additional legal party master types,
design that separately.

# ============================================================
# 77. RECKON ACCOUNT DASHBOARD
# ============================================================

After core reports are stable, create a simple dashboard.

Cards:

Cash Balance
Bank Balance
Receivables
Payables
Sales This Month
Expenses This Month
Net Profit

Quick Links:

Party Ledger
Day Book
Cash Book
Bank Book
Trial Balance
P&L
Balance Sheet

Do not implement dashboard before core accounting calculations are proven.

# ============================================================
# 78. USER ROLES
# ============================================================

Phase 1 may reuse standard ERPNext accounting roles.

Prepare architecture for future custom roles:

Reckon Accounts Operator
Reckon Accountant
Reckon Senior Accountant
Reckon Finance Manager
Reckon Auditor
Reckon Accounts Administrator

Do not reduce standard ERPNext security.

# ============================================================
# 79. AUDIT
# ============================================================

The reporting layer must not alter audit history.

All voucher drill-down must lead to original ERPNext documents.

Do not silently rewrite submitted transactions.

# ============================================================
# 80. BACKWARD COMPATIBILITY
# ============================================================

Existing ERPNext Accounting Workspace must continue functioning.

Existing custom applications must continue functioning.

Existing custom fields must remain intact.

Existing reports must remain intact.

No destructive schema changes.

# ============================================================
# 81. BENCH COMMANDS
# ============================================================

Before executing commands, confirm current bench structure.

Typical development operations may include:

bench new-app reckon_accounts

bench --site <site> install-app reckon_accounts

bench migrate

bench build

bench restart

But do not run destructive or production-impacting commands without
understanding environment.

Never:

bench reinstall

drop-site

delete company

truncate accounting tables

reset database

unless explicitly instructed by the project owner.

# ============================================================
# 82. GIT
# ============================================================

Use clean commits where possible.

Recommended milestones:

feat: create reckon accounts foundation

feat: add shared accounting report engine

feat: add party and account ledger reports

feat: add day cash and bank books

feat: add voucher registers

feat: add receivable payable reports

feat: add trial balance

feat: add financial statements

test: add accounting reconciliation suite

Do not mix unrelated changes.

# ============================================================
# 83. COMPLETION REPORT AFTER EACH MILESTONE
# ============================================================

At the end of each milestone output:

MILESTONE:
STATUS:

FILES CREATED:

FILES MODIFIED:

FEATURES COMPLETED:

TESTS RUN:

RECONCILIATION RESULTS:

KNOWN ISSUES:

ASSUMPTIONS:

NEXT MILESTONE:

Do not claim success if tests fail.

# ============================================================
# 84. DEFINITION OF DONE - PHASE 1
# ============================================================

Phase 1 is considered complete when:

1. Reckon Accounts workspace exists.

2. Party Ledger supports:
   Customer
   Supplier
   Employee
   Shareholder
   Other/account-based view.

3. Party Ledger displays:
   Party Name
   Account Head underneath
   Date
   Particulars
   Voucher
   Payment Type
   Debit
   Credit
   Running Balance
   Remarks
   Opening
   Closing

4. Account Ledger works.

5. Account Head Wise Party Ledger works.

6. Party Summary works.

7. General Ledger works.

8. Day Book works.

9. Cash Book works.

10. Bank Book works.

11. Receipt Register works.

12. Payment Register works.

13. Contra Register works.

14. Journal Register works.

15. Sales Register works.

16. Purchase Register works.

17. Receivable Summary works.

18. Payable Summary works.

19. Bill Wise Receivable works.

20. Bill Wise Payable works.

21. Receivable Ageing works.

22. Payable Ageing works.

23. Trial Balance works.

24. Profit & Loss works.

25. Balance Sheet works.

26. Voucher drill-down works.

27. Company permissions are respected.

28. Accounting dimensions work.

29. Large reports use server-side queries.

30. Reports export correctly.

31. No ERPNext core files are modified.

32. No accounting data is duplicated.

33. Reports reconcile with standard ERPNext results.

34. Automated accounting tests pass.

# ============================================================
# 85. VERY IMPORTANT RESTRICTIONS
# ============================================================

NEVER:

Modify ERPNext core.

Create duplicate GL Entry tables.

Manually write financial balances into custom DocTypes.

Delete GL Entry.

Update submitted GL Entry.

Generate accounting entries without standard ERPNext transaction logic.

Bypass Company permissions.

Use client-provided Company/Party/Account values without server validation.

Use SQL string concatenation.

Fetch the entire GL table and calculate everything in JavaScript.

Hardcode a specific company.

Hardcode a specific chart of accounts.

Hardcode only BDT.

Hardcode only Customer/Supplier.

Assume every installation has identical custom fields.

Assume installed ERPNext APIs match another version.

# ============================================================
# 86. FIRST CODEX TASK
# ============================================================

START NOW WITH PHASE 0 ONLY.

Do the following:

1. Inspect repository structure.

2. Identify bench directory.

3. Identify site(s).

4. Check installed apps.

5. Determine Frappe version.

6. Determine ERPNext version.

7. Check whether reckon_accounts already exists.

8. Inspect installed accounting DocTypes and required fields.

9. Inspect:
   GL Entry
   Payment Ledger Entry
   Payment Entry
   Payment Entry Reference
   Journal Entry
   Journal Entry Account
   Account
   Customer
   Supplier
   Employee
   Shareholder
   Sales Invoice
   Purchase Invoice
   Bank Account
   Mode of Payment
   Cost Center
   Project
   Accounting Dimension

10. Inspect standard ERPNext implementations of:
    General Ledger
    Trial Balance
    Accounts Receivable
    Accounts Payable
    Profit and Loss
    Balance Sheet
    Cash Flow

11. Identify reusable ERPNext accounting helper functions.

12. Identify custom app conflicts.

13. Inspect database indexes used by GL Entry.

14. Identify installed accounting dimensions.

15. Determine correct approach for party-account resolution.

16. Determine correct approach for historical outstanding.

17. Determine how Employee and Shareholder party entries are represented in
    this installed version.

18. Determine how cancelled GL entries are represented.

19. Determine how Finance Book filtering should work.

20. Generate:

RECKON_ACCOUNTS_PHASE1_DISCOVERY.md

The discovery document must include the exact implementation plan for
Milestone 1.

DO NOT MODIFY PRODUCTION ACCOUNTING DATA.

DO NOT START MILESTONE 1 UNTIL DISCOVERY IS COMPLETE.

At the end, show:

DISCOVERY SUMMARY

FRAPPE VERSION:
ERPNEXT VERSION:
SITE:
CUSTOM APPS:
ACCOUNTING DIMENSIONS:
PARTY TYPES:
KEY STANDARD FUNCTIONS TO REUSE:
RISKS:
RECOMMENDED MILESTONE-1 STRUCTURE:

Then STOP.