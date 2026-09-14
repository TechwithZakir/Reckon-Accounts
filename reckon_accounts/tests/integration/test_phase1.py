"""Real document posting and independent ERPNext reconciliation gates.

Run only on a disposable site with reckon_accounts_test_site = true. No GL row is
inserted directly. These tests are skipped by source-only runs without Frappe.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

try:
    import frappe
except ImportError:
    frappe = None


@unittest.skipIf(frappe is None, "Requires an initialized disposable Frappe test site")
class TestPhase1Integration(unittest.TestCase):
    def setUp(self):
        if not frappe.conf.get("reckon_accounts_test_site"):
            self.skipTest("Set reckon_accounts_test_site only on a disposable development site")
        self.previous_user = frappe.session.user
        frappe.set_user("Administrator")
        self.marker = "ra_" + uuid4().hex[:10]
        frappe.db.savepoint(self.marker)
        self.addCleanup(self.cleanup_site)
        self.year = date.today().year
        self.company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": self.marker,
                "abbr": self.marker[-5:],
                "default_currency": "USD",
                "country": "United States",
                "chart_of_accounts": "Standard",
            }
        ).insert()
        from erpnext.accounts.utils import get_fiscal_year

        try:
            get_fiscal_year(date(self.year, 1, 10), company=self.company.name)
        except frappe.ValidationError:
            frappe.get_doc(
                {
                    "doctype": "Fiscal Year",
                    "year": self.marker,
                    "year_start_date": date(self.year, 1, 1),
                    "year_end_date": date(self.year, 12, 31),
                    "companies": [{"company": self.company.name}],
                }
            ).insert()
        self.ar = self.account("Receivable", "Asset", "Receivable")
        self.ar2 = self.account("Receivable 2", "Asset", "Receivable")
        self.cash = self.account("Cash", "Asset", "Cash")
        self.equity = self.account("Equity", "Equity", "")
        self.alice = self.customer("Alice")
        self.bob = self.customer("Bob")
        self.journal(self.ar, 100, self.alice, opening=True)
        self.journal(self.ar, 50, self.alice)
        self.journal(self.ar2, 25, self.alice)
        self.journal(self.ar, 999, self.bob)
        payment = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "company": self.company.name,
                "payment_type": "Receive",
                "posting_date": date(self.year, 1, 10),
                "party_type": "Customer",
                "party": self.alice,
                "paid_from": self.ar,
                "paid_to": self.cash,
                "paid_amount": 30,
                "received_amount": 30,
                "source_exchange_rate": 1,
                "target_exchange_rate": 1,
            }
        ).insert()
        payment.submit()
        self.payment = payment.name
        cancelled = self.journal(self.ar, 10, self.alice)
        cancelled.cancel()

    def cleanup_site(self):
        frappe.set_user("Administrator")
        frappe.db.rollback(save_point=self.marker)
        frappe.clear_cache()
        frappe.set_user(self.previous_user)

    def account(self, label, root_type, account_type, currency="USD"):
        parent = frappe.get_all(
            "Account",
            filters={"company": self.company.name, "root_type": root_type, "is_group": 1},
            pluck="name",
            limit_page_length=1,
        )[0]
        return (
            frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": self.marker + " " + label,
                    "company": self.company.name,
                    "parent_account": parent,
                    "account_type": account_type,
                    "account_currency": currency,
                    "is_group": 0,
                }
            )
            .insert()
            .name
        )

    def customer(self, label):
        return (
            frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": self.marker + " " + label,
                    "customer_type": "Individual",
                    "customer_group": "All Customer Groups",
                    "territory": "All Territories",
                }
            )
            .insert()
            .name
        )

    def journal(self, account, amount, customer, opening=False, exchange_rate=1):
        doc = frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "company": self.company.name,
                "posting_date": date(self.year, 1, 1 if opening else 10),
                "is_opening": "Yes" if opening else "No",
                "multi_currency": int(exchange_rate != 1),
                "accounts": [
                    {
                        "account": account,
                        "party_type": "Customer",
                        "party": customer,
                        "debit_in_account_currency": amount,
                        "exchange_rate": exchange_rate,
                    },
                    {
                        "account": self.equity,
                        "credit_in_account_currency": amount * exchange_rate,
                        "exchange_rate": 1,
                    },
                ],
            }
        ).insert()
        doc.submit()
        return doc

    def filters(self, **extra):
        return {
            "company": self.company.name,
            "from_date": f"{self.year}-01-01",
            "to_date": f"{self.year}-01-31",
        } | extra

    def run_report(self, name, **extra):
        from reckon_accounts.accounting.adapters import LedgerAdapter, get_gateway

        return LedgerAdapter(get_gateway()).run(name, self.filters(**extra))

    def test_party_ledger_matches_independent_expected_and_standard_gl(self):
        from erpnext.accounts.report.general_ledger.general_ledger import execute

        result = self.run_report("Party Ledger", party_type="Customer", party=self.alice)
        self.assertEqual(
            {section.account: section.closing for section in result.sections},
            {self.ar: Decimal(120), self.ar2: Decimal(25)},
        )
        for section in result.sections:
            _, standard = execute(
                frappe._dict(
                    self.filters(
                        account=[section.account],
                        party_type="Customer",
                        party=[self.alice],
                        presentation_currency="USD",
                        include_default_book_entries=0,
                    )
                )
            )
            reference = Decimal(str(standard[-1].get("debit", 0))) - Decimal(
                str(standard[-1].get("credit", 0))
            )
            self.assertAlmostEqual(section.closing, reference, places=result.precision)

    def test_account_and_general_ledger_balance(self):
        account = self.run_report("Account Ledger", account=self.ar)
        self.assertEqual(account.sections[0].closing, 1119)
        general = self.run_report("General Ledger Custom")
        self.assertEqual(general.totals()["closing_debit"], 1174)
        self.assertEqual(general.totals()["closing_credit"], 1174)

    def test_payment_filter_and_full_export_pagination(self):
        from reckon_accounts.accounting.reporting import export_csv

        result = self.run_report(
            "Party Ledger", party_type="Customer", party=self.alice, payment_type="Receive"
        )
        self.assertEqual(result.sections[0].closing, -30)
        paged = self.run_report(
            "Party Ledger", party_type="Customer", party=self.alice, page=2, page_size=1
        )
        exported = export_csv(paged)
        self.assertIn(self.payment, exported)
        self.assertIn(self.ar2, exported)

    def test_restricted_customer_is_excluded_before_totals(self):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": self.marker + "@example.invalid",
                "first_name": "Reckon test",
                "send_welcome_email": 0,
                "roles": [{"role": "Accounts User"}],
            }
        ).insert()
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user.name,
                "allow": "Customer",
                "for_value": self.alice,
            }
        ).insert()
        frappe.set_user(user.name)
        result = self.run_report("Account Ledger", account=self.ar)
        self.assertEqual(result.sections[0].closing, 120)
        self.assertNotIn(self.bob, repr(result))

    def test_foreign_account_in_both_currencies(self):
        foreign = self.account("EUR Receivable", "Asset", "Receivable", "EUR")
        self.journal(foreign, 10, self.alice, exchange_rate=1.2)
        company = self.run_report("Account Ledger", account=foreign)
        account = self.run_report("Account Ledger", account=foreign, currency_mode="account")
        self.assertEqual((company.currency, company.sections[0].closing), ("USD", 12))
        self.assertEqual((account.currency, account.sections[0].closing), ("EUR", 10))

    def test_registered_reports_and_workspace(self):
        from reckon_accounts.accounting.service import REPORTS

        workspace = frappe.get_doc("Workspace", "Reckon Accounts")
        links = {link.link_to for link in workspace.links if link.type == "Link"}
        self.assertTrue(set(REPORTS).issubset(links))
        for name in REPORTS:
            doc = frappe.get_doc("Report", name)
            self.assertEqual(doc.report_type, "Script Report")
            self.assertFalse(doc.add_total_row)

    def test_day_book_expands_selected_account_to_source_lines(self):
        from reckon_accounts.accounting.adapters import LedgerAdapter, get_gateway
        from reckon_accounts.accounting.books import run_book

        result = run_book(
            LedgerAdapter(get_gateway()),
            "Day Book",
            self.filters(account=self.ar, party_type="Customer", party=self.alice, page_size=1),
        )
        self.assertEqual(len(result.units[0]), len(result.rows()))
        self.assertIn(self.equity, {row.get("account") for row in result.rows()})

    def test_cash_book_and_monthly_summary_use_posted_movements(self):
        from reckon_accounts.accounting.adapters import LedgerAdapter, get_gateway
        from reckon_accounts.accounting.books import run_book

        cash = run_book(LedgerAdapter(get_gateway()), "Cash Book", self.filters())
        self.assertEqual(
            {section.account: section.closing for section in cash.sections}[self.cash], 30
        )
        monthly = run_book(
            LedgerAdapter(get_gateway()),
            "Ledger Monthly Summary",
            self.filters(account=self.ar, party_type="Customer", party=self.alice),
        )
        self.assertEqual(monthly.rows()[0]["balance"], 120)
