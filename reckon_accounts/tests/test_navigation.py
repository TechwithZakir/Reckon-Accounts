import json
import unittest
from pathlib import Path

from reckon_accounts.navigation import GROUPS, sidebar_document, workspace_documents


class TestNavigation(unittest.TestCase):
    def test_one_workspace_and_three_column_cards(self):
        workspaces = list(workspace_documents())
        self.assertEqual([item["name"] for item in workspaces], ["Reckon Accounts"])
        self.assertTrue(
            all(card["data"]["col"] == 4 for card in json.loads(workspaces[0]["content"]))
        )

    def test_sidebar_contains_requested_standard_reports_and_erpnext_link(self):
        sidebar = sidebar_document()
        links = {
            (item.get("label"), item.get("link_type"), item.get("link_to"))
            for item in sidebar["items"]
        }
        for report in (
            "Balance Sheet",
            "Profit and Loss Statement",
            "Trial Balance for Party",
            "Item-wise Sales Register",
            "Item-wise Purchase Register",
            "Sales Register",
            "Purchase Register",
        ):
            self.assertIn((report, "Report", report), links)
        self.assertIn(("Financial Reports (ERPNext)", "Workspace", "Accounting"), links)

    def test_payment_mode_property_setter_is_server_synced(self):
        path = Path(__file__).parents[1] / "fixtures" / "property_setter.json"
        records = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(records[0]["field_name"], "mode_of_payment")
        self.assertEqual((records[0]["property"], records[0]["value"]), ("reqd", "1"))

    def test_navigation_names_are_unique(self):
        links = [(kind, name) for _, kind, names in GROUPS for name in names]
        self.assertEqual(len(links), len(set(links)))

    def test_voucher_page_contains_daily_counts_and_requested_reports(self):
        path = Path(__file__).parents[1] / "reckon_accounts/page/voucher_entry/voucher_entry.js"
        source = path.read_text(encoding="utf-8")
        self.assertIn("frappe.db.count", source)
        for label in (
            "Day Book",
            "Cash Book",
            "Bank Book",
            "Party Ledger",
            "General Ledger Custom",
            "Payment Register",
            "Receipt Register",
            "Trial Balance",
            "Balance Sheet",
            "Profit and Loss Statement",
            "Trial Balance for Party",
            "Item-wise Sales Register",
            "Item-wise Purchase Register",
            "Sales Register",
            "Purchase Register",
            "Financial Reports (ERPNext)",
        ):
            self.assertIn(f'"{label}"', source)


if __name__ == "__main__":
    unittest.main()
