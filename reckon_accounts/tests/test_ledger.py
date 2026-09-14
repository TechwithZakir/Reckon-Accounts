import unittest
from datetime import date, datetime
from decimal import Decimal

from reckon_accounts.accounting.ledger import LedgerEntry, paginate_ledger


def entry(identity, debit="0", credit="0", day=1):
    return LedgerEntry(identity, date(2026, 1, day), debit, credit)


class TestLedger(unittest.TestCase):
    def test_full_totals_and_carry_across_pages(self):
        entries = [entry("c", credit="150", day=2), entry("b", credit="30"), entry("a", debit="25")]
        first = paginate_ledger(iter(entries), "100", page_size=2)
        second = paginate_ledger(entries, "100", page_size=2, page=2)
        self.assertEqual([row.entry.entry_id for row in first.rows], ["a", "b"])
        self.assertEqual([row.balance.net for row in first.rows], [125, 95])
        self.assertEqual(second.carry_forward.net, 95)
        self.assertEqual(second.rows[0].balance.net, -55)
        for result in (first, second):
            self.assertEqual((result.period_debit, result.period_credit), (25, 180))
            self.assertEqual(result.closing.net, -55)
            self.assertEqual((result.total_rows, result.total_pages), (3, 2))
        self.assertTrue(first.has_next)
        self.assertFalse(second.has_next)
        self.assertEqual(second.page_closing, second.closing)

    def test_empty_scope_retains_opening(self):
        result = paginate_ledger([], "-12.50")
        self.assertEqual(result.rows, ())
        self.assertEqual(result.total_pages, 1)
        self.assertEqual(result.period_debit, 0)
        self.assertEqual(result.opening, result.carry_forward)
        self.assertEqual(result.opening, result.page_closing)
        self.assertEqual(result.closing.net, Decimal("-12.50"))

    def test_reversals_and_precision(self):
        result = paginate_ledger([entry("a", "1.12345"), entry("b", "-1.12345")], 0)
        self.assertEqual(result.closing.net, 0)
        self.assertEqual(result.rows[0].balance.net, Decimal("1.12345"))

    def test_invalid_pagination(self):
        for kwargs in (
            {"page": 0},
            {"page": True},
            {"page": 1.5},
            {"page": 2},
            {"page_size": 0},
            {"page_size": 501},
            {"page_size": False},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                paginate_ledger([], 0, **kwargs)

    def test_duplicate_identity_rejected_even_on_other_date(self):
        with self.assertRaises(ValueError):
            paginate_ledger([entry("a"), entry("a", day=2)], 0)

    def test_invalid_entries(self):
        for identity, posting_date, amount in (
            ("", date(2026, 1, 1), 0),
            ("a", "2026-01-01", 0),
            ("a", datetime(2026, 1, 1), 0),
            ("a", date(2026, 1, 1), "NaN"),
        ):
            with self.subTest(identity=identity, amount=amount), self.assertRaises(ValueError):
                LedgerEntry(identity, posting_date, amount, 0)
        with self.assertRaises(ValueError):
            paginate_ledger([{}], 0)
