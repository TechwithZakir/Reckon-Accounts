import json
import unittest
from pathlib import Path

from reckon_accounts.navigation import GROUPS

ROOT = Path(__file__).parents[1]


class TestVoucherCustomization(unittest.TestCase):
    def test_direct_vouchers_use_standard_payment_entry(self):
        source = (ROOT / "accounting" / "voucher_service.py").read_text(encoding="utf-8")
        self.assertIn('"doctype": "Payment Entry"', source)
        self.assertIn('payment_type="Pay"', source)
        self.assertIn('payment_type="Receive"', source)
        self.assertIn('custom_voucher_subtype="Direct Expense"', source)
        self.assertIn('custom_voucher_subtype="Direct Income"', source)
        self.assertNotIn('"doctype": "Journal Entry"', source)

    def test_payment_entry_override_adds_direct_gl_leg(self):
        source = (ROOT / "overrides" / "payment_entry.py").read_text(encoding="utf-8")
        self.assertIn("class PaymentEntry(ERPNextPaymentEntry)", source)
        self.assertIn(
            'DIRECT_SUBTYPES = {"Direct Expense": "Pay", "Direct Income": "Receive"}',
            source,
        )
        self.assertIn("def add_party_gl_entries", source)
        self.assertIn("root_type=profit_loss_root_type", source)
        self.assertNotIn("ignore_permissions=True", source)

    def test_payment_entry_custom_field_is_fixture_synced(self):
        records = json.loads((ROOT / "fixtures" / "custom_field.json").read_text(encoding="utf-8"))
        field = records[0]
        self.assertEqual(field["dt"], "Payment Entry")
        self.assertEqual(field["fieldname"], "custom_voucher_subtype")
        self.assertIn("Direct Expense", field["options"])
        self.assertIn("Direct Income", field["options"])

    def test_navigation_removes_dedicated_voucher_pages(self):
        links = {(kind, name) for _, kind, names in GROUPS for name in names}
        self.assertNotIn(("Page", "payment-voucher"), links)
        self.assertNotIn(("Page", "receipt-voucher"), links)
        for page in ("payment_voucher", "receipt_voucher"):
            page_root = ROOT / "reckon_accounts" / "page" / page
            self.assertFalse((page_root / f"{page}.json").exists())
            self.assertFalse((page_root / f"{page}.js").exists())
        self.assertFalse((ROOT / "public" / "js" / "voucher_page.js").exists())


if __name__ == "__main__":
    unittest.main()
