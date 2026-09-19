"""Roles and additive permissions owned by Reckon Accounts."""

import frappe

APP_ROLES = ("Reckon Accounts User", "Reckon Accounts Manager")

TRANSACTION_DOCTYPES = (
    "Journal Entry",
    "Payment Entry",
    "Sales Invoice",
    "Purchase Invoice",
    "Dunning",
    "Bank Transaction",
    "Payment Reconciliation",
)
MASTER_DOCTYPES = (
    "Company",
    "Account",
    "Customer",
    "Supplier",
    "Bank",
    "Bank Account",
    "Cost Center",
    "Project",
)
SETUP_DOCTYPES = (
    "Accounts Settings",
    "Fiscal Year",
    "Finance Book",
    "Accounting Dimension",
    "Mode of Payment",
    "Payment Terms Template",
    "Budget",
)
REPORT_DOCTYPES = ("GL Entry",)
NAVIGATION_DOCTYPES = ("Page", "Report", "Workspace", "Workspace Sidebar")
STANDARD_REPORTS = (
    "General Ledger",
    "Trial Balance",
    "Balance Sheet",
    "Profit and Loss Statement",
    "Cash Flow",
    "Financial Ratios",
    "Trial Balance for Party",
    "Item-wise Sales Register",
    "Item-wise Purchase Register",
    "Sales Register",
    "Purchase Register",
    "Accounts Receivable",
    "Accounts Payable",
    "Bank Reconciliation Statement",
)

READ_PERMISSIONS = {
    "read": 1,
    "select": 1,
    "report": 1,
    "export": 1,
    "print": 1,
    "email": 1,
}
ENTRY_PERMISSIONS = {**READ_PERMISSIONS, "create": 1, "write": 1, "submit": 1}
MANAGER_PERMISSIONS = {
    **ENTRY_PERMISSIONS,
    "cancel": 1,
    "amend": 1,
    "delete": 1,
    "import": 1,
    "share": 1,
}
PERMISSION_FIELDS = tuple(MANAGER_PERMISSIONS)


def setup_roles_and_permissions():
    """Create or refresh app roles and their ERPNext Custom DocPerm rows."""
    for role in APP_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()

    for doctype in NAVIGATION_DOCTYPES + REPORT_DOCTYPES + MASTER_DOCTYPES + SETUP_DOCTYPES:
        _upsert_permission(doctype, APP_ROLES[0], READ_PERMISSIONS)
    for doctype in TRANSACTION_DOCTYPES:
        _upsert_permission(doctype, APP_ROLES[0], ENTRY_PERMISSIONS)

    for doctype in NAVIGATION_DOCTYPES:
        _upsert_permission(doctype, APP_ROLES[1], READ_PERMISSIONS)
    for doctype in REPORT_DOCTYPES + TRANSACTION_DOCTYPES + MASTER_DOCTYPES + SETUP_DOCTYPES:
        _upsert_permission(doctype, APP_ROLES[1], MANAGER_PERMISSIONS)

    for report in STANDARD_REPORTS:
        _ensure_role_links("Report", report)
    for report in frappe.get_all("Report", filters={"module": "Reckon Accounts"}, pluck="name"):
        _ensure_role_links("Report", report)
    _ensure_role_links("Page", "voucher-entry")
    _ensure_role_links("Workspace", "Reckon Accounts")
    _ensure_role_links("Workspace", "Accounting")

    frappe.clear_cache()


def _upsert_permission(doctype, role, permissions):
    if not frappe.db.exists("DocType", doctype):
        return
    filters = {"parent": doctype, "role": role, "permlevel": 0}
    name = frappe.db.exists("Custom DocPerm", filters)
    values = {
        **filters,
        **dict.fromkeys(PERMISSION_FIELDS, 0),
        **permissions,
    }
    if name:
        frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
    else:
        frappe.get_doc({"doctype": "Custom DocPerm", **values}).insert()


def _ensure_role_links(parenttype, parent):
    if not frappe.db.exists(parenttype, parent):
        return
    for role in APP_ROLES:
        filters = {
            "parenttype": parenttype,
            "parent": parent,
            "parentfield": "roles",
            "role": role,
        }
        if not frappe.db.exists("Has Role", filters):
            frappe.get_doc({"doctype": "Has Role", **filters}).insert()
