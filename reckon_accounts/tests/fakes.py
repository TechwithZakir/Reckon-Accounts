"""Small permission/query doubles; they do not substitute for bench tests."""

from contextlib import contextmanager
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from reckon_accounts.accounting.adapters import REQUIRED_GL


class Record(dict):
    def __getattr__(self, name):
        return self.get(name)


class Meta:
    def __init__(self, fields=(), *, tree=False, title=None):
        self.fields = {
            key: SimpleNamespace(fieldname=key, fieldtype="Data", options=None, label=key)
            for key in fields
        }
        self.is_tree = tree
        self.title_field = title

    def has_field(self, key):
        return key in self.fields

    def get_field(self, key):
        return self.fields.get(key)


class FakeGateway:
    def __init__(self):
        self.records = {
            "Company": [Record(name="Co", default_currency="BDT", default_finance_book="Main")],
            "Account": [
                Record(name="AR", company="Co", is_group=0, account_currency="USD", lft=1, rgt=2),
                Record(name="Bank", company="Co", is_group=0, account_currency="BDT", lft=3, rgt=4),
            ],
            "Customer": [
                Record(name="Alice", customer_name="Alice Ltd"),
                Record(name="Bob", customer_name="Bob Ltd"),
            ],
            "Party Type": [Record(name="Customer")],
            "Journal Entry": [
                Record(name="JV-1", company="Co", voucher_type="Journal Entry"),
                Record(name="JV-2", company="Co", voucher_type="Journal Entry"),
            ],
            "Payment Entry": [Record(name="PE-1", company="Co", payment_type="Receive")],
            "Finance Book": [Record(name="Main"), Record(name="Other")],
            "Cost Center": [
                Record(name="Main CC", company="Co", lft=1, rgt=4),
                Record(name="Child CC", company="Co", lft=2, rgt=3),
            ],
            "Project": [Record(name="Project A", company="Co")],
            "Fiscal Year": [
                Record(
                    name="2026",
                    year_start_date=date(2026, 1, 1),
                    year_end_date=date(2026, 12, 31),
                    companies=[],
                )
            ],
            "GL Entry": [],
        }
        self.metas = {
            doctype: Meta(set().union(*(record.keys() for record in records)))
            for doctype, records in self.records.items()
        }
        self.metas["GL Entry"] = Meta(
            REQUIRED_GL | {"name", "creation", "cost_center", "project", "remarks"}
        )
        for key, doctype in (("cost_center", "Cost Center"), ("project", "Project")):
            self.metas["GL Entry"].fields[key].fieldtype = "Link"
            self.metas["GL Entry"].fields[key].options = doctype
        self.metas["Customer"].title_field = "customer_name"
        self.metas["Account"].is_tree = True
        self.metas["Cost Center"].is_tree = True
        self.metas["Accounts Settings"] = Meta(["ignore_is_opening_check_for_reporting"])
        self.denied_docs = set()
        self.denied_list = set()
        self.denied_types = set()
        self.hidden_fields = {}
        self.queries = []
        self.ignore_opening = False
        self.definitions = []
        self.report_denied = False
        self.export_denied = False
        self.frappe = ModuleType("frappe")
        self.frappe.__version__ = "15.0.0"
        self.frappe.session = SimpleNamespace(user="accountant@example.com")
        self.frappe.PermissionError = PermissionError
        self.frappe.DoesNotExistError = KeyError
        self.frappe.local = SimpleNamespace(response={})
        self.frappe.get_doc = self.get_doc
        self.frappe.has_permission = self.has_permission
        self.frappe.get_all = self.get_all
        self.frappe.get_meta = self.meta
        self.frappe.throw = self.throw
        self.frappe.db = SimpleNamespace(get_single_value=lambda *args: self.ignore_opening)
        self.frappe.whitelist = lambda *args, **kwargs: lambda fn: fn
        self.frappe.validate_and_sanitize_search_inputs = lambda fn: fn

    def get_all(self, doctype, **kwargs):
        if doctype != "Accounting Dimension":
            raise AssertionError("Unrestricted financial query")
        return self.definitions

    def throw(self, message, exc=ValueError):
        raise exc(message)

    def has_permission(self, doctype, ptype="read", throw=False, **kwargs):
        permitted = doctype not in self.denied_types and not (
            ptype == "export" and self.export_denied
        )
        if throw and not permitted:
            raise PermissionError("Denied")
        return permitted

    def get_doc(self, doctype, name):
        return next(record for record in self.records.get(doctype, []) if record["name"] == name)

    def meta(self, doctype):
        return self.metas.get(doctype, Meta())

    def can_read_type(self, doctype):
        return doctype not in self.denied_types

    def can_read_document(self, doctype, name):
        return self.can_read_type(doctype) and (doctype, name) not in self.denied_docs

    def list_records(self, doctype, *, filters, limit, or_filters=None, order_by="name asc"):
        self.queries.append((doctype, filters, limit))
        if not self.can_read_type(doctype):
            raise PermissionError("No read permission")
        if isinstance(filters, dict):
            filters = [
                [key, *(value if isinstance(value, list) else ["=", value])]
                for key, value in filters.items()
            ]

        def matches(record, condition):
            key, op, value = condition
            actual = record.get(key)
            if op == "=":
                return actual == value
            if op == "in":
                return actual in value
            if op == "<=":
                return actual <= value
            if op == ">=":
                return actual >= value
            if op == "like":
                return value.strip("%") in str(actual or "")
            raise AssertionError(op)

        selected = [
            dict(record)
            for record in self.records.get(doctype, [])
            if (doctype, record["name"]) not in self.denied_list
            and all(matches(record, item) for item in filters)
            and (not or_filters or any(matches(record, item) for item in or_filters))
        ]
        for key in reversed(order_by.split(", ")):
            field = key.split()[0]
            selected.sort(key=lambda row: row.get(field, ""))
        for record in selected:
            for field in self.hidden_fields.get(doctype, []):
                record.pop(field, None)
        return selected[:limit]

    @contextmanager
    def installed(self):
        modules = {"frappe": self.frappe}
        for key in (
            "frappe.desk",
            "frappe.desk.query_report",
            "frappe.model",
            "frappe.model.meta",
            "frappe.utils",
            "erpnext",
        ):
            modules[key] = ModuleType(key)

        def get_report_doc(name):
            if self.report_denied:
                raise PermissionError("Report denied")

        modules["frappe.desk.query_report"].get_report_doc = get_report_doc
        modules["frappe.model.meta"].get_field_precision = lambda *args, **kwargs: 2
        modules["frappe.utils"].flt = lambda value, precision: float(
            Decimal(str(value)).quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)
        )
        modules["frappe.utils"].now_datetime = lambda: datetime(2026, 2, 1)
        modules["erpnext"].__version__ = "15.0.0"
        with patch.dict("sys.modules", modules):
            yield modules


def gl(name="gl-1", **changes):
    return Record(
        {
            "name": name,
            "company": "Co",
            "account": "AR",
            "posting_date": date(2026, 1, 10),
            "creation": datetime(2026, 1, 10),
            "debit": 100,
            "credit": 0,
            "account_currency": "USD",
            "debit_in_account_currency": 10,
            "credit_in_account_currency": 0,
            "party_type": "Customer",
            "party": "Alice",
            "voucher_type": "Journal Entry",
            "voucher_no": "JV-1",
            "is_opening": "No",
            "is_cancelled": 0,
            "finance_book": None,
            "cost_center": None,
            "project": None,
            "remarks": "Memo",
        }
        | changes
    )
