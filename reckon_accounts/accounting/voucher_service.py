"""Backward-compatible API helpers for direct Payment Entry vouchers."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

import frappe


def _(value):
    return getattr(frappe, "_", lambda text: text)(value)


CASH_BANK_TYPES = {"Cash", "Bank"}


def create_direct_expense(values):
    """Create a direct expense as a standard Payment Entry with type Pay."""
    data = _coerce(values)
    company = _required(data, "company")
    amount = _positive_amount(data.get("amount"))
    cash_bank = _validate_cash_bank_account(data.get("paid_from"), company, "Paid From")
    expense = _validate_profit_loss_account(
        data.get("expense_account"), company, "Expense", "Expense Account"
    )
    _validate_distinct(cash_bank.name, expense.name)
    dimensions = _validated_dimensions(data, company)
    remark = _voucher_remark("Direct Expense Payment", data, "paid_to")
    doc = _payment_entry(
        company=company,
        posting_date=_required(data, "posting_date"),
        payment_type="Pay",
        custom_voucher_subtype="Direct Expense",
        paid_from=cash_bank.name,
        paid_to=expense.name,
        paid_amount=amount,
        received_amount=amount,
        mode_of_payment=_required(data, "mode_of_payment"),
        reference_no=data.get("reference_number"),
        reference_date=data.get("reference_date"),
        cost_center=dimensions.pop("cost_center", None),
        project=dimensions.pop("project", None),
        custom_remarks=1,
        remarks=remark,
        **dimensions,
    )
    return _submit_and_response(doc, "Payment Entry Created Successfully")


def create_direct_income(values):
    """Create a direct income as a standard Payment Entry with type Receive."""
    data = _coerce(values)
    company = _required(data, "company")
    amount = _positive_amount(data.get("amount"))
    cash_bank = _validate_cash_bank_account(data.get("received_to"), company, "Received To")
    income = _validate_profit_loss_account(
        data.get("income_account"), company, "Income", "Income Account"
    )
    _validate_distinct(cash_bank.name, income.name)
    dimensions = _validated_dimensions(data, company)
    remark = _voucher_remark("Direct Income Receipt", data, "received_from")
    doc = _payment_entry(
        company=company,
        posting_date=_required(data, "posting_date"),
        payment_type="Receive",
        custom_voucher_subtype="Direct Income",
        paid_from=income.name,
        paid_to=cash_bank.name,
        paid_amount=amount,
        received_amount=amount,
        mode_of_payment=_required(data, "mode_of_payment"),
        reference_no=data.get("reference_number"),
        reference_date=data.get("reference_date"),
        cost_center=dimensions.pop("cost_center", None),
        project=dimensions.pop("project", None),
        custom_remarks=1,
        remarks=remark,
        **dimensions,
    )
    return _submit_and_response(doc, "Payment Entry Created Successfully")


def get_default_payment_account(company, mode_of_payment):
    """Return the ERPNext Mode of Payment account configured for this company."""
    if not company or not mode_of_payment:
        return None
    frappe.has_permission("Mode of Payment", "read", mode_of_payment, throw=True)
    account = frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": mode_of_payment, "company": company},
        "default_account",
    )
    if account:
        _validate_cash_bank_account(account, company, "Default Account")
    return account


def get_accounting_dimensions():
    """Return enabled accounting dimensions for compatibility with older clients."""
    rows = frappe.get_all(
        "Accounting Dimension",
        filters={"disabled": 0},
        fields=["fieldname", "label", "document_type"],
        limit_page_length=100,
    )
    return [
        {
            "fieldname": row.fieldname,
            "label": row.get("label") or row.fieldname.replace("_", " ").title(),
            "doctype": row.document_type,
        }
        for row in rows
        if row.fieldname not in {"cost_center", "project"}
    ]


def _payment_entry(**values):
    frappe.has_permission("Payment Entry", "create", throw=True)
    return frappe.get_doc({"doctype": "Payment Entry", **values})


def _coerce(values):
    if isinstance(values, str):
        values = json.loads(values)
    if not isinstance(values, dict):
        frappe.throw(_("Voucher data is required"))
    return values


def _required(data, fieldname):
    value = data.get(fieldname)
    if value in (None, ""):
        frappe.throw(_("{0} is required").format(_label(fieldname)))
    return value


def _positive_amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError):
        frappe.throw(_("Amount must be a positive number"))
    if amount <= 0:
        frappe.throw(_("Amount must be greater than zero"))
    return float(amount)


def _validate_cash_bank_account(account, company, label):
    account = _account(account, label)
    if account.company != company:
        frappe.throw(_("{0} must belong to the selected company").format(_(label)))
    if account.is_group:
        frappe.throw(_("{0} cannot be a group account").format(_(label)))
    if account.account_type not in CASH_BANK_TYPES:
        frappe.throw(_("{0} must be a Cash or Bank account").format(_(label)))
    return account


def _validate_profit_loss_account(account, company, root_type, label):
    account = _account(account, label)
    if account.company != company:
        frappe.throw(_("{0} must belong to the selected company").format(_(label)))
    if account.is_group:
        frappe.throw(_("{0} cannot be a group account").format(_(label)))
    if account.root_type != root_type:
        frappe.throw(_("{0} must be an {1} account").format(_(label), _(root_type)))
    return account


def _account(name, label):
    name = _required({label: name}, label)
    frappe.has_permission("Account", "read", name, throw=True)
    return frappe.get_cached_doc("Account", name)


def _validate_distinct(first, second):
    if first == second:
        frappe.throw(_("Payment Entry accounts must be different"))


def _validated_dimensions(data, company):
    result = {}
    for fieldname, doctype in _dimension_fields().items():
        value = data.get(fieldname)
        if not value:
            continue
        frappe.has_permission(doctype, "read", value, throw=True)
        if frappe.get_meta(doctype).has_field("company"):
            item_company = frappe.db.get_value(doctype, value, "company")
            if item_company and item_company != company:
                frappe.throw(_("{0} must belong to the selected company").format(_label(fieldname)))
        result[fieldname] = value
    return result


def _dimension_fields():
    fields = {"cost_center": "Cost Center", "project": "Project"}
    for row in get_accounting_dimensions():
        fields[row["fieldname"]] = row["doctype"]
    return fields


def _submit_and_response(doc, message):
    doc.insert()
    doc.submit()
    accounts = [
        {"account": doc.paid_to, "debit": doc.received_amount, "credit": 0},
        {"account": doc.paid_from, "debit": 0, "credit": doc.paid_amount},
    ]
    return {
        "message": message,
        "doctype": doc.doctype,
        "name": doc.name,
        "voucher_number": doc.name,
        "posting_date": doc.posting_date,
        "accounts": accounts,
    }


def _voucher_remark(title, data, counterparty_field):
    parts = [title]
    if data.get(counterparty_field):
        parts.append(f"{_label(counterparty_field)}: {data[counterparty_field]}")
    if data.get("reference_number"):
        parts.append(f"Reference: {data['reference_number']}")
    if data.get("remarks"):
        parts.append(str(data["remarks"]))
    return "\n".join(parts)


def _label(fieldname):
    return str(fieldname).replace("_", " ").title()
