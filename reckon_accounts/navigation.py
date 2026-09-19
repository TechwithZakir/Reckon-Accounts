"""Shared native navigation definitions for Frappe 15 and 16."""

import json

GROUPS = (
    ("Voucher Entry", "Page", ("voucher-entry",)),
    (
        "Ledgers",
        "Report",
        (
            "Party Ledger",
            "Account Ledger",
            "Account Head Wise Party Ledger",
            "Party Summary",
            "General Ledger Custom",
            "Ledger Monthly Summary",
        ),
    ),
    (
        "Cash and Bank",
        "Report",
        ("Cash Book", "Bank Book", "Cash Bank Summary", "Bank Summary", "Receipts and Payments"),
    ),
    (
        "Groups and Analysis",
        "Report",
        (
            "Group Summary",
            "Group Monthly Summary",
            "Group Vouchers",
            "Funds Flow",
            "Negative Cash",
            "Ledger Exceptions",
        ),
    ),
    (
        "Voucher Registers",
        "Report",
        (
            "Day Book",
            "Receipt Register",
            "Payment Register",
            "Contra Register",
            "Journal Register",
            "Debit Note Register",
            "Credit Note Register",
            "Voucher Statistics",
        ),
    ),
    (
        "Financial Statements",
        "Report",
        (
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
        ),
    ),
    (
        "Outstanding and Reconciliation",
        "Report",
        ("Accounts Receivable", "Accounts Payable", "Bank Reconciliation Statement"),
    ),
    ("ERPNext", "Workspace", ("Accounting",)),
    (
        "Transactions",
        "DocType",
        (
            "Journal Entry",
            "Payment Entry",
            "Sales Invoice",
            "Purchase Invoice",
            "Dunning",
            "Bank Transaction",
            "Payment Reconciliation",
        ),
    ),
    (
        "Masters",
        "DocType",
        (
            "Company",
            "Account",
            "Customer",
            "Supplier",
            "Bank",
            "Bank Account",
            "Cost Center",
            "Project",
        ),
    ),
    (
        "Accounting Setup",
        "DocType",
        (
            "Accounts Settings",
            "Fiscal Year",
            "Finance Book",
            "Accounting Dimension",
            "Mode of Payment",
            "Payment Terms Template",
            "Budget",
        ),
    ),
)


def workspace_documents():
    """One app workspace; Frappe 16 navigation lives in Workspace Sidebar."""

    def document(name, groups, sequence, parent=None):
        links, content = [], []
        for index, (label, link_type, names) in enumerate(groups):
            links.append({"type": "Card Break", "label": label})
            links.extend(
                {
                    "type": "Link",
                    "label": _label(name),
                    "link_type": link_type,
                    "link_to": name,
                    "is_query_report": int(link_type == "Report"),
                }
                for name in names
            )
            content.append(
                {"id": f"card-{index}", "type": "card", "data": {"card_name": label, "col": 4}}
            )
        return {
            "doctype": "Workspace",
            "name": name,
            "label": _label(name),
            "title": name,
            "module": "Reckon Accounts",
            "public": 1,
            "is_hidden": 0,
            "icon": "accounting",
            "sequence_id": sequence,
            "parent_page": parent or "",
            "content": json.dumps(content),
            "links": links,
            "roles": [
                {"role": role}
                for role in (
                    "Accounts User",
                    "Accounts Manager",
                    "Reckon Accounts User",
                    "Reckon Accounts Manager",
                    "System Manager",
                    "Auditor",
                )
            ],
            "charts": [],
            "custom_blocks": [],
            "number_cards": [],
            "shortcuts": [],
            "quick_lists": [],
        }

    yield document("Reckon Accounts", GROUPS, 20)


def sidebar_document():
    """App-level sidebar files are synced natively by v16 and ignored by v15."""
    items = [
        {
            "type": "Link",
            "label": "Home",
            "link_type": "Workspace",
            "link_to": "Reckon Accounts",
            "child": 0,
            "icon": "house",
        }
    ]
    for label, link_type, names in GROUPS:
        items.append(
            {
                "type": "Section Break",
                "label": label,
                "child": 0,
                "collapsible": 1,
                "keep_closed": 0,
                "indent": 1,
            }
        )
        items.extend(
            {
                "type": "Link",
                "label": _label(name),
                "link_type": link_type,
                "link_to": name,
                "child": 1,
            }
            for name in names
        )
    return {
        "doctype": "Workspace Sidebar",
        "name": "Reckon Accounts",
        "title": "Reckon Accounts",
        "app": "reckon_accounts",
        "module": "Reckon Accounts",
        "standard": 1,
        "header_icon": "accounting",
        "items": items,
    }


def _label(name):
    return {
        "voucher-entry": "Voucher Entry",
        "Accounting": "Financial Reports (ERPNext)",
    }.get(name, name)
