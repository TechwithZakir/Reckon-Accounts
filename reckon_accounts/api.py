"""Permission-checked report export, metadata and selection entry points."""

import json
from collections.abc import Mapping

import frappe

from reckon_accounts.accounting.adapters import LedgerAdapter, authorize_report, get_gateway
from reckon_accounts.accounting.dimensions import dimension_contract
from reckon_accounts.accounting.permissions import PermissionScope
from reckon_accounts.accounting.reporting import export_csv


def check_app_permission():
    """Show the desktop app only to signed-in users who can read accounting entries."""
    if frappe.session.user == "Guest":
        return False
    roles = set(frappe.get_roles())
    return bool(roles.intersection({"Reckon Accounts User", "Reckon Accounts Manager"})) or (
        frappe.has_permission("GL Entry", "read")
    )


def normalize_report_filters(values):
    """Translate Frappe control serialization into the strict internal contract."""
    if isinstance(values, str):
        values = json.loads(values)
    if not isinstance(values, Mapping):
        raise ValueError("Report filters must be an object")
    result = dict(values)
    links = {
        "account",
        "party_type",
        "party",
        "voucher_type",
        "voucher_no",
        "payment_type",
        "mode_of_payment",
        "reference_no",
        "fiscal_year",
        "finance_book",
        "customer_group",
        "supplier_group",
        "territory",
        "group_by",
        "current_assets_group",
        "current_liabilities_group",
    }
    for key in links:
        if result.get(key) == "":
            result[key] = None
    for key in (
        "only_entries_without_party",
        "include_default_book_entries",
        "show_opening_entries",
    ):
        if key in result and type(result[key]) is int and result[key] in (0, 1):
            result[key] = bool(result[key])
    if result.get("dimensions") == "":
        result["dimensions"] = {}
    elif isinstance(result.get("dimensions"), str):
        result["dimensions"] = json.loads(result["dimensions"])
    return result


@frappe.whitelist()
def export_ledger(report_name, filters):
    """Export only after both report and GL export permission checks."""
    try:
        from reckon_accounts.accounting.books import book_csv, run_book
        from reckon_accounts.accounting.catalog import BOOK_REPORTS

        if report_name in BOOK_REPORTS:
            result = run_book(
                LedgerAdapter(get_gateway()),
                report_name,
                normalize_report_filters(filters),
                full=True,
                export=True,
            )
            content = book_csv(result)
        else:
            result = LedgerAdapter(get_gateway()).run(
                report_name,
                normalize_report_filters(filters),
                full=True,
                export=True,
            )
            content = export_csv(result)
    except ValueError as exc:
        frappe.throw(str(exc))
    frappe.local.response.update(
        {
            "type": "download",
            "filename": report_name.replace(" ", "_") + "_full.csv",
            "filecontent": content.encode("utf-8"),
            "display_content_as": "attachment",
        }
    )


def _metadata(gateway):
    definitions = frappe.get_all(
        "Accounting Dimension",
        fields=["fieldname", "document_type", "disabled"],
        limit_page_length=101,
    )
    if len(definitions) > 100:
        raise ValueError("Too many accounting dimensions")
    contract = dimension_contract(gateway.meta("GL Entry"), definitions)
    disabled = {item["fieldname"] for item in definitions if item.get("disabled")}
    return {key: value for key, value in contract.items() if key not in disabled}


@frappe.whitelist()
def filter_options(report_name):
    authorize_report(frappe, report_name)
    gateway = get_gateway()
    permissions = PermissionScope(gateway)
    records = (
        gateway.list_records("Party Type", filters={}, limit=101)
        if gateway.can_read_type("Party Type")
        else []
    )
    if len(records) > 100:
        frappe.throw("Too many configured party types")
    permissions.load("Party Type", [record["name"] for record in records])
    types = [
        record["name"]
        for record in records
        if permissions.get("Party Type", record["name"]) and gateway.can_read_type(record["name"])
    ]
    dimensions = [
        {"fieldname": key, "doctype": value, "label": gateway.meta("GL Entry").get_field(key).label}
        for key, value in _metadata(gateway).items()
        if gateway.can_read_type(value)
    ]
    return {"party_types": sorted(types) + ["Other"], "dimensions": dimensions}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_records(doctype, txt, searchfield, start, page_len, filters):
    """Use the same list/document intersection as totals for name searches."""
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not isinstance(filters, Mapping):
        frappe.throw("Search scope is required")
    authorize_report(frappe, filters.get("report_name"))
    gateway = get_gateway()
    permissions = PermissionScope(gateway)
    fieldname = filters.get("scope_field")
    allowed = {
        "company": "Company",
        "account": "Account",
        "fiscal_year": "Fiscal Year",
        "finance_book": "Finance Book",
        "voucher_type": "DocType",
        "mode_of_payment": "Mode of Payment",
    } | _metadata(gateway)
    party_type = filters.get("party_type")
    if fieldname == "party":
        permissions.require("Party Type", party_type)
        allowed["party"] = party_type
    if fieldname == "voucher_no":
        source_type = filters.get("voucher_type")
        if not source_type or not gateway.can_read_type(source_type):
            frappe.throw("Select a permitted source type")
        allowed["voucher_no"] = source_type
    if filters.get("report_name") == "Party Summary":
        allowed.update(
            customer_group="Customer Group", supplier_group="Supplier Group", territory="Territory"
        )
    if filters.get("report_name") == "Funds Flow":
        allowed.update(current_assets_group="Account", current_liabilities_group="Account")
    if allowed.get(fieldname) != doctype:
        frappe.throw("Unsupported selection scope", frappe.PermissionError)
    if not 0 <= int(start) <= 1000 or not 1 <= int(page_len) <= 50:
        frappe.throw("Invalid search page")
    query = []
    company = filters.get("company")
    if company:
        permissions.require("Company", company)
        if gateway.meta(doctype).has_field("company"):
            query.append(["company", "=", company])
    if fieldname == "voucher_type":
        query.append(["is_submittable", "=", 1])
    # Do not interpolate a user-supplied search field into a query.
    title = gateway.meta(doctype).title_field
    matches = [["name", "like", "%" + txt + "%"]]
    if title and gateway.meta(doctype).has_field(title):
        matches.append([title, "like", "%" + txt + "%"])
    records = gateway.list_records(
        doctype, filters=query, or_filters=matches, limit=int(start) + int(page_len) + 100
    )
    permissions.load(doctype, [record["name"] for record in records])
    permitted = [permissions.get(doctype, record["name"]) for record in records]
    permitted = [record for record in permitted if record is not None]
    if fieldname == "voucher_type":
        permitted = [record for record in permitted if gateway.can_read_type(record["name"])]
    return [
        [record["name"], record.get(title) or record["name"]]
        for record in permitted[int(start) : int(start) + int(page_len)]
    ]
