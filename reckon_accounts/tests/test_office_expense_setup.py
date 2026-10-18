"""Default Office Expense Settings seed against an in-memory chart (no database)."""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
ALL_DOCTYPES = ("Account", "Cost Center", "Mode of Payment", "Office Expense Settings")


class Row(dict):
    __getattr__ = dict.get


class FakeSite:
    """The handful of frappe calls the seed makes, backed by plain lists."""

    def __init__(self, abbr="CO", doctypes=ALL_DOCTYPES):
        self.abbr = abbr
        self.doctypes = set(doctypes)
        self.records = {doctype: [] for doctype in ALL_DOCTYPES}
        self.inserted = []

    def add(self, doctype, **values):
        values.setdefault("disabled", 0)
        values.setdefault("lft", len(self.records[doctype]))
        self.records[doctype].append(Row(values))

    def account(self, account_name, root_type, *, is_group=0, parent=None, account_type=None):
        self.add(
            "Account",
            name=f"{account_name} - {self.abbr}",
            account_name=account_name,
            company="Co",
            root_type=root_type,
            is_group=is_group,
            parent_account=parent,
            account_type=account_type,
        )
        return f"{account_name} - {self.abbr}"

    def _matches(self, row, filters):
        if isinstance(filters, str):
            return row.name == filters
        return all(row.get(key) == value for key, value in filters.items())

    def _find(self, doctype, filters):
        rows = [row for row in self.records.get(doctype, []) if self._matches(row, filters)]
        return sorted(rows, key=lambda row: row.lft)

    # frappe.get_all
    def get_all(self, doctype, filters=None, fields=None, pluck=None, order_by=None):
        if doctype == "DocType":
            return [name for name in filters["name"][1] if name in self.doctypes]
        rows = self._find(doctype, filters or {})
        if pluck:
            return [row[pluck] for row in rows]
        return [Row({field: row.get(field) for field in fields}) for row in rows]

    # frappe.db.exists
    def exists(self, doctype, filters=None):
        rows = self._find(doctype, filters)
        return rows[0].name if rows else None

    # frappe.db.get_value
    def get_value(self, doctype, filters, fieldname="name", as_dict=False, order_by=None):
        rows = self._find(doctype, filters)
        if not rows:
            return None
        if isinstance(fieldname, list):
            return Row({field: rows[0].get(field) for field in fieldname})
        return rows[0][fieldname]

    # frappe.get_doc
    def get_doc(self, values):
        site = self

        def insert(ignore_permissions=False):
            doctype = values["doctype"]
            if doctype == "Account":
                name = f"{values['account_name']} - {site.abbr}"
            elif doctype == "Cost Center":
                name = f"{values['cost_center_name']} - {site.abbr}"
            elif doctype == "Mode of Payment":
                name = values["mode_of_payment"]
            else:
                name = values["company"]
            doc.name = name
            site.add(doctype, name=name, **{k: v for k, v in values.items() if k != "doctype"})
            site.inserted.append((doctype, name))
            return doc

        doc = SimpleNamespace(name=None, insert=insert)
        return doc

    def settings(self):
        return self.records["Office Expense Settings"][0]


def standard_chart(site):
    """What ERPNext's standard chart gives a new company."""
    expenses = site.account("Expenses", "Expense", is_group=1)
    site.account("Direct Expenses", "Expense", is_group=1, parent=expenses)
    site.account("Indirect Expenses", "Expense", is_group=1, parent=expenses)
    assets = site.account("Application of Funds (Assets)", "Asset", is_group=1)
    site.account("Cash", "Asset", parent=assets, account_type="Cash")
    site.account("Main Bank", "Asset", parent=assets, account_type="Bank")
    site.add("Cost Center", name="Main - CO", company="Co", is_group=0)
    site.add("Mode of Payment", name="Cash")
    site.add("Mode of Payment", name="Bank")


