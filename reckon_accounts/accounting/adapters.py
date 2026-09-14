"""Read-only Frappe 15/16 adapters with runtime schema and permission checks.

Inspected upstream revisions are recorded in UPSTREAM_CONTRACTS.md. Query and
document permissions are both enforced. Bounds protect this initial materialized
implementation; a limit error never returns a partial financial result.
"""

from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from reckon_accounts.accounting.dimensions import dimension_contract, expand_selection
from reckon_accounts.accounting.filters import parse_ledger_filters
from reckon_accounts.accounting.party import party_name, permitted_particulars, voucher_label
from reckon_accounts.accounting.permissions import PermissionScope, ScopeError
from reckon_accounts.accounting.service import Posting, build_ledger, validate_report_scope

MAX_GL_ROWS = 5000
REQUIRED_GL = {
    "company",
    "account",
    "posting_date",
    "debit",
    "credit",
    "account_currency",
    "debit_in_account_currency",
    "credit_in_account_currency",
    "party_type",
    "party",
    "voucher_type",
    "voucher_no",
    "is_opening",
    "is_cancelled",
    "finance_book",
}


class Frappe15Gateway:
    def __init__(self, frappe):
        self.frappe = frappe
        self.document_permissions = {}

    def meta(self, doctype):
        return self.frappe.get_meta(doctype)

    def list_records(self, doctype, *, filters, limit, or_filters=None, order_by="name asc"):
        return self.frappe.get_list(
            doctype,
            fields=["*"],
            filters=filters,
            or_filters=or_filters,
            order_by=order_by,
            limit_page_length=limit,
            ignore_permissions=False,
        )

    def can_read_type(self, doctype):
        return self.frappe.has_permission(doctype, "read")

    def can_read_document(self, doctype, name):
        key = (doctype, name)
        if key not in self.document_permissions:
            try:
                doc = self.frappe.get_doc(doctype, name)
                self.document_permissions[key] = self.frappe.has_permission(
                    doctype, "read", doc=doc
                )
            except (self.frappe.DoesNotExistError, self.frappe.PermissionError):
                self.document_permissions[key] = False
        return self.document_permissions[key]


class Frappe16Gateway(Frappe15Gateway):
    def list_records(self, doctype, *, filters, limit, or_filters=None, order_by="name asc"):
        return self.frappe.get_list(
            doctype,
            fields=["*"],
            filters=filters,
            or_filters=or_filters,
            order_by=order_by,
            limit=limit,
            ignore_permissions=False,
        )


def get_gateway():
    import erpnext
    import frappe

    majors = (frappe.__version__.split(".")[0], erpnext.__version__.split(".")[0])
    if majors[0] != majors[1] or majors[0] not in ("15", "16"):
        raise ScopeError("Reckon Accounts requires matching Frappe/ERPNext major versions 15 or 16")
    return (Frappe15Gateway if majors[0] == "15" else Frappe16Gateway)(frappe)


def authorize_report(frappe, report_name, *, export=False):
    from frappe.desk.query_report import get_report_doc

    from reckon_accounts.accounting.service import REPORTS

    if report_name not in REPORTS or frappe.session.user == "Guest":
        frappe.throw("Report access denied", frappe.PermissionError)
    get_report_doc(report_name)
    frappe.has_permission("GL Entry", "read", throw=True)
    if export:
        frappe.has_permission("GL Entry", "export", throw=True)


def _required(record, fields):
    if not set(fields).issubset(record):
        raise ScopeError("Required accounting fields are unavailable or not readable")


def finance_books(filters, company_default):
    if (
        filters.include_default_book_entries
        and filters.finance_book
        and company_default
        and filters.finance_book != company_default
    ):
        raise ScopeError("Uncheck Include Default Book Entries to select a different Finance Book")
    selected = filters.finance_book or (
        company_default if filters.include_default_book_entries else None
    )
    return {None, "", selected}


