import unittest
from pathlib import Path

from reckon_accounts.navigation import GROUPS


ROOT = Path(__file__).parents[1]


class TestVoucherCustomization(unittest.TestCase):
    def test_direct_voucher_service_uses_journal_entry_not_gl_or_payment_entry(self):
        source = (ROOT / "accounting" / "voucher_service.py").read_text(encoding="utf-8")
        self.assertIn('"doctype": "Journal Entry"', source)
        self.assertIn('"voucher_type": "Journal Entry"', source)
        self.assertIn("doc.insert()", source)
        self.assertIn("doc.submit()", source)
        self.assertNotIn('"doctype": "GL Entry"', source)
        self.assertNotIn("ignore_permissions=True", source)
        self.assertNotIn("ignore_permissions = True", source)

    def test_direct_vouchers_validate_expected_account_classes(self):
        source = (ROOT / "accounting" / "voucher_service.py").read_text(encoding="utf-8")
        self.assertIn("account.account_type not in CASH_BANK_TYPES", source)
        self.assertIn("account.root_type != root_type", source)
        self.assertIn("_validate_profit_loss_account(", source)
        self.assertIn('"Expense"', source)
        self.assertIn('"Income"', source)
        self.assertIn("_positive_amount", source)
        self.assertIn("amount <= 0", source)

    def test_pages_route_party_modes_to_standard_payment_entry(self):
        shared = (ROOT / "public" / "js" / "voucher_page.js").read_text(encoding="utf-8")
        payment = (
            ROOT / "reckon_accounts" / "page" / "payment_voucher" / "payment_voucher.js"
        ).read_text(encoding="utf-8")
        receipt = (
            ROOT / "reckon_accounts" / "page" / "receipt_voucher" / "receipt_voucher.js"
        ).read_text(encoding="utf-8")
        self.assertIn('frappe.new_doc("Payment Entry"', shared)
        self.assertIn('partyPaymentType: "Pay"', payment)
        self.assertIn('partyPaymentType: "Receive"', receipt)
        self.assertIn('root_type: "Expense"', payment)
        self.assertIn('root_type: "Income"', receipt)
        self.assertIn('account_type: ["in", ["Cash", "Bank"]]', shared)
        self.assertIn("reckon_accounts.api.direct_payment_voucher", payment)
        self.assertIn("reckon_accounts.api.direct_receipt_voucher", receipt)
        self.assertIn('frappe.set_route("print", result.doctype, result.name, config.title)', shared)

    def test_navigation_exposes_dedicated_voucher_pages(self):
        links = {(kind, name) for _, kind, names in GROUPS for name in names}
        self.assertIn(("Page", "payment-voucher"), links)
        self.assertIn(("Page", "receipt-voucher"), links)
        access = (ROOT / "access_control.py").read_text(encoding="utf-8")
        self.assertIn('_ensure_role_links("Page", "payment-voucher")', access)
        self.assertIn('_ensure_role_links("Page", "receipt-voucher")', access)

    def test_voucher_pages_are_packaged_and_shared_script_loaded(self):
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('app_include_js = ["public/js/voucher_page.js"]', hooks)
        for page in ("payment_voucher", "receipt_voucher"):
            self.assertTrue((ROOT / "reckon_accounts" / "page" / page / f"{page}.json").is_file())
            page_script = ROOT / "reckon_accounts" / "page" / page / f"{page}.js"
            self.assertTrue(page_script.is_file())
            self.assertIn(
                '{% include "reckon_accounts/public/js/voucher_page.js" %}',
                page_script.read_text(encoding="utf-8"),
            )
        for print_format in ("payment_voucher", "receipt_voucher"):
            self.assertTrue(
                (
                    ROOT
                    / "reckon_accounts"
                    / "print_format"
                    / print_format
                    / f"{print_format}.json"
                ).is_file()
            )


if __name__ == "__main__":
    unittest.main()
