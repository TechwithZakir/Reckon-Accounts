"""Tally-style direct voucher creation using standard ERPNext documents."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

import frappe


def _(value):
    return getattr(frappe, "_", lambda text: text)(value)


CASH_BANK_TYPES = {"Cash", "Bank"}
DIRECT_PAYMENT_SERIES = "PV-.YYYY.-"
DIRECT_RECEIPT_SERIES = "RV-.YYYY.-"


def create_direct_expense(values):
    """Create a submitted Journal Entry for a non-party Payment Voucher."""
    data = _coerce(values)
    company = _required(data, "company")
    amount = _positive_amount(data.get("amount"))
    cash_bank = _validate_cash_bank_account(data.get("paid_from"), company, "Paid From")
    expense = _validate_profit_loss_account(
        data.get("expense_account"), company, "Expense", "Expense Account"
    )
    _validate_distinct(cash_bank.name, expense.name)
    dimensions = _validated_dimensions(data, company)
    remark = _voucher_remark("Direct Expense via Reckon Payment Voucher", data, "paid_to")
    doc = _journal_entry(
        company=company,
        posting_date=_required(data, "posting_date"),
        naming_series=DIRECT_PAYMENT_SERIES,
        mode_of_payment=data.get("mode_of_payment"),
        cheque_no=data.get("reference_number"),
        cheque_date=data.get("reference_date"),
        pay_to_recd_from=data.get("paid_to"),
        remark=remark,
        user_remark=remark,
        accounts=[
            {"account": expense.name, "debit_in_account_currency": amount, **dimensions},
            {"account": cash_bank.name, "credit_in_account_currency": amount, **dimensions},
        ],
    )
    return _submit_and_response(doc, "Payment Voucher Created Successfully")


def create_direct_income(values):
    """Create a submitted Journal Entry for a non-party Receipt Voucher."""
    data = _coerce(values)
    company = _required(data, "company")
    amount = _positive_amount(data.get("amount"))
    cash_bank = _validate_cash_bank_account(data.get("received_to"), company, "Received To")
    income = _validate_profit_loss_account(data.get("income_account"), company, "Income", "Income Account")
    _validate_distinct(cash_bank.name, income.name)
    dimensions = _validated_dimensions(data, company)
    remark = _voucher_remark("Direct Income via Reckon Receipt Voucher", data, "received_from")
    doc = _journal_entry(
        company=company,
        posting_date=_required(data, "posting_date"),
        naming_series=DIRECT_RECEIPT_SERIES,
        mode_of_payment=data.get("mode_of_payment"),
        cheque_no=data.get("reference_number"),
        cheque_date=data.get("reference_date"),
        pay_to_recd_from=data.get("received_from"),
        remark=remark,
        user_remark=remark,
        accounts=[
            {"account": cash_bank.name, "debit_in_account_currency": amount, **dimensions},
            {"account": income.name, "credit_in_account_currency": amount, **dimensions},
        ],
    )
    return _submit_and_response(doc, "Receipt Voucher Created Successfully")


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
    """Expose enabled accounting dimensions for the voucher pages."""
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
        frappe.throw(_("Debit and credit accounts must be different"))


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


def _journal_entry(**values):
    frappe.has_permission("Journal Entry", "create", throw=True)
    return frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Journal Entry", **values})


def _submit_and_response(doc, message):
    doc.insert()
    doc.submit()
    return {
        "message": message,
        "doctype": doc.doctype,
        "name": doc.name,
        "voucher_number": doc.name,
        "posting_date": doc.posting_date,
        "accounts": [
            {
                "account": row.account,
                "debit": row.debit_in_account_currency,
                "credit": row.credit_in_account_currency,
            }
            for row in doc.accounts
        ],
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
