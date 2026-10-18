"""Payment Entry controller composition with Reckon Distribution (runs without a database).

Frappe keeps only the last installed app's ``override_doctype_class`` for a doctype,
so this app's controller must carry Distribution's Office Expense behaviour too (and
vice versa) for both to apply whichever hook wins.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).parents[1]
DISTRIBUTION_MODULE = "reckon_distribution.overrides.office_expense_payment"


class ValidationError(Exception):
    pass


class ERPNextPaymentEntry:
    """The few ERPNext controller methods the mixins call through ``super()``."""

    def __init__(self, **values):
        self.calls = []
        self.meta = SimpleNamespace(get_label=lambda fieldname: fieldname)
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


class FakeOfficeExpensePaymentMixin:
    """Stands in for ``reckon_distribution.overrides.office_expense_payment``."""

    def set_missing_values(self):
        if not self.get("rd_office_expense"):
            return super().set_missing_values()
        self.calls.append("office expense")


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


class PaymentEntryCompositionTests(unittest.TestCase):
    def setUp(self):
        frappe = ModuleType("frappe")
        frappe._ = lambda text: text
        frappe.throw = Mock(side_effect=ValidationError)
        frappe.has_permission = Mock(return_value=True)
        accounts = {
            "Cash - Co": SimpleNamespace(
                name="Cash - Co", company="Co", is_group=0, account_type="Cash", root_type="Asset"
            ),
            "Rent - Co": SimpleNamespace(
                name="Rent - Co", company="Co", is_group=0, account_type="", root_type="Expense"
            ),
        }
        frappe.get_cached_doc = Mock(side_effect=lambda doctype, name: accounts[name])
        self.frappe = frappe

        payment_entry = ModuleType("erpnext.accounts.doctype.payment_entry.payment_entry")
        payment_entry.PaymentEntry = ERPNextPaymentEntry
        payment_entry.get_account_details = Mock(
            return_value=SimpleNamespace(account_currency="BDT", account_type="Cash")
        )

        self.modules = {
            "frappe": frappe,
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

    def _controller(self, distribution_modules):
        modules = {**self.modules, **distribution_modules}
        with patch.dict(sys.modules, modules):
            direct = _load(
                ROOT / "overrides" / "direct_voucher.py", "reckon_accounts.overrides.direct_voucher"
            )
            module = _load(
                ROOT / "overrides" / "payment_entry.py", "reckon_accounts.overrides.payment_entry"
            )
        return direct.DirectVoucherPaymentMixin, module

    def _with_distribution(self):
        office = ModuleType(DISTRIBUTION_MODULE)
        office.OfficeExpensePaymentMixin = FakeOfficeExpensePaymentMixin
        return self._controller(
            {
                "reckon_distribution": _package("reckon_distribution"),
                "reckon_distribution.overrides": _package("reckon_distribution.overrides"),
                DISTRIBUTION_MODULE: office,
            }
        )

    def _without_distribution(self):
        # ``None`` in sys.modules makes ``import reckon_distribution`` fail as if absent.
        return self._controller({"reckon_distribution": None})

    def _direct_expense(self, controller, **values):
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
        return controller(**{**defaults, **values})

    def test_hook_still_points_at_reckon_accounts_controller(self):
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"Payment Entry": "reckon_accounts.overrides.payment_entry.PaymentEntry"', hooks)

    def test_without_distribution_only_direct_vouchers_are_added(self):
        direct, module = self._without_distribution()

        self.assertEqual(module.PaymentEntry.__mro__[1:], (direct, ERPNextPaymentEntry, object))
        entry = module.PaymentEntry(payment_type="Pay", rd_office_expense="OE-0001")
        entry.set_missing_values()
        self.assertEqual(entry.calls, ["erpnext"])

    def test_with_distribution_both_mixins_are_composed_in_shared_order(self):
        direct, module = self._with_distribution()

        self.assertEqual(
            module.PaymentEntry.__mro__[1:],
            (FakeOfficeExpensePaymentMixin, direct, ERPNextPaymentEntry, object),
        )

    def test_office_expense_reaches_distribution_behaviour(self):
        _, module = self._with_distribution()

        entry = module.PaymentEntry(payment_type="Pay", rd_office_expense="OE-0001")
        entry.set_missing_values()

        self.assertEqual(entry.calls, ["office expense"])

    def test_direct_expense_clears_party_and_posts_expense_leg(self):
        _, module = self._with_distribution()

        entry = self._direct_expense(module.PaymentEntry)
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

    def test_direct_expense_still_rejects_deductions(self):
        _, module = self._with_distribution()

        entry = self._direct_expense(module.PaymentEntry, deductions=[SimpleNamespace(amount=1)])
        with self.assertRaises(ValidationError):
            entry.set_missing_values()

    def test_party_settlement_falls_through_to_erpnext(self):
        _, module = self._with_distribution()

        entry = module.PaymentEntry(payment_type="Receive", custom_voucher_subtype="Party Settlement")
        entry.set_missing_values()
        entry.add_party_gl_entries([])
        entry.set_title()

        self.assertEqual(entry.calls, ["erpnext", "erpnext gl", "erpnext title"])

    def test_old_constant_imports_keep_working(self):
        _, module = self._without_distribution()

        self.assertEqual(module.DIRECT_SUBTYPES, {"Direct Expense": "Pay", "Direct Income": "Receive"})
        self.assertEqual(module.CASH_BANK_TYPES, {"Cash", "Bank"})

    def test_old_distribution_without_mixin_module_is_skipped(self):
        direct, module = self._controller(
            {
                "reckon_distribution": _package("reckon_distribution"),
                "reckon_distribution.overrides": _package("reckon_distribution.overrides"),
            }
        )

        self.assertEqual(module.PaymentEntry.__mro__[1:], (direct, ERPNextPaymentEntry, object))

    def test_broken_distribution_import_is_not_swallowed(self):
        error = ModuleNotFoundError("No module named 'missing_dependency'", name="missing_dependency")
        with patch("importlib.import_module", side_effect=error):
            with self.assertRaises(ModuleNotFoundError):
                self._controller({})


if __name__ == "__main__":
    unittest.main()
