"""Payment Entry controller: Office Expense and direct vouchers (runs without a database).

Frappe keeps one ``override_doctype_class`` per doctype, so both behaviours are
mixins composed into the single registered controller.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).parents[1]


class ValidationError(Exception):
    pass


class ERPNextPaymentEntry:
    """The few ERPNext controller methods the mixins call through ``super()``."""

    def __init__(self, **values):
        self.calls = []
        self.flags = {}
        self.meta = SimpleNamespace(get_label=lambda fieldname: fieldname, has_field=lambda f: True)
        self.__dict__.update(values)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def set(self, key, value):
        self.__dict__[key] = value

    def get_gl_dict(self, values, item=None):
        return values

    def set_missing_values(self):
        self.calls.append("erpnext")

    def add_party_gl_entries(self, gl_entries):
        self.calls.append("erpnext gl")

    def set_title(self):
        self.calls.append("erpnext title")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _package(name):
    module = ModuleType(name)
    module.__path__ = []
    return module


class PaymentEntryControllerTests(unittest.TestCase):
    def setUp(self):
        frappe = ModuleType("frappe")
        frappe._ = lambda text: text
        frappe.throw = Mock(side_effect=ValidationError)
        frappe.has_permission = Mock(return_value=True)
        frappe.db = SimpleNamespace(
            get_value=Mock(return_value=SimpleNamespace(company="Co", payment_entry=None))
        )
        accounts = {
            "Cash - Co": SimpleNamespace(
                name="Cash - Co", company="Co", is_group=0, account_type="Cash", root_type="Asset"
            ),
            "Rent - Co": SimpleNamespace(
                name="Rent - Co", company="Co", is_group=0, account_type="", root_type="Expense"
            ),
        }
        frappe.get_cached_doc = Mock(side_effect=lambda doctype, name: accounts[name])
        utils = ModuleType("frappe.utils")
        utils.flt = lambda value, precision=None: float(value or 0)
        frappe.utils = utils
        self.frappe = frappe

        payment_entry = ModuleType("erpnext.accounts.doctype.payment_entry.payment_entry")
        payment_entry.PaymentEntry = ERPNextPaymentEntry
        payment_entry.get_account_details = Mock(
            return_value=SimpleNamespace(
                account_currency="BDT", account_type="Cash", account_balance=500
            )
        )
        self.get_account_details = payment_entry.get_account_details

        modules = {
            "frappe": frappe,
            "frappe.utils": utils,
            "erpnext": _package("erpnext"),
            "erpnext.accounts": _package("erpnext.accounts"),
            "erpnext.accounts.doctype": _package("erpnext.accounts.doctype"),
            "erpnext.accounts.doctype.payment_entry": _package(
                "erpnext.accounts.doctype.payment_entry"
            ),
            "erpnext.accounts.doctype.payment_entry.payment_entry": payment_entry,
            "reckon_accounts": _package("reckon_accounts"),
            "reckon_accounts.overrides": _package("reckon_accounts.overrides"),
        }
        with patch.dict(sys.modules, modules):
            overrides = ROOT / "overrides"
            self.direct = _load(
                overrides / "direct_voucher.py", "reckon_accounts.overrides.direct_voucher"
            ).DirectVoucherPaymentMixin
            self.office = _load(
                overrides / "office_expense_payment.py",
                "reckon_accounts.overrides.office_expense_payment",
            ).OfficeExpensePaymentMixin
            self.module = _load(
                overrides / "payment_entry.py", "reckon_accounts.overrides.payment_entry"
            )
        self.controller = self.module.PaymentEntry

    def _direct_expense(self, **values):
        defaults = {
            "company": "Co",
            "payment_type": "Pay",
            "custom_voucher_subtype": "Direct Expense",
            "paid_from": "Cash - Co",
            "paid_to": "Rent - Co",
            "paid_amount": 100,
            "received_amount": 100,
            "base_received_amount": 100,
            "transaction_currency": "BDT",
            "transaction_exchange_rate": 1,
            "posting_date": "2026-10-18",
            "cost_center": "Main - Co",
            "party_type": "Supplier",
            "party": "Stale Supplier",
            "references": ["stale"],
        }
        return self.controller(**{**defaults, **values})

    def _office_expense(self, **values):
        defaults = {
            "name": "ACC-PAY-0001",
            "company": "Co",
            "payment_type": "Pay",
            "custom_voucher_subtype": "Party Settlement",
            "rd_office_expense": "OE-0001",
            "party": None,
            "party_type": None,
            "paid_from": "Cash - Co",
            "paid_to": "Cash - Co",
            "paid_amount": 100,
            "deductions": [SimpleNamespace(amount=60), SimpleNamespace(amount=40)],
            "posting_date": "2026-10-18",
            "cost_center": "Main - Co",
            "party_account": "Creditors - Co",
            "references": ["stale"],
            "flags": {"reckon_office_expense_payment": True},
        }
        return self.controller(**{**defaults, **values})

    def test_hook_points_at_the_composed_controller(self):
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"Payment Entry": "reckon_accounts.overrides.payment_entry.PaymentEntry"', hooks)

    def test_both_mixins_sit_in_front_of_erpnext(self):
        self.assertEqual(
            self.controller.__mro__[1:], (self.office, self.direct, ERPNextPaymentEntry, object)
        )

    def test_direct_expense_clears_party_and_posts_expense_leg(self):
        entry = self._direct_expense()
        entry.set_missing_values()
        gl_entries = []
        entry.add_party_gl_entries(gl_entries)
        entry.set_title()

        self.assertEqual(entry.calls, [])
        self.assertIsNone(entry.party)
        self.assertIsNone(entry.party_type)
        self.assertEqual(entry.references, [])
        self.assertEqual(entry.paid_to_account_currency, "BDT")
        self.assertEqual(len(gl_entries), 1)
        self.assertEqual(gl_entries[0]["account"], "Rent - Co")
        self.assertEqual(gl_entries[0]["debit"], 100)
        self.assertEqual(gl_entries[0]["against"], "Cash - Co")
        self.assertEqual(entry.title, "Direct Expense - Rent - Co")
        self.frappe.db.get_value.assert_not_called()

    def test_direct_expense_still_rejects_deductions(self):
        entry = self._direct_expense(deductions=[SimpleNamespace(amount=1)])
        with self.assertRaises(ValidationError):
            entry.set_missing_values()

    def test_party_settlement_falls_through_to_erpnext(self):
        entry = self.controller(payment_type="Receive", custom_voucher_subtype="Party Settlement")
        entry.set_missing_values()
        entry.add_party_gl_entries([])
        entry.set_title()

        self.assertEqual(entry.calls, ["erpnext", "erpnext gl", "erpnext title"])

    def test_office_expense_payment_is_balanced_without_party(self):
        entry = self._office_expense()
        entry.set_missing_values()

        self.assertEqual(entry.calls, [])
        self.frappe.db.get_value.assert_called_once_with(
            "Office Expense", "OE-0001", ["company", "payment_entry"], as_dict=True
        )
        self.get_account_details.assert_called_once_with("Cash - Co", "2026-10-18", "Main - Co")
        self.assertEqual(entry.paid_from_account_currency, "BDT")
        self.assertEqual(entry.paid_to_account_type, "Cash")
        self.assertEqual(entry.paid_to_account_balance, 500)
        self.assertIsNone(entry.party_account)
        self.assertEqual(entry.party_account_currency, "BDT")
        self.assertEqual(entry.references, [])

    def test_office_expense_cannot_also_be_a_direct_voucher(self):
        entry = self._office_expense(custom_voucher_subtype="Direct Expense")
        with self.assertRaises(ValidationError):
            entry.set_missing_values()

        self.assertIn("direct", self.frappe.throw.call_args.args[0])
        self.assertEqual(entry.calls, [])

    def test_unbalanced_office_expense_is_rejected(self):
        entry = self._office_expense(paid_amount=90)
        with self.assertRaises(ValidationError):
            entry.set_missing_values()

        self.assertIn("equal the paid amount", self.frappe.throw.call_args.args[0])

    def test_office_expense_of_another_company_is_rejected(self):
        self.frappe.db.get_value.return_value = SimpleNamespace(company="Other", payment_entry=None)
        entry = self._office_expense()
        with self.assertRaises(ValidationError):
            entry.set_missing_values()

        self.assertIn("same Company", self.frappe.throw.call_args.args[0])

    def test_unlinked_office_expense_falls_through(self):
        entry = self._office_expense(flags={})
        entry.set_missing_values()

        self.assertEqual(entry.calls, ["erpnext"])

    def test_old_constant_imports_keep_working(self):
        self.assertEqual(
            self.module.DIRECT_SUBTYPES, {"Direct Expense": "Pay", "Direct Income": "Receive"}
        )
        self.assertEqual(self.module.CASH_BANK_TYPES, {"Cash", "Bank"})

    def test_office_expense_link_field_is_fixture_synced(self):
        import json

        records = json.loads((ROOT / "fixtures" / "custom_field.json").read_text(encoding="utf-8"))
        field = next(row for row in records if row["fieldname"] == "rd_office_expense")
        self.assertEqual(field["dt"], "Payment Entry")
        self.assertEqual(field["options"], "Office Expense")
        self.assertTrue(field["hidden"] and field["read_only"] and field["no_copy"])
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"Payment Entry-rd_office_expense"', hooks)


if __name__ == "__main__":
    unittest.main()
