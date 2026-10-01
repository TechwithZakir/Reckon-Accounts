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
        self.assertNotIn('_ensure_role_links("Page", "payment-voucher")', source)
        self.assertNotIn('_ensure_role_links("Page", "receipt-voucher")', source)
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
        self.assertNotIn(("Payment Voucher", "Page", "payment-voucher"), links)
        self.assertNotIn(("Receipt Voucher", "Page", "receipt-voucher"), links)

    def test_dashboard_is_after_home_in_sidebar(self):
        items = sidebar_document()["items"]
        self.assertEqual(items[0]["link_to"], "Reckon Accounts")
        self.assertEqual(items[1]["label"], "Accounts Dashboard")
        self.assertEqual(items[1]["link_to"], "accounts-dashboard")
        source = (Path(__file__).parents[1] / "access_control.py").read_text(encoding="utf-8")
        self.assertIn('_ensure_role_links("Page", "accounts-dashboard")', source)

    def test_payment_mode_property_setter_is_server_synced(self):
        path = Path(__file__).parents[1] / "fixtures" / "property_setter.json"
        records = json.loads(path.read_text(encoding="utf-8"))
        settings = {(row["field_name"], row["property"]): row["value"] for row in records}
        self.assertEqual(settings[("naming_series", "hidden")], "1")
        self.assertEqual(settings[("party_section", "label")], "Party Details")
        self.assertEqual(settings[("mode_of_payment", "reqd")], "1")

    def test_payment_remarks_use_standard_metadata_layout(self):
        fixture_path = Path(__file__).parents[1] / "fixtures" / "property_setter.json"
        records = json.loads(fixture_path.read_text(encoding="utf-8"))
        settings = {(row.get("field_name"), row["property"]): row["value"] for row in records}
        self.assertEqual(settings[("custom_remarks", "hidden")], "1")
        self.assertEqual(settings[("custom_remarks", "default")], "1")
        self.assertEqual(settings[("remarks", "label")], "Custom Remarks")
        self.assertEqual(settings[("remarks", "read_only_depends_on")], "")
        source = (Path(__file__).parents[1] / "payment_entry_setup.py").read_text(encoding="utf-8")
        self.assertIn(
            '_move_after(field_order, "remarks", "custom_column_break_payment_header")',
            source,
        )
        self.assertIn('("custom_column_break_party", "contact_email")', source)
        self.assertIn(
            '"book_advance_payments_in_separate_party_account",\n        "custom_column_break_party"',
            source,
        )
        self.assertIn('"taxes_and_charges_section",\n        "deductions_or_loss_section"', source)
        self.assertIn('"transaction_references",\n        "accounting_dimensions_section"', source)

    def test_navigation_names_are_unique(self):
        links = [(kind, name) for _, kind, names in GROUPS for name in names]
        self.assertEqual(len(links), len(set(links)))

    def test_voucher_page_contains_analytics_and_requested_reports(self):
        path = Path(__file__).parents[1] / "reckon_accounts/page/voucher_entry/voucher_entry.js"
        source = path.read_text(encoding="utf-8")
        self.assertIn("reckon_accounts.api.voucher_entry_data", source)
        self.assertIn("Voucher Entry Analytics", source)
        self.assertNotIn("reckon-step", source)
        self.assertLess(source.index("Attention Required"), source.index("Voucher Entry Analytics"))
        self.assertLess(source.index("Reports"), source.index("Voucher Entry Analytics"))
        self.assertIn("data-range", source)
        self.assertIn("data-status", source)
        self.assertNotIn("Refresh Analytics", source)
        self.assertIn('page.set_primary_action(__("Refresh")', source)
        self.assertIn('frappe.set_route("List", entry.doctype, "List")', source)
        self.assertIn("List</button>", source)
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
        ):
            self.assertIn(f'"{label}"', source)
        self.assertIn("Financial Reports (ERPNext)", source)
        self.assertNotIn('page_route: "payment-voucher"', source)
        self.assertNotIn('page_route: "receipt-voucher"', source)
        self.assertIn('custom_voucher_subtype: "Direct Expense"', source)
        self.assertIn('custom_voucher_subtype: "Direct Income"', source)
        self.assertIn("frappe.new_doc(entry.doctype", source)

    def test_desktop_app_uses_packaged_custom_icon(self):
        from reckon_accounts import hooks

        icon = hooks.add_to_apps_screen[0]
        self.assertEqual(icon["logo"], "/assets/reckon_accounts/images/reckon-accounts-icon.png")
        self.assertEqual(icon["route"], "/desk/accounts-dashboard")
        self.assertEqual(icon["desk_route"], "/desk/accounts-dashboard")
        path = Path(__file__).parents[1] / "public/images/reckon-accounts-icon.png"
        self.assertTrue(path.is_file())
        self.assertEqual(len(hashlib.sha256(path.read_bytes()).hexdigest()), 64)

    def test_migration_repairs_workspace_sidebar_icon(self):
        path = Path(__file__).parents[1] / "patches/v0_1/sync_desktop_app_icon.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn('"icon_type": "Link"', source)
        self.assertIn('"link_type": "Workspace Sidebar"', source)
        self.assertIn('"standard": 0', source)
        self.assertIn('"link_to": LABEL', source)
        self.assertIn('"link": None', source)
        self.assertIn('"logo_url": ICON_URL', source)
        self.assertIn('"icon_image": ICON_URL', source)

        patches = (Path(__file__).parents[1] / "patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_accounts.patches.v0_1.restore_desktop_app_icon", patches)
        self.assertIn("reckon_accounts.patches.v0_1.fix_desktop_workspace_route", patches)
        self.assertIn("reckon_accounts.patches.v0_1.restore_workspace_sidebar_icon", patches)


if __name__ == "__main__":
    unittest.main()
