"""Office Expense behaviour for Payment Entry."""

from __future__ import annotations

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_account_details
from frappe import _
from frappe.utils import flt


class OfficeExpensePaymentMixin:
    """Allow the Office Expense workflow to create a balanced, no-party Pay entry.

    Other documents fall through to ``super()``, so this mixin can sit in front of
    ERPNext's controller next to other apps' Payment Entry mixins.
    """

    def set_missing_values(self) -> None:
        if not self._is_office_expense_payment():
            return super().set_missing_values()

        # Direct vouchers post their own GL legs; mixing the two would post the
        # expense twice.
        is_direct_voucher = getattr(self, "is_direct_voucher", None)
        if is_direct_voucher and is_direct_voucher():
            frappe.throw(_("Office Expense payments cannot be direct income or expense vouchers."))
        if self.party or self.party_type:
            frappe.throw(_("Office Expense payments cannot be linked to a party."))
        if self.paid_from != self.paid_to:
            frappe.throw(_("Office Expense payments must use one cash or bank account."))
        if not self.deductions:
            frappe.throw(_("Office Expense payments require expense deductions."))
        if flt(sum(flt(row.amount) for row in self.deductions)) != flt(self.paid_amount):
            frappe.throw(_("Office Expense deductions must equal the paid amount."))

        # ERPNext normally obtains these values from the customer or supplier
        # account. For this controlled payment they come from the cash/bank
        # account on both sides; only the deductions create the expense debits.
        account = get_account_details(self.paid_from, self.posting_date, self.cost_center)
        self.paid_from_account_currency = account.account_currency
        self.paid_from_account_type = account.account_type
        self.paid_to_account_currency = account.account_currency
        self.paid_to_account_type = account.account_type
        if self.meta.has_field("paid_from_account_balance"):
            self.paid_from_account_balance = account.account_balance
        if self.meta.has_field("paid_to_account_balance"):
            self.paid_to_account_balance = account.account_balance
        self.party_account = None
        self.party_account_currency = account.account_currency
        self.references = []

    def _is_office_expense_payment(self) -> bool:
        if self.payment_type != "Pay" or not self.get("rd_office_expense"):
            return False

        expense = frappe.db.get_value(
            "Office Expense", self.rd_office_expense, ["company", "payment_entry"], as_dict=True
        )
        if not expense or expense.company != self.company:
            frappe.throw(_("Office Expense payment must belong to the same Company."))

        return bool(
            self.flags.get("reckon_office_expense_payment")
            or expense.payment_entry == self.name
        )
