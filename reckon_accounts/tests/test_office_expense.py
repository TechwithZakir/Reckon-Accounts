"""Office Expense workflow, doctypes and navigation (runs without a database)."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from reckon_accounts.navigation import GROUPS, sidebar_document, workspace_documents

ROOT = Path(__file__).parents[1]
DOCTYPES = ROOT / "reckon_accounts" / "doctype"
OFFICE_DOCTYPES = (
    "office_expense",
    "office_expense_item",
    "office_expense_settings",
    "office_expense_category_setup",
    "office_expense_payment_setup",
)


class ValidationError(Exception):
    pass


class Doc(SimpleNamespace):
    """Just enough of a Frappe document for the workflow functions."""

    def __init__(self, **values):
        values.setdefault("flags", SimpleNamespace(ignore_permissions=False))
        super().__init__(**values)
        self.db_set = Mock(side_effect=lambda field, value, **kwargs: setattr(self, field, value))

    def get(self, key, default=None):
        return getattr(self, key, default)


SETTINGS = Doc(
    company="Co",
    default_expense_category="Office Supplies",
    default_payment_method="Cash",
    default_cost_center="Main - Co",
    categories=[
        Doc(category="Office Supplies", expense_account="Supplies - Co", enabled=1),
        Doc(category="Office Rent", expense_account="Rent - Co", enabled=1),
        Doc(category="Retired", expense_account="Old - Co", enabled=0),
    ],
    payment_methods=[Doc(payment_method="Cash", payment_account="Cash - Co", enabled=1)],
)
ACCOUNTS = {
    "Supplies - Co": dict(company="Co", is_group=0, disabled=0, root_type="Expense", account_type=""),
    "Rent - Co": dict(company="Co", is_group=0, disabled=0, root_type="Expense", account_type=""),
    "Cash - Co": dict(company="Co", is_group=0, disabled=0, root_type="Asset", account_type="Cash"),
}


class OfficeExpenseWorkflowTests(unittest.TestCase):
    def setUp(self):
        frappe = ModuleType("frappe")
        frappe._ = lambda text: text
        frappe.throw = Mock(side_effect=ValidationError)
        frappe.whitelist = lambda *args, **kwargs: (lambda fn: fn)
        frappe.validate_and_sanitize_search_inputs = lambda fn: fn
        frappe.has_permission = Mock(return_value=True)
        frappe.defaults = SimpleNamespace(get_user_default=Mock(return_value="Co"))
        frappe.get_all = Mock(return_value=[["Cash"]])
        frappe.db = SimpleNamespace(
            exists=Mock(return_value=True), get_value=Mock(side_effect=self._get_value)
        )
        self.payment_entry = SimpleNamespace(
            name="ACC-PAY-0001", flags=SimpleNamespace(), insert=Mock(), submit=Mock()
        )
        frappe.get_doc = Mock(side_effect=self._get_doc)
        self.frappe = frappe

        utils = ModuleType("frappe.utils")
        utils.flt = lambda value, precision=None: float(value or 0)
        document = ModuleType("frappe.model.document")
        document.Document = object
        modules = {
            "frappe": frappe,
            "frappe.utils": utils,
            "frappe.model": ModuleType("frappe.model"),
            "frappe.model.document": document,
        }
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location(
                "reckon_accounts.office_expense", ROOT / "office_expense.py"
            )
            self.workflow = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.workflow)

    def _get_value(self, doctype, name, fields, as_dict=False):
        if doctype == "Account":
            return SimpleNamespace(**ACCOUNTS[name]) if name in ACCOUNTS else None
        if doctype == "Cost Center":
            return SimpleNamespace(company="Co", is_group=0, disabled=0)
        raise AssertionError(doctype)

    def _get_doc(self, doctype, name=None):
        if doctype == "Office Expense Settings":
            return SETTINGS
        if isinstance(doctype, dict):
            self.payment_entry.values = doctype
            return self.payment_entry
        raise AssertionError(doctype)

    def _expense(self, **values):
        defaults = dict(
            name="OEXP-00001",
            company=None,
            docstatus=0,
            posting_date="2026-10-18",
            payment_method=None,
            payee="Stationery shop",
            reference_no=None,
            reference_date=None,
            payment_entry=None,
            journal_entry=None,
            items=[
                Doc(idx=1, expense_category=None, amount=60),
                Doc(idx=2, expense_category="Rent - Co", amount=40),
            ],
        )
        return Doc(**{**defaults, **values})

    def test_validate_fills_company_accounts_and_total(self):
        doc = self._expense()
        self.workflow.validate_office_expense(doc)

        self.assertEqual(doc.company, "Co")
        self.frappe.has_permission.assert_called_with("Company", "read", "Co", throw=True)
        self.assertEqual(doc.payment_method, "Cash")
        self.assertEqual(doc.payment_account, "Cash - Co")
        self.assertEqual(doc.cost_center, "Main - Co")
        self.assertEqual(
            [row.expense_account for row in doc.items], ["Supplies - Co", "Rent - Co"]
        )
        self.assertEqual({row.cost_center for row in doc.items}, {"Main - Co"})
        self.assertEqual(doc.total_amount, 100)
        self.assertEqual(doc.status, "Draft")

    def test_system_saves_skip_the_company_permission_check(self):
        doc = self._expense(company="Co", flags=SimpleNamespace(ignore_permissions=True))
        self.workflow.validate_office_expense(doc)

        self.frappe.has_permission.assert_not_called()

    def test_disabled_category_and_zero_amount_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.workflow.validate_office_expense(
                self._expense(items=[Doc(idx=1, expense_category="Old - Co", amount=5)])
            )
        self.assertIn("is not enabled", self.frappe.throw.call_args.args[0])

        with self.assertRaises(ValidationError):
            self.workflow.validate_office_expense(
                self._expense(items=[Doc(idx=1, expense_category="Rent - Co", amount=0)])
            )
        self.assertIn("greater than zero", self.frappe.throw.call_args.args[0])

    def test_submit_posts_one_balanced_pay_entry(self):
        doc = self._expense()
        self.workflow.validate_office_expense(doc)
        self.workflow.create_office_expense_payment_entry(doc)

        values = self.payment_entry.values
        self.assertEqual(values["payment_type"], "Pay")
        self.assertEqual((values["paid_from"], values["paid_to"]), ("Cash - Co", "Cash - Co"))
        self.assertEqual(values["paid_amount"], 100)
        self.assertEqual(values["rd_office_expense"], "OEXP-00001")
        self.assertEqual(
            [(row["account"], row["amount"]) for row in values["deductions"]],
            [("Supplies - Co", 60), ("Rent - Co", 40)],
        )
        self.assertTrue(self.payment_entry.flags.reckon_office_expense_payment)
        self.payment_entry.insert.assert_called_once_with(ignore_permissions=True)
        self.payment_entry.submit.assert_called_once_with()
        self.assertEqual(doc.payment_entry, "ACC-PAY-0001")
        self.assertEqual(doc.status, "Submitted")

    def test_defaults_report_missing_setup(self):
        self.frappe.db.exists.return_value = False

        self.assertEqual(
            self.workflow.get_office_expense_defaults("Co"), {"configured": False, "company": "Co"}
        )

    def test_defaults_return_friendly_choices(self):
        result = self.workflow.get_office_expense_defaults()

        self.assertTrue(result["configured"])
        self.assertEqual(result["default_expense_account"], "Supplies - Co")
        self.assertEqual(result["categories"], ["Office Rent", "Office Supplies"])
        self.assertEqual(result["payment_methods"], ["Cash"])

    def test_defaults_require_access_to_the_company(self):
        self.frappe.has_permission.side_effect = PermissionError
        with self.assertRaises(PermissionError):
            self.workflow.get_office_expense_defaults("Other")

    def test_search_queries_use_the_form_company(self):
        self.workflow.get_office_expense_payment_methods(
            "Mode of Payment", "Ca", "name", 0, 20, {"company": "Co"}
        )
        self.frappe.has_permission.assert_called_with("Company", "read", "Co", throw=True)
        self.assertEqual(
            self.frappe.get_all.call_args.kwargs["filters"], {"name": ["in", ["Cash"]]}
        )

        self.workflow.get_office_expense_categories("Account", "", "name", 0, 20, {"company": "Co"})
        self.assertEqual(
            self.frappe.get_all.call_args.kwargs["filters"]["name"],
            ["in", ["Rent - Co", "Supplies - Co"]],
        )


class OfficeExpenseDoctypeTests(unittest.TestCase):
    def _json(self, name):
        return json.loads((DOCTYPES / name / f"{name}.json").read_text(encoding="utf-8"))

    def test_doctypes_belong_to_reckon_accounts(self):
        for name in OFFICE_DOCTYPES:
            with self.subTest(doctype=name):
                self.assertEqual(self._json(name)["module"], "Reckon Accounts")
                for path in (DOCTYPES / name).glob("*.*"):
                    self.assertNotIn("reckon_distribution", path.read_text(encoding="utf-8"))

    def test_permissions_use_accounts_roles_only(self):
        expense = {row["role"]: row for row in self._json("office_expense")["permissions"]}
        self.assertEqual(
            set(expense),
            {
                "System Manager",
                "Accounts Manager",
                "Reckon Accounts Manager",
                "Accounts User",
                "Reckon Accounts User",
            },
        )
        self.assertTrue(expense["Reckon Accounts User"]["submit"])
        self.assertFalse(expense["Reckon Accounts User"]["cancel"])
        self.assertTrue(expense["Reckon Accounts Manager"]["cancel"])

        settings = {row["role"]: row for row in self._json("office_expense_settings")["permissions"]}
        self.assertTrue(settings["Reckon Accounts Manager"]["write"])
        self.assertFalse(settings["Reckon Accounts User"]["write"])
        self.assertTrue(settings["Reckon Accounts User"]["read"])

    def test_form_script_passes_the_form_company(self):
        source = (DOCTYPES / "office_expense" / "office_expense.js").read_text(encoding="utf-8")
        self.assertIn("reckon_accounts.office_expense.get_office_expense_defaults", source)
        self.assertIn("args: { company: frm.doc.company || null }", source)
        self.assertEqual(source.count("filters: { company: frm.doc.company }"), 2)


class OfficeExpenseNavigationTests(unittest.TestCase):
    def test_office_expenses_follow_voucher_entry(self):
        self.assertEqual(
            GROUPS[1], ("Office Expenses", "DocType", ("Office Expense", "Office Expense Settings"))
        )

    def test_sidebar_and_workspace_link_both_doctypes(self):
        expected = {
            ("Office Expenses", "DocType", "Office Expense"),
            ("Office Expense Setup", "DocType", "Office Expense Settings"),
        }
        sidebar = {
            (item.get("label"), item.get("link_type"), item.get("link_to"))
            for item in sidebar_document()["items"]
        }
        workspace = {
            (item.get("label"), item.get("link_type"), item.get("link_to"))
            for item in next(workspace_documents())["links"]
        }
        self.assertTrue(expected.issubset(sidebar))
        self.assertTrue(expected.issubset(workspace))

    def test_generated_sidebar_file_is_in_sync(self):
        path = ROOT / "workspace_sidebar" / "reckon_accounts.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), sidebar_document())


if __name__ == "__main__":
    unittest.main()
