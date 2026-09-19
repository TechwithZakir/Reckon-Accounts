"""Remove obsolete generated child workspaces; the v16 sidebar replaces them."""

import frappe

OLD_WORKSPACES = (
    "Reckon Accounts Voucher Entry",
    "Reckon Accounts Ledgers",
    "Reckon Accounts Cash and Bank",
    "Reckon Accounts Groups and Analysis",
    "Reckon Accounts Voucher Registers",
    "Reckon Accounts Financial Statements",
    "Reckon Accounts Outstanding and Reconciliation",
    "Reckon Accounts ERPNext",
    "Reckon Accounts Transactions",
    "Reckon Accounts Masters",
    "Reckon Accounts Accounting Setup",
)


def execute():
    for name in OLD_WORKSPACES:
        module = frappe.db.get_value("Workspace", name, "module")
        if module == "Reckon Accounts":
            frappe.delete_doc("Workspace", name, force=True, ignore_permissions=True)
