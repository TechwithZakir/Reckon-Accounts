import unittest
from datetime import date

from reckon_accounts.accounting.adapters import LedgerAdapter
from reckon_accounts.accounting.books import book_csv, make_book, run_book
from reckon_accounts.accounting.catalog import BOOK_REPORTS
from reckon_accounts.tests.fakes import FakeGateway, gl
from reckon_accounts.tests.test_service import ledger, posting


def book(name, postings, **filters):
    return ledger(postings, report=name, **filters)


class TestBooks(unittest.TestCase):
    def test_exceptions_respect_normal_credit_accounts(self):
        result = make_book(
            book(
                "Ledger Exceptions",
                [
                    posting("normal", credit=50, account="Payable", root_type="Liability"),
                    posting("abnormal", 25, account="Income", root_type="Income"),
                ],
            )
        )
        self.assertEqual(len(result.rows()), 1)
        self.assertEqual(result.rows()[0]["account"], "Income")
        self.assertIn("Unexpected debit", result.rows()[0]["description"])

    def test_group_monthly_rolls_up_once_and_preserves_detail_sides(self):
        result = make_book(
            book(
                "Group Monthly Summary",
                [posting("a", 100), posting("b", credit=40, account="Other")],
                account="Assets",
            )
        )
        self.assertEqual(len(result.rows()), 1)
        self.assertEqual(result.rows()[0]["balance"], 60)
        self.assertEqual(
            (result.rows()[0]["balance_debit"], result.rows()[0]["balance_credit"]), (100, 40)
        )

    def test_monthly_carries_empty_months_and_partial_boundaries(self):
        result = make_book(
            book(
                "Ledger Monthly Summary",
                [posting("a", 100), posting("b", credit=20, month=3)],
                account="Receivable",
                to_date="2026-03-31",
            )
        )
        rows = result.rows(full=True)
        self.assertEqual([r["balance"] for r in rows], [100, 100, 80])
        self.assertEqual([r["opening"] for r in rows], [0, 100, 100])
        self.assertEqual(rows[1]["period_end"], date(2026, 2, 28))

    def test_voucher_pagination_does_not_split_lines(self):
        result = make_book(
            book(
                "Day Book",
                [posting("a", 100), posting("b", credit=100, account="Bank")],
                page_size=1,
            )
        )
        self.assertEqual(len(result.units), 1)
        self.assertEqual(len([r for r in result.rows() if r["row_kind"] == "entry"]), 2)
        self.assertNotIn("balance", result.rows()[-1])

    def test_voucher_statistics_count_identity_not_lines(self):
        result = make_book(
            book("Voucher Statistics", [posting("a", 100), posting("b", credit=100)])
        )
        self.assertEqual(result.rows()[0]["voucher_count"], 1)

    def test_negative_cash_checks_end_of_day_not_intraday(self):
        result = make_book(
            book(
                "Negative Cash",
                [
                    posting("a", credit=100, creation_hour=8),
                    posting("b", 150, creation_hour=9),
                    posting("c", credit=75, day=11),
                ],
            )
        )
        self.assertEqual(len(result.rows()), 1)
        self.assertEqual(result.rows()[0]["balance"], -25)

    def test_summary_keeps_independent_account_balances(self):
        result = make_book(
            book(
                "Cash Bank Summary",
                [posting("a", 100), posting("b", credit=40, account="Bank")],
            )
        )
        self.assertEqual(
            {r["account"]: r["balance"] for r in result.rows()}, {"Bank": -40, "Receivable": 100}
        )

    def test_receipts_payments_discloses_internal_transfers(self):
        result = make_book(book("Receipts and Payments", [posting("a", 100)]))
        self.assertIn("including internal transfers", result.notice)

    def test_funds_flow_working_capital_and_sources_reconcile(self):
        records = [
            posting("a", 100, account="Cash"),
            posting("b", credit=30, account="Payable"),
            posting("c", credit=100, account="Equity"),
            posting("d", 30, account="Equipment"),
        ]
        result = make_book(
            book("Funds Flow", records),
            current_assets={"Cash"},
            current_liabilities={"Payable"},
        )
        rows = result.rows(full=True)
        self.assertEqual(rows[-1]["working_capital_change"], 70)
        self.assertEqual(sum(r.get("sources", 0) - r.get("applications", 0) for r in rows), 70)
        with self.assertRaises(ValueError):
            make_book(
                book("Funds Flow", records),
                current_assets={"Cash"},
                current_liabilities={"Cash"},
            )

    def test_full_export_ignores_summary_pagination_and_escapes_formulas(self):
        records = [posting("a", 100, account="=unsafe"), posting("b", 20, account="Bank")]
        result = make_book(book("Group Summary", records, account="Assets", page_size=1), page=2)
        text = book_csv(result)
        self.assertIn("'=unsafe", text)
        self.assertIn("Bank", text)
        self.assertEqual(len(result.rows()), 1)


