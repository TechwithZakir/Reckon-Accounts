import hashlib
import json
import unittest
from pathlib import Path

from reckon_accounts.navigation import GROUPS, sidebar_document, workspace_documents


class TestNavigation(unittest.TestCase):
    def test_reckon_roles_cover_workspace_and_relevant_doctypes(self):
        roles = {row["role"] for row in next(workspace_documents())["roles"]}
        self.assertTrue({"Reckon Accounts User", "Reckon Accounts Manager"}.issubset(roles))
        source = (Path(__file__).parents[1] / "access_control.py").read_text(encoding="utf-8")
        for collection in (
            "TRANSACTION_DOCTYPES",
            "MASTER_DOCTYPES",
            "SETUP_DOCTYPES",
            "NAVIGATION_DOCTYPES",
            "STANDARD_REPORTS",
        ):
            self.assertIn(collection, source)
        self.assertIn('_ensure_role_links("Workspace", "Reckon Accounts")', source)
        self.assertIn('_ensure_role_links("Page", "voucher-entry")', source)
        self.assertIn('_ensure_role_links("Workspace", "Accounting")', source)

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

    def test_desktop_app_uses_packaged_custom_icon(self):
        from reckon_accounts import hooks

        icon = hooks.add_to_apps_screen[0]
        self.assertEqual(icon["logo"], "/assets/reckon_accounts/images/reckon-accounts-icon.png")
        self.assertEqual(icon["route"], "/desk/reckon-accounts")
        self.assertEqual(icon["desk_route"], "/desk/reckon-accounts")
        path = Path(__file__).parents[1] / "public/images/reckon-accounts-icon.png"
        self.assertTrue(path.is_file())
        self.assertEqual(len(hashlib.sha256(path.read_bytes()).hexdigest()), 64)

    def test_migration_repairs_workspace_icon_as_desktop_app(self):
        path = Path(__file__).parents[1] / "patches/v0_1/sync_desktop_app_icon.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn('"icon_type": "App"', source)
        self.assertIn('"link_type": "External"', source)
        self.assertIn('"standard": 0', source)
        self.assertIn('"link": APP_ROUTE', source)
        self.assertIn('"logo_url": ICON_URL', source)
        self.assertIn('"icon_image": ICON_URL', source)

        patches = (Path(__file__).parents[1] / "patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_accounts.patches.v0_1.restore_desktop_app_icon", patches)
        self.assertIn("reckon_accounts.patches.v0_1.fix_desktop_workspace_route", patches)


if __name__ == "__main__":
    unittest.main()
