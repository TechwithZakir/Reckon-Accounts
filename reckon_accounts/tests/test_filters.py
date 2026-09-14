import unittest
from datetime import date, datetime

from reckon_accounts.accounting.filters import parse_ledger_filters


class TestFilters(unittest.TestCase):
    def parse(self, **changes):
        values = {"company": "Reckon", "from_date": "2026-01-01", "to_date": "2026-01-31"}
        return parse_ledger_filters(values | changes)

    def test_defaults_and_date_normalization(self):
        filters = self.parse(company=" Reckon ", to_date=date(2026, 1, 31))
        self.assertEqual(filters.company, "Reckon")
        self.assertEqual(filters.from_date, date(2026, 1, 1))
        self.assertEqual(
            (filters.page, filters.page_size, filters.currency_mode), (1, 100, "company")
        )
        self.assertEqual(filters.balance_label, "Balance")

    def test_invalid_dates_and_reversed_period(self):
        for value in (
            None,
            "2026-02-30",
            "20260101",
            "2026-1-1",
            "2026-01-01T12:00:00",
            datetime(2026, 1, 1),
            "2026-02-01",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(from_date=value)

    def test_single_day_period(self):
        self.assertEqual(self.parse(to_date="2026-01-01").to_date, date(2026, 1, 1))

    def test_required_and_optional_links_reject_wrong_types(self):
        for key in (
            "company",
            "account",
            "party_type",
            "party",
            "voucher_type",
            "voucher_no",
            "payment_type",
        ):
            for value in ("", "   ", True, 3, ["Account"]):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.parse(**{key: value})
        with self.assertRaises(ValueError):
            self.parse(company=None)
        self.assertIsNone(self.parse(account=None).account)

    def test_conflicting_or_incomplete_filters(self):
        for changes in (
            {"party": "Customer A"},
            {"voucher_no": "PAY-001"},
            {"party_type": "Customer", "only_entries_without_party": True},
            {"only_entries_without_party": "false"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.parse(**changes)
        self.assertTrue(self.parse(only_entries_without_party=True).only_entries_without_party)

    def test_unknown_options_never_silently_disappear(self):
        for key in ("cost_center", "ignore_permissions", "presentation_currency"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.parse(**{key: None})
        with self.assertRaises(ValueError):
            self.parse(currency_mode="account")
        with self.assertRaises(ValueError):
            parse_ledger_filters([])

    def test_voucher_scope_and_label_survive_pagination(self):
        changes = {
            "voucher_type": "Payment Entry",
            "voucher_no": "PAY-001",
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": "A",
        }
        first = self.parse(**changes)
        second = self.parse(**changes, page=2, page_size=50)
        self.assertEqual(first.balance_scope(), second.balance_scope())
        self.assertEqual(first.balance_label, "Filtered balance")
        self.assertEqual(first.balance_scope()["voucher_no"], "PAY-001")
        self.assertNotIn("from_date", first.balance_scope())
        for change in ({"voucher_type": "Journal Entry"}, {"payment_type": "Pay"}):
            self.assertTrue(self.parse(**change).filtered_balance)

    def test_pagination_bounds(self):
        for change in (
            {"page": True},
            {"page": 0},
            {"page": "1"},
            {"page_size": 0},
            {"page_size": 501},
            {"page_size": 1.5},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.parse(**change)
        self.assertEqual(self.parse(page_size=500).page_size, 500)

    def test_dimensions_and_new_scope_options(self):
        filters = self.parse(
            fiscal_year="2026",
            finance_book="Primary",
            dimensions={"cost_center": ["Main", None, "Main"]},
        )
        self.assertEqual(filters.dimensions, (("cost_center", ("Main", None)),))
        self.assertEqual(filters.balance_scope()["finance_book"], "Primary")
        self.assertEqual(
            self.parse(account="Bank", currency_mode="account").currency_mode, "account"
        )
        for dimension in (
            None,
            {"x;drop": ["a"]},
            {"cost_center": []},
            {"cost_center": "Main"},
            {"cost_center": [True]},
        ):
            with self.subTest(dimension=dimension), self.assertRaises(ValueError):
                self.parse(dimensions=dimension)

    def test_other_is_an_account_view(self):
        self.assertEqual(self.parse(party_type="Other").party_type, "Other")
        self.assertEqual(self.parse(party_type="Other", account="Bank").party_type, "Other")
        self.assertTrue(
            self.parse(
                party_type="Other", account="Bank", only_entries_without_party=True
            ).only_entries_without_party
        )
        for values in (
            {"party_type": "Other", "account": "Bank", "party": "A"},
            {"payment_type": "Pay", "voucher_type": "Journal Entry"},
            {"include_default_book_entries": "false"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.parse(**values)