class OfficeExpenseDefaultsTests(unittest.TestCase):
    def _seed(self, site, company="Co"):
        frappe = ModuleType("frappe")
        frappe.get_all = site.get_all
        frappe.get_doc = site.get_doc
        frappe.db = SimpleNamespace(exists=site.exists, get_value=site.get_value)
        utils = ModuleType("frappe.utils")
        utils.cint = lambda value: int(value or 0)
        with patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils}):
            spec = importlib.util.spec_from_file_location(
                "reckon_accounts.office_expense_setup", ROOT / "office_expense_setup.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.ensure_office_expense_defaults(company)

    def test_standard_chart_gets_categories_cash_and_bank(self):
        site = FakeSite()
        standard_chart(site)

        created = self._seed(site)

        settings = site.settings()
        self.assertEqual(created[-1], "Office Expense Settings")
        self.assertEqual(len(settings.categories), 10)
        self.assertEqual(settings.default_expense_category, "Office Supplies")
        self.assertEqual(settings.default_payment_method, "Cash")
        self.assertEqual(settings.default_cost_center, "Main - CO")
        accounts = {row["category"]: row["expense_account"] for row in settings.categories}
        self.assertEqual(accounts["Office Rent"], "Office Rent - CO")
        rent = site.exists("Account", {"name": "Office Rent - CO"})
        parent = site.get_value("Account", {"name": rent}, "parent_account")
        self.assertEqual(parent, "Indirect Expenses - CO")
        self.assertEqual(
            site.get_value("Account", {"name": "Vehicle Fuel - CO"}, "parent_account"),
            "Direct Expenses - CO",
        )
        self.assertEqual(
            [(row["payment_method"], row["payment_account"]) for row in settings.payment_methods],
            [("Cash", "Cash - CO"), ("Bank", "Main Bank - CO")],
        )
        # Only the ten category ledgers and the settings are new.
        self.assertEqual(
            sorted({doctype for doctype, _name in site.inserted}),
            ["Account", "Office Expense Settings"],
        )
        self.assertEqual(len(site.inserted), 11)

    def test_rerun_creates_nothing(self):
        site = FakeSite()
        standard_chart(site)
        self._seed(site)
        site.inserted.clear()

        self.assertEqual(self._seed(site), [])
        self.assertEqual(site.inserted, [])

    def test_existing_settings_are_never_replaced(self):
        site = FakeSite()
        standard_chart(site)
        site.add("Office Expense Settings", name="Co", company="Co", categories=[])

        self.assertEqual(self._seed(site), [])
        self.assertEqual(site.inserted, [])
        self.assertEqual(site.settings().categories, [])

    def test_missing_doctypes_skip_quietly(self):
        site = FakeSite(doctypes=("Account", "Cost Center", "Mode of Payment"))

        self.assertEqual(self._seed(site), [])
        self.assertEqual(site.inserted, [])

    def test_empty_chart_gets_roots_cost_center_cash_and_mode(self):
        site = FakeSite()

        created = self._seed(site)

        self.assertIn("Cost Center: Main - CO", created)
        self.assertIn("Mode of Payment: Cash", created)
        self.assertIn("Account: Expenses - CO", created)
        self.assertIn("Account: Office Cash - CO", created)
        settings = site.settings()
        self.assertEqual(settings.payment_methods, [
            {"payment_method": "Cash", "payment_account": "Office Cash - CO", "enabled": 1}
        ])
        self.assertEqual(
            site.get_value("Account", {"name": "Office Cash - CO"}, "account_type"), "Cash"
        )

    def test_unrelated_ledger_with_same_label_is_not_reused(self):
        site = FakeSite()
        standard_chart(site)
        site.account("Office Rent", "Asset")  # a custom chart's prepaid-rent asset
        site.account("Utilities", "Asset")
        site.account("Utilities - Distribution", "Expense", parent="Indirect Expenses - CO")

        self._seed(site)

        accounts = {row["category"]: row["expense_account"] for row in site.settings().categories}
        self.assertEqual(accounts["Office Rent"], "Office Rent - Office Expense - CO")
        # Ledgers made by Reckon Distribution's earlier seed are reused.
        self.assertEqual(accounts["Utilities"], "Utilities - Distribution - CO")
        self.assertNotIn(("Account", "Utilities - Office Expense - CO"), site.inserted)


if __name__ == "__main__":
    unittest.main()
