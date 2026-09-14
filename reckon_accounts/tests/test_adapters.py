import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from reckon_accounts.accounting.adapters import (
    Frappe15Gateway,
    Frappe16Gateway,
    LedgerAdapter,
    ScopeError,
    get_gateway,
)
from reckon_accounts.tests.fakes import FakeGateway, gl


class TestAdapters(unittest.TestCase):
    def setUp(self):
        self.gateway = FakeGateway()
        self.gateway.records["GL Entry"] = [gl()]

    def run_report(self, *, report="General Ledger Custom", export=False, **changes):
        with self.gateway.installed():
            return LedgerAdapter(self.gateway).run(
                report,
                {
                    "company": "Co",
                    "from_date": "2026-01-01",
                    "to_date": "2026-01-31",
                }
                | changes,
                export=export,
            )

    def test_company_currency_default_and_account_currency(self):
        self.assertEqual(self.run_report().sections[0].closing, 100)
        account = self.run_report(account="AR", currency_mode="account")
        self.assertEqual((account.currency, account.sections[0].closing), ("USD", 10))
        self.gateway.records["GL Entry"][0]["account_currency"] = "EUR"
        with self.assertRaises(ScopeError):
            self.run_report(account="AR", currency_mode="account")

    def test_cancelled_rows_excluded_and_amendment_included(self):
        self.gateway.records["GL Entry"] = [gl(is_cancelled=1), gl("amended", debit=45)]
        self.assertEqual(self.run_report().sections[0].closing, 45)

    def test_opening_is_not_a_universal_predate_sum(self):
        self.gateway.records["GL Entry"] = [
            gl(posting_date=date(2026, 2, 1), is_opening="Yes"),
            gl("normal", debit=25),
        ]
        result = self.run_report()
        self.assertEqual((result.sections[0].opening, result.sections[0].closing), (100, 125))
        self.gateway.ignore_opening = True
        self.assertEqual(self.run_report().sections[0].closing, 25)

    def test_finance_book_blank_default_and_alternative(self):
        self.gateway.records["GL Entry"] = [
            gl(),
            gl("main", debit=20, finance_book="Main"),
            gl("other", debit=30, finance_book="Other"),
        ]
        self.assertEqual(self.run_report().sections[0].closing, 100)
        self.assertEqual(
            self.run_report(include_default_book_entries=True).sections[0].closing, 120
        )
        self.assertEqual(self.run_report(finance_book="Other").sections[0].closing, 130)
        with self.assertRaises(ScopeError):
            self.run_report(finance_book="Other", include_default_book_entries=True)

    def test_payment_type_applies_to_opening_and_movement(self):
        self.gateway.records["GL Entry"] = [
            gl(),
            gl("payment", debit=30, voucher_type="Payment Entry", voucher_no="PE-1"),
            gl(
                "opening",
                debit=50,
                is_opening="Yes",
                voucher_type="Payment Entry",
                voucher_no="PE-1",
            ),
        ]
        result = self.run_report(payment_type="Receive")
        self.assertEqual((result.sections[0].opening, result.sections[0].debit), (50, 30))
        self.assertTrue(result.filters.filtered_balance)
        self.assertEqual(self.run_report(payment_type="Pay").sections, ())

    def test_restricted_rows_do_not_enter_totals_or_names(self):
        self.gateway.records["GL Entry"].append(
            gl("hidden", debit=999, party="Bob", voucher_no="JV-2")
        )
        self.gateway.denied_docs.add(("Journal Entry", "JV-2"))
        result = self.run_report()
        self.assertEqual(result.totals()["closing_debit"], 100)
        self.assertNotIn("Bob", repr(result))

    def test_query_restrictions_apply_before_aggregation(self):
        self.gateway.denied_list.add(("GL Entry", "gl-1"))
        self.assertEqual(self.run_report().sections, ())

    def test_unfiltered_account_company_is_checked(self):
        self.gateway.records["Account"][0]["company"] = "Elsewhere"
        with self.assertRaises(ScopeError):
            self.run_report()
        self.gateway.hidden_fields["Account"] = ["company"]
        with self.assertRaises(ScopeError):
            self.run_report()

    def test_hidden_dimension_ownership_fails_closed(self):
        self.gateway.hidden_fields["Project"] = ["company"]
        with self.assertRaises(ScopeError):
            self.run_report(dimensions={"project": ["Project A"]})

    def test_permissions_checked_before_gl_query(self):
        for kind in ("report", "company", "export", "guest", "gl"):
            self.setUp()
            if kind == "report":
                self.gateway.report_denied = True
            if kind == "company":
                self.gateway.denied_docs.add(("Company", "Co"))
            if kind == "export":
                self.gateway.export_denied = True
            if kind == "guest":
                self.gateway.frappe.session.user = "Guest"
            if kind == "gl":
                self.gateway.denied_types.add("GL Entry")
            with self.subTest(kind=kind), self.assertRaises((PermissionError, ScopeError)):
                self.run_report(export=True)
            self.assertFalse(any(query[0] == "GL Entry" for query in self.gateway.queries))

    def test_dimension_tree_blank_multiple_and_disabled(self):
        self.gateway.records["GL Entry"] = [gl(cost_center="Child CC"), gl("blank", debit=20)]
        self.assertEqual(
            self.run_report(dimensions={"cost_center": ["Main CC"]}).sections[0].closing, 100
        )
        self.assertEqual(
            self.run_report(dimensions={"cost_center": [None]}).sections[0].closing, 20
        )
        self.assertEqual(
            self.run_report(dimensions={"cost_center": ["Main CC", None]}).sections[0].closing, 120
        )
        with self.assertRaises(ScopeError):
            self.run_report(dimensions={"disabled_field": ["x"]})

    def test_dimension_denial_and_company_mismatch(self):
        self.gateway.records["GL Entry"][0]["project"] = "Project A"
        self.gateway.denied_docs.add(("Project", "Project A"))
        self.assertEqual(self.run_report().sections, ())
        self.gateway.denied_docs.clear()
        self.gateway.records["Project"][0]["company"] = "Elsewhere"
        with self.assertRaises(ScopeError):
            self.run_report(dimensions={"project": ["Project A"]})

    def test_fiscal_year_and_account_company_validation(self):
        self.assertEqual(self.run_report(fiscal_year="2026").currency, "BDT")
        with self.assertRaises(ScopeError):
            self.run_report(fiscal_year="2026", from_date="2025-12-01")
        self.gateway.records["Account"][0]["company"] = "Elsewhere"
        with self.assertRaises(ScopeError):
            self.run_report(account="AR")

    def test_hidden_required_fields_fail_and_narration_can_be_redacted(self):
        self.gateway.hidden_fields["GL Entry"] = ["debit"]
        with self.assertRaises(ScopeError):
            self.run_report()
        self.gateway.hidden_fields["GL Entry"] = ["remarks"]
        self.assertEqual(self.run_report().sections[0].movements[0].posting.remarks, "")

    def test_candidate_limit_rejects_without_partial_result(self):
        self.gateway.records["GL Entry"].append(gl("second"))
        with (
            patch("reckon_accounts.accounting.adapters.MAX_GL_ROWS", 1),
            self.assertRaises(ScopeError),
        ):
            self.run_report()

    def test_other_and_no_party_filter(self):
        self.gateway.records["GL Entry"].append(gl("blank", debit=25, party=None, party_type=None))
        result = self.run_report(report="Party Ledger", party_type="Other", account="AR")
        self.assertEqual(result.sections[0].closing, 125)
        self.assertEqual(
            self.run_report(account="AR", only_entries_without_party=True).sections[0].closing, 25
        )

    def test_version_gate_and_query_signatures(self):
        with self.gateway.installed() as modules:
            self.assertIsInstance(get_gateway(), Frappe15Gateway)
            modules["frappe"].__version__ = modules["erpnext"].__version__ = "16.0.0"
            self.assertIsInstance(get_gateway(), Frappe16Gateway)
            modules["erpnext"].__version__ = "15.0.0"
            with self.assertRaises(ScopeError):
                get_gateway()
        calls = []
        fake = SimpleNamespace(get_list=lambda *args, **kwargs: calls.append(kwargs))
        Frappe15Gateway(fake).list_records("Account", filters={}, limit=20)
        Frappe16Gateway(fake).list_records("Account", filters={}, limit=20)
        self.assertEqual(calls[0]["limit_page_length"], 20)
        self.assertEqual(calls[1]["limit"], 20)
        self.assertTrue(all(call["ignore_permissions"] is False for call in calls))