class TestBookAdapters(unittest.TestCase):
    def test_return_and_contra_register_classification(self):
        for name, source_type, source_fields in (
            ("Credit Note Register", "Sales Invoice", {"is_return": 1}),
            ("Debit Note Register", "Purchase Invoice", {"is_return": 1}),
            ("Contra Register", "Journal Entry", {"voucher_type": "Contra Entry"}),
        ):
            self.setUp()
            self.gateway.records[source_type] = [
                dict(name="Return-1", company="Co", **source_fields)
            ]
            self.gateway.records["GL Entry"] = [gl(voucher_type=source_type, voucher_no="Return-1")]
            with self.subTest(name=name):
                result = self.run_book(name)
                self.assertEqual(len(result.units), 1)
                self.assertEqual(
                    [r["voucher_no"] for r in result.rows() if r["row_kind"] == "entry"],
                    ["Return-1"],
                )

    def test_group_summary_rolls_up_to_immediate_child(self):
        self.gateway.records["Account"] = [
            dict(
                name="Root",
                company="Co",
                is_group=1,
                account_currency="BDT",
                lft=1,
                rgt=8,
                parent_account=None,
            ),
            dict(
                name="Subgroup",
                company="Co",
                is_group=1,
                account_currency="BDT",
                lft=2,
                rgt=7,
                parent_account="Root",
            ),
            dict(
                name="AR",
                company="Co",
                is_group=0,
                account_currency="BDT",
                lft=3,
                rgt=4,
                parent_account="Subgroup",
            ),
            dict(
                name="Bank",
                company="Co",
                is_group=0,
                account_currency="BDT",
                lft=5,
                rgt=6,
                parent_account="Subgroup",
            ),
        ]
        result = self.run_book("Group Summary", account="Root")
        self.assertEqual(len(result.units), 1)
        self.assertEqual(result.rows()[0]["account"], "Subgroup")
        self.assertEqual(result.rows()[0]["debit"], 100)
        self.assertEqual(result.rows()[0]["credit"], 100)
        self.assertTrue(result.rows()[0]["is_group"])

    def test_voucher_expansion_includes_other_finance_book_lines(self):
        self.gateway.records["GL Entry"][1]["finance_book"] = "Main"
        result = self.run_book("Day Book", account="AR")
        self.assertEqual(len([r for r in result.rows() if r["row_kind"] == "entry"]), 2)

    def test_export_cannot_bypass_report_permission(self):
        self.gateway.export_denied = True
        with self.gateway.installed(), self.assertRaises(PermissionError):
            run_book(
                LedgerAdapter(self.gateway),
                "Day Book",
                dict(company="Co", from_date="2026-01-01", to_date="2026-01-31"),
                full=True,
                export=True,
            )

    def setUp(self):
        self.gateway = FakeGateway()
        for record in self.gateway.records["Account"]:
            record["account_type"] = "Bank" if record["name"] == "Bank" else "Receivable"
            record["root_type"] = "Asset"
        self.gateway.records["Account"].append(
            dict(
                name="Cash",
                company="Co",
                is_group=0,
                account_currency="BDT",
                account_type="Cash",
                lft=5,
                rgt=6,
            )
        )
        self.gateway.records["GL Entry"] = [gl(), gl("bank", account="Bank", debit=0, credit=100)]

    def run_book(self, name, **filters):
        with self.gateway.installed():
            return run_book(
                LedgerAdapter(self.gateway),
                name,
                dict(company="Co", from_date="2026-01-01", to_date="2026-01-31", **filters),
            )

    def test_daybook_account_filter_selects_complete_permitted_voucher(self):
        result = self.run_book("Day Book", account="AR", page_size=1)
        self.assertEqual(
            {r["account"] for r in result.rows() if r["row_kind"] == "entry"}, {"AR", "Bank"}
        )
        self.assertEqual(result.ledger.filters.account, "AR")

    def test_restricted_voucher_expansion_does_not_expose_hidden_account(self):
        self.gateway.denied_docs.add(("Account", "Bank"))
        result = self.run_book("Day Book", account="AR")
        self.assertNotIn("Bank", repr(result.rows()))
        self.assertIn("completeness", result.rows()[0]["description"])

    def test_book_types_derive_from_account_master(self):
        result = self.run_book("Bank Book")
        self.assertEqual([s.account for s in result.sections], ["Bank"])
        self.assertEqual(self.run_book("Cash Book").sections, ())

    def test_receipt_register_rejects_journal_and_retains_payment_lines(self):
        self.gateway.records["GL Entry"] += [
            gl("p1", voucher_type="Payment Entry", voucher_no="PE-1"),
            gl(
                "p2",
                account="Bank",
                credit=100,
                debit=0,
                voucher_type="Payment Entry",
                voucher_no="PE-1",
            ),
        ]
        result = self.run_book("Receipt Register")
        entries = [r for r in result.rows() if r["row_kind"] == "entry"]
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(r["voucher_no"] == "PE-1" for r in entries))

    def test_all_catalog_views_have_executable_renderers(self):
        for name, kind in BOOK_REPORTS.items():
            if kind == "funds_flow":
                continue  # separately tested with explicit chart mappings
            filters = (
                {"account": "AR"}
                if kind in {"monthly", "group_monthly", "group_summary", "group_vouchers"}
                else {}
            )
            with self.subTest(name=name):
                result = self.run_book(name, **filters)
                self.assertIsInstance(book_csv(result), str)

    def test_statistics_ignore_cancelled_and_future_opening(self):
        self.gateway.records["GL Entry"] += [
            gl("cancelled", is_cancelled=1, voucher_no="JV-2"),
            gl("future", posting_date=date(2027, 1, 1), is_opening="Yes", voucher_no="JV-2"),
        ]
        result = self.run_book("Voucher Statistics")
        self.assertEqual(result.rows()[0]["voucher_count"], 1)