class LedgerAdapter:
    def __init__(self, gateway):
        self.gateway = gateway
        self.frappe = gateway.frappe
        self.permissions = PermissionScope(gateway)

    def run(self, report_name, raw_filters, *, full=False, export=False, voucher_keys=None):
        authorize_report(self.frappe, report_name, export=export)
        filters = parse_ledger_filters(raw_filters)
        if full:
            filters = replace(filters, page=1)
        if voucher_keys is None:
            validate_report_scope(report_name, filters)
        gl_meta = self.gateway.meta("GL Entry")
        if any(not gl_meta.has_field(field) for field in REQUIRED_GL):
            raise ScopeError("Installed GL Entry schema is incompatible with Phase 1")
        company = self.permissions.require("Company", filters.company)
        _required(company, ("default_currency", "default_finance_book"))
        if not company["default_currency"]:
            raise ScopeError("Company currency is not configured")
        books = finance_books(filters, company.get("default_finance_book"))
        for book in books - {None, ""}:
            self.permissions.require("Finance Book", book)
        if filters.fiscal_year:
            year = self.permissions.require("Fiscal Year", filters.fiscal_year)
            _required(year, ("year_start_date", "year_end_date"))
            if not (
                _as_date(year["year_start_date"])
                <= filters.from_date
                <= filters.to_date
                <= _as_date(year["year_end_date"])
            ):
                raise ScopeError("Explicit dates conflict with the selected Fiscal Year")
            year_doc = self.frappe.get_doc("Fiscal Year", filters.fiscal_year)
            companies = {row.company for row in year_doc.get("companies", [])}
            if companies and filters.company not in companies:
                raise ScopeError("Fiscal Year does not apply to the selected company")

        # Configuration metadata only, never accounting amounts or party names.
        definitions = self.frappe.get_all(
            "Accounting Dimension",
            fields=["fieldname", "document_type", "disabled"],
            limit_page_length=101,
        )
        if len(definitions) > 100:
            raise ScopeError("Too many accounting dimensions for this report version")
        dimensions = dimension_contract(gl_meta, definitions)
        active = {"cost_center", "project"} | {
            row["fieldname"] for row in definitions if not row.get("disabled")
        }
        selections = {}
        for fieldname, values in filters.dimensions:
            if fieldname not in dimensions or fieldname not in active:
                raise ScopeError("Unknown or disabled accounting dimension")
            selections[fieldname] = expand_selection(
                self.gateway,
                self.permissions,
                dimensions[fieldname],
                values,
                filters.company,
            )

        conditions = [["company", "=", filters.company], ["is_cancelled", "=", 0]]
        if voucher_keys is not None:
            if not voucher_keys:
                raise ScopeError("Voucher expansion requires selected identities")
            conditions.append(["voucher_no", "in", sorted({name for _, name in voucher_keys})])
        currency = company["default_currency"]
        if filters.account:
            account = self.permissions.require("Account", filters.account)
            _required(account, ("company", "is_group", "account_currency"))
            if account["company"] != filters.company:
                raise ScopeError("Account belongs to another company")
            accounts = expand_selection(
                self.gateway, self.permissions, "Account", [filters.account], filters.company
            )
            conditions.append(["account", "in", sorted(accounts)])
            if filters.currency_mode == "account":
                if account["is_group"] or not account["account_currency"]:
                    raise ScopeError(
                        "Account currency requires one non-group account with a currency"
                    )
                currency = account["account_currency"]
        if filters.party_type and filters.party_type != "Other":
            self.permissions.require("Party Type", filters.party_type)
            if not self.gateway.can_read_type(filters.party_type):
                raise ScopeError("Party type is unavailable or not permitted")
            conditions.append(["party_type", "=", filters.party_type])
        if filters.party:
            selected_party = self.permissions.require(filters.party_type, filters.party)
            if selected_party.get("company") not in (None, "", filters.company):
                raise ScopeError("Party belongs to another company")
            conditions.append(["party", "=", filters.party])
        for key in ("voucher_type", "voucher_no"):
            if getattr(filters, key):
                conditions.append([key, "=", getattr(filters, key)])
        if filters.voucher_type and not self.gateway.can_read_type(filters.voucher_type):
            raise ScopeError("Voucher type is unavailable or not permitted")
        if filters.voucher_no:
            self.permissions.require(filters.voucher_type, filters.voucher_no)
        if filters.payment_type:
            conditions.append(["voucher_type", "=", "Payment Entry"])

        settings_meta = self.gateway.meta("Accounts Settings")
        if not settings_meta.has_field("ignore_is_opening_check_for_reporting"):
            raise ScopeError("Installed opening-entry setting is unavailable")
        ignore_opening = bool(
            self.frappe.db.get_single_value(
                "Accounts Settings", "ignore_is_opening_check_for_reporting"
            )
        )
        date_conditions = [["posting_date", "<=", filters.to_date]]
        if not ignore_opening:
            date_conditions.append(["is_opening", "=", "Yes"])
        candidates = self.gateway.list_records(
            "GL Entry",
            filters=conditions,
            or_filters=date_conditions,
            limit=MAX_GL_ROWS + 1,
            order_by="posting_date asc, creation asc, name asc",
        )
        if len(candidates) > MAX_GL_ROWS:
            raise ScopeError(
                "Ledger exceeds 5,000 candidate GL rows; narrow account or party scope"
            )
        scoped = []
        for row in candidates:
            _required(row, REQUIRED_GL | set(dimensions) | {"name", "creation"})
            if row["company"] != filters.company or row["is_cancelled"]:
                raise ScopeError("Unexpected GL rows returned by the adapter")
            if (
                voucher_keys is not None
                and (row["voucher_type"], row["voucher_no"]) not in voucher_keys
            ):
                continue
            if voucher_keys is None and row.get("finance_book") not in books:
                continue
            if filters.only_entries_without_party and row.get("party"):
                continue
            if any((row.get(field) or None) not in values for field, values in selections.items()):
                continue
            scoped.append(row)

        # Batch master and source visibility, then run custom document checks.
        references = defaultdict(set)
        for row in scoped:
            references["Account"].add(row["account"])
            if row.get("party"):
                references[row["party_type"]].add(row["party"])
            references[row["voucher_type"]].add(row["voucher_no"])
            for fieldname, doctype in dimensions.items():
                if row.get(fieldname):
                    references[doctype].add(row[fieldname])
            if row.get("finance_book"):
                references["Finance Book"].add(row["finance_book"])
        for doctype, names in references.items():
            if not doctype:
                raise ScopeError("GL source or party identity is missing")
            self.permissions.load(doctype, names)
        permitted = []
        for row in scoped:
            if not self.permissions.row_allowed(row, dimensions):
                continue
            from reckon_accounts.accounting.catalog import (
                ACCOUNT_TYPES,
                BOOK_REPORTS,
                SOURCE_LABELS,
            )

            kind = BOOK_REPORTS.get(report_name)
            account_record = self.permissions.require("Account", row["account"])
            if kind == "exceptions":
                _required(account_record, ("root_type",))
            if kind in ACCOUNT_TYPES:
                _required(account_record, ("account_type",))
                if account_record["account_type"] not in ACCOUNT_TYPES[kind]:
                    continue
            source = self.permissions.get(row["voucher_type"], row["voucher_no"])
            if kind in SOURCE_LABELS:
                if row["voucher_type"] == "Journal Entry":
                    _required(source, ("voucher_type",))
                if row["voucher_type"] == "Payment Entry":
                    _required(source, ("payment_type",))
                if row["voucher_type"] in ("Sales Invoice", "Purchase Invoice"):
                    _required(source, ("is_return",))
                if voucher_label(row["voucher_type"], source) not in SOURCE_LABELS[kind]:
                    continue
            if source.get("company") not in (None, "", filters.company):
                raise ScopeError("GL source company does not match")
            if filters.payment_type:
                _required(source, ("payment_type",))
                if source["payment_type"] != filters.payment_type:
                    continue
            if filters.currency_mode == "account" and row["account_currency"] != currency:
                raise ScopeError("GL account currencies are inconsistent")
            permitted.append(row)

        account_titles = {
            name: str(record.get("account_name") or name)
            for (doctype, name), record in self.permissions.cache.items()
            if doctype == "Account" and record is not None
        }
        peers = defaultdict(list)
        for row in permitted:
            peers[(row["voucher_type"], row["voucher_no"])].append(row)
        postings = []
        for row in permitted:
            source = self.permissions.get(row["voucher_type"], row["voucher_no"])
            party = (
                self.permissions.get(row["party_type"], row["party"]) if row.get("party") else None
            )
            debit_field = (
                "debit_in_account_currency" if filters.currency_mode == "account" else "debit"
            )
            credit_field = (
                "credit_in_account_currency" if filters.currency_mode == "account" else "credit"
            )
            postings.append(
                Posting(
                    name=row["name"],
                    posting_date=_as_date(row["posting_date"]),
                    creation=_as_datetime(row["creation"]),
                    account=row["account"],
                    account_name=account_titles[row["account"]],
                    debit=row[debit_field],
                    credit=row[credit_field],
                    party_type=row.get("party_type") or "",
                    party=row.get("party") or "",
                    party_name=party_name(party, self.gateway.meta(row["party_type"]))
                    if party
                    else "",
                    voucher_type=row["voucher_type"],
                    voucher_no=row["voucher_no"],
                    voucher_label=voucher_label(row["voucher_type"], source),
                    remarks=str(row.get("remarks") or ""),
                    particulars=permitted_particulars(
                        row, peers[(row["voucher_type"], row["voucher_no"])], account_titles
                    ),
                    is_opening=row["is_opening"] == "Yes",
                    account_root_type=self.permissions.require("Account", row["account"]).get(
                        "root_type"
                    )
                    or "",
                )
            )
        from frappe.model.meta import get_field_precision
        from frappe.utils import flt, now_datetime

        precision = get_field_precision(
            gl_meta.get_field(
                "debit_in_account_currency" if filters.currency_mode == "account" else "debit"
            ),
            currency=currency,
        )
        # Group Vouchers expansion has no account filter: validation occurred in
        # the selecting request. Keep the selected group only for the service contract.
        if voucher_keys is not None and report_name == "Group Vouchers":
            filters = replace(filters, account="Selected voucher scope")
        result = build_ledger(
            report_name,
            filters,
            postings,
            currency=currency,
            precision=precision,
            round_amount=lambda amount: Decimal(str(flt(amount, precision))),
            generated_at=str(now_datetime()),
            ignore_opening_check=ignore_opening,
        )
        return replace(result, account_titles=tuple(sorted(account_titles.items())))


def _as_date(value):
    return value if type(value) is date else date.fromisoformat(str(value))


def _as_datetime(value):
    return value if type(value) is datetime else datetime.fromisoformat(str(value))
