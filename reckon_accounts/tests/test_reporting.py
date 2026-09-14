import csv
import unittest
from dataclasses import replace
from io import StringIO

from reckon_accounts.accounting.reporting import export_csv, message, report_tuple
from reckon_accounts.tests.test_service import ledger, posting


class TestReporting(unittest.TestCase):
    def test_full_export_from_page_two_keeps_all_rows_and_numeric_amounts(self):
        result = ledger([posting("a", 25), posting("b", credit=50)], page=2, page_size=1)
        data = list(csv.reader(StringIO(export_csv(result).lstrip("\ufeff"))))
        headings = next(row for row in data if row and row[0] == "Particulars / section")
        kind = headings.index("Row Type")
        entries = [row for row in data if len(row) == len(headings) and row[kind] == "entry"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1][headings.index("Signed Balance")], "-25.00")
        self.assertNotIn("'", entries[1][headings.index("Signed Balance")])

    def test_export_neutralizes_untrusted_formulas(self):
        malicious = replace(posting("a", 1), remarks='=HYPERLINK("bad")', party_name="+command")
        csv_text = export_csv(ledger([malicious]))
        self.assertIn("'+command", csv_text)
        self.assertIn("'=HYPERLINK", csv_text)

    def test_report_message_escapes_filter_markup(self):
        result = ledger([], company="<script>alert(1)</script>")
        self.assertNotIn("<script>", message(result))
        self.assertIn("&lt;script&gt;", message(result))

    def test_report_disables_generic_totals_and_labels_page_export(self):
        result = report_tuple(ledger([posting("a", 10)]))
        self.assertTrue(result[5])
        self.assertEqual(result[1][0]["row_kind"], "scope")
        self.assertIn("PAGE 1/1", result[1][0]["description"])
        self.assertEqual(len(result[4]), 6)

    def test_ledger_titles_preserve_distinct_account_identities(self):
        records = [
            replace(posting("a", 10, account="ACC-001"), account_name="Cash"),
            replace(posting("b", 20, account="ACC-002"), account_name="Cash"),
        ]
        result = ledger(records)
        cols, rows, *_ = report_tuple(result)
        self.assertEqual(len(result.sections), 2)
        self.assertEqual(next(c for c in cols if c["fieldname"] == "account")["hidden"], 1)
        entries = [r for r in rows if r["row_kind"] == "entry"]
        self.assertEqual([r["account_name"] for r in entries], ["Cash", "Cash"])
        headings = [r["description"] for r in rows if r["row_kind"] == "account_heading"]
        self.assertEqual(headings, ["Cash", "Cash"])
        data = list(csv.reader(StringIO(export_csv(result).lstrip("\ufeff"))))
        header = next(r for r in data if r and r[0] == "Particulars / section")
        self.assertTrue(
            any(len(r) == len(header) and r[header.index("Ledger Account")] == "Cash" for r in data)
        )

    def test_book_titles_include_opening_only_and_selected_groups(self):
        from reckon_accounts.accounting.books import make_book

        for report in (
            "Day Book",
            "Cash Bank Summary",
            "Ledger Monthly Summary",
            "Ledger Exceptions",
            "Group Monthly Summary",
        ):
            result = ledger(
                [replace(posting("a", credit=10, account="ACC-001"), account_name="Cash")],
                report=report,
                account="GROUP-001",
            )
            result = replace(result, account_titles=(("GROUP-001", "Current Assets"),))
            rows = make_book(result).rows(full=True)
            for row in rows:
                if row.get("account"):
                    self.assertEqual(
                        row["account_name"],
                        "Current Assets" if row["account"] == "GROUP-001" else "Cash",
                    )
                    self.assertNotEqual(row["description"], row["account"])
        result = ledger([replace(posting("o", 5, opening=True), account_name="Trade Receivables")])
        self.assertIn("Trade Receivables", [r["description"] for r in report_tuple(result)[1]])
