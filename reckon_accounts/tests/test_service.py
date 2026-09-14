import unittest
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from reckon_accounts.accounting.filters import parse_ledger_filters
from reckon_accounts.accounting.service import Posting, build_ledger, display_rows


def posting(
    name,
    debit=0,
    credit=0,
    *,
    account="Receivable",
    party="Alice",
    day=10,
    month=1,
    opening=False,
    creation_hour=9,
    root_type="Asset",
):
    return Posting(
        name,
        date(2026, month, day),
        datetime(2026, 1, 1, creation_hour),
        account,
        debit,
        credit,
        "Customer" if party else "",
        party,
        party,
        "Journal Entry",
        "JV-001",
        "Journal Entry",
        "Memo",
        "Source",
        opening,
        account_root_type=root_type,
    )


def ledger(records, report="General Ledger Custom", ignore_opening=False, **changes):
    filters = parse_ledger_filters(
        {"company": "Co", "from_date": "2026-01-01", "to_date": "2026-01-31"} | changes
    )
    return build_ledger(
        report,
        filters,
        records,
        currency="BDT",
        precision=2,
        round_amount=lambda value: value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP),
        generated_at="2026-02-01 10:00:00",
        ignore_opening_check=ignore_opening,
    )


class TestService(unittest.TestCase):
    def test_multi_account_party_keeps_independent_balances(self):
        result = ledger(
            [posting("a", 100), posting("b", credit=40, account="Other AR")],
            report="Party Ledger",
            party_type="Customer",
            party="Alice",
        )
        self.assertEqual(
            {s.account: s.closing for s in result.sections}, {"Receivable": 100, "Other AR": -40}
        )
        self.assertEqual(result.totals()["closing_debit"], 100)
        self.assertEqual(result.totals()["closing_credit"], 40)

    def test_general_ledger_does_not_net_different_parties(self):
        result = ledger([posting("a", 100), posting("b", credit=100, party="Bob")])
        self.assertEqual(len(result.sections), 2)
        self.assertEqual(
            (result.totals()["closing_debit"], result.totals()["closing_credit"]), (100, 100)
        )

    def test_account_ledger_combines_all_posted_parties(self):
        result = ledger(
            [posting("a", 100), posting("b", credit=30, party="Bob")],
            report="Account Ledger",
            account="Receivable",
        )
        self.assertEqual(len(result.sections), 1)
        self.assertEqual(result.sections[0].closing, 70)
        self.assertEqual(result.sections[0].party_heading, "All parties")

    def test_other_does_not_create_a_synthetic_party(self):
        result = ledger(
            [posting("a", 100), posting("b", credit=30, party="")],
            report="Party Ledger",
            party_type="Other",
            account="Receivable",
        )
        self.assertEqual(result.sections[0].closing, 70)
        self.assertEqual(
            [r["party"] for r in display_rows(result) if r["row_kind"] == "entry"], ["Alice", ""]
        )

    def test_opening_policy_includes_future_opening_voucher(self):
        rows = [
            posting("a", 50, month=2, opening=True),
            posting("b", 10),
            posting("c", 999, month=2),
        ]
        result = ledger(rows)
        self.assertEqual(
            (result.sections[0].opening, result.sections[0].debit, result.sections[0].closing),
            (50, 10, 60),
        )
        limited = ledger(rows, ignore_opening=True)
        self.assertEqual(limited.sections[0].closing, 10)

    def test_show_opening_entries_and_prior_date(self):
        rows = [posting("a", 40, day=1, opening=True), posting("b", 20, month=2, opening=True)]
        result = ledger(rows, show_opening_entries=True, from_date="2026-01-05")
        self.assertEqual((result.sections[0].opening, result.sections[0].debit), (40, 20))

    def test_opening_only_section_is_visible(self):
        result = ledger([posting("a", 70, opening=True)])
        self.assertEqual(result.total_rows, 0)
        self.assertEqual(result.total_pages, 1)
        self.assertIn("closing", [row["row_kind"] for row in display_rows(result)])

    def test_page_carry_and_creation_tie_breaker(self):
        rows = [
            posting("a", credit=30, creation_hour=11),
            posting("z", 100, creation_hour=9),
            posting("b", credit=20, creation_hour=11),
        ]
        result = ledger(rows, page=2, page_size=1)
        data = display_rows(result)
        self.assertEqual([r["gl_entry"] for r in data if r["row_kind"] == "entry"], ["a"])
        self.assertEqual(next(r["balance"] for r in data if r["row_kind"] == "carry"), 100)
        self.assertEqual(next(r["balance"] for r in data if r["row_kind"] == "closing"), 50)
        self.assertEqual(next(r["balance"] for r in data if r["row_kind"] == "page_closing"), 70)

    def test_party_heading_always_immediately_precedes_account(self):
        for report, changes in (
            ("General Ledger Custom", {}),
            ("Account Ledger", {"account": "Receivable"}),
            ("Party Ledger", {"party_type": "Customer", "party": "Alice"}),
        ):
            rows = display_rows(ledger([posting("a", 5)], report=report, **changes))
            for index, row in enumerate(rows):
                if row["row_kind"] == "account_heading":
                    self.assertEqual(rows[index - 1]["row_kind"], "party_heading")

    def test_full_rows_match_all_pages_without_duplicates(self):
        records = [posting(str(i), i, party="Alice" if i < 3 else "Bob") for i in range(5)]
        full = display_rows(ledger(records), full=True)
        page_entries = []
        for page in (1, 2, 3):
            page_entries += [
                row
                for row in display_rows(ledger(records, page=page, page_size=2))
                if row["row_kind"] == "entry"
            ]
        self.assertEqual([r for r in full if r["row_kind"] == "entry"], page_entries)

    def test_invalid_scope_and_duplicate_entries(self):
        for report in ("Unknown", "Party Ledger", "Account Ledger"):
            with self.subTest(report=report), self.assertRaises(ValueError):
                ledger([], report=report)
        with self.assertRaises(ValueError):
            ledger([posting("a"), posting("a")])
        with self.assertRaises(ValueError):
            ledger([], page=2)

    def test_reversal_zero_crossing_and_source_identity(self):
        result = ledger([posting("a", "0.10"), posting("b", credit="0.30"), posting("c", "-0.10")])
        self.assertEqual(result.sections[0].closing, Decimal("-0.30"))
        self.assertEqual(result.sections[0].movements[-1].posting.voucher_no, "JV-001")
