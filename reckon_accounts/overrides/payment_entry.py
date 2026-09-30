"""Payment Entry extensions for direct income and expense vouchers."""

from __future__ import annotations

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry as ERPNextPaymentEntry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_account_details
from frappe import _

DIRECT_SUBTYPES = {"Direct Expense": "Pay", "Direct Income": "Receive"}
CASH_BANK_TYPES = {"Cash", "Bank"}


class PaymentEntry(ERPNextPaymentEntry):
    """Allow direct income/expense rows while preserving ERPNext's normal PE flow."""

    def is_direct_voucher(self):
        return self.get("custom_voucher_subtype") in DIRECT_SUBTYPES

    def set_missing_values(self):
        if not self.is_direct_voucher():
            return super().set_missing_values()

        expected_payment_type = DIRECT_SUBTYPES[self.custom_voucher_subtype]
        if self.payment_type != expected_payment_type:
            frappe.throw(
                _("{0} must use Payment Type {1}").format(
                    _(self.custom_voucher_subtype), _(expected_payment_type)
                )
            )

        if self.get("taxes") or self.get("deductions"):
            frappe.throw(_("Taxes and deductions are not supported for direct vouchers"))

        self._validate_direct_accounts()
        for fieldname in (
            "party_type",
            "party",
            "party_name",
            "contact_person",
            "contact_email",
            "bank_account",
            "party_bank_account",
            "total_allocated_amount",
            "base_total_allocated_amount",
            "unallocated_amount",
        ):
            self.set(fieldname, None)
        self.references = []
        self.party_account = None
        self.party_account_currency = (
            self.paid_from_account_currency
            if self.payment_type == "Receive"
            else self.paid_to_account_currency
        )
        self.is_opening = "No"

    def _validate_direct_accounts(self):
        if self.payment_type == "Pay":
            cash_bank_field, profit_loss_field = "paid_from", "paid_to"
            profit_loss_root_type = "Expense"
        else:
            cash_bank_field, profit_loss_field = "paid_to", "paid_from"
            profit_loss_root_type = "Income"

        cash_bank = self._get_account(cash_bank_field)
        profit_loss = self._get_account(profit_loss_field)
        self._validate_account(cash_bank, cash_bank_field, account_types=CASH_BANK_TYPES)
        self._validate_account(profit_loss, profit_loss_field, root_type=profit_loss_root_type)
        if cash_bank.name == profit_loss.name:
            frappe.throw(_("Direct voucher accounts must be different"))

        for fieldname in ("paid_from", "paid_to"):
            details = get_account_details(self.get(fieldname), self.posting_date, self.cost_center)
            self.set(f"{fieldname}_account_currency", details.account_currency)
            self.set(f"{fieldname}_account_type", details.account_type)

    def _get_account(self, fieldname):
        name = self.get(fieldname)
        if not name:
            frappe.throw(_("{0} is mandatory").format(self.meta.get_label(fieldname)))
        frappe.has_permission("Account", "read", name, throw=True)
        return frappe.get_cached_doc("Account", name)

    def _validate_account(self, account, fieldname, *, account_types=None, root_type=None):
        if account.company != self.company:
            frappe.throw(_("{0} must belong to the selected company").format(self.meta.get_label(fieldname)))
        if account.is_group:
            frappe.throw(_("{0} cannot be a group account").format(self.meta.get_label(fieldname)))
        if account_types and account.account_type not in account_types:
            frappe.throw(
                _("{0} must be a Cash or Bank account").format(self.meta.get_label(fieldname))
            )
        if root_type and account.root_type != root_type:
            frappe.throw(
                _("{0} must be an {1} account").format(
                    self.meta.get_label(fieldname), _(root_type)
                )
            )

    def add_party_gl_entries(self, gl_entries):
        if not self.is_direct_voucher():
            return super().add_party_gl_entries(gl_entries)

        if self.payment_type == "Pay":
            account = self.paid_to
            account_currency = self.paid_to_account_currency
            amount = self.received_amount
            base_amount = self.base_received_amount
            debit_or_credit = "debit"
            against = self.paid_from
        else:
            account = self.paid_from
            account_currency = self.paid_from_account_currency
            amount = self.paid_amount
            base_amount = self.base_paid_amount
            debit_or_credit = "credit"
            against = self.paid_to

        transaction_amount = (
            amount
            if account_currency == self.transaction_currency
            else base_amount / self.transaction_exchange_rate
        )
        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": account,
                    "account_currency": account_currency,
                    "against": against,
                    debit_or_credit: base_amount,
                    f"{debit_or_credit}_in_account_currency": amount,
                    f"{debit_or_credit}_in_transaction_currency": transaction_amount,
                    "cost_center": self.cost_center,
                },
                item=self,
            )
        )

    def set_unallocated_amount(self):
        if self.is_direct_voucher():
            self.unallocated_amount = 0
            return
        super().set_unallocated_amount()

    def set_difference_amount(self):
        if self.is_direct_voucher():
            self.difference_amount = 0
            return
        super().set_difference_amount()

    def set_title(self):
        if self.is_direct_voucher():
            label = "Expense" if self.payment_type == "Pay" else "Income"
            account = self.paid_to if self.payment_type == "Pay" else self.paid_from
            self.title = _("Direct {0} - {1}").format(_(label), account)
            return
        super().set_title()

    def set_remarks(self):
        if not self.is_direct_voucher():
            return super().set_remarks()
        if self.custom_remarks:
            return

        label = "expense payment" if self.payment_type == "Pay" else "income receipt"
        account = self.paid_to if self.payment_type == "Pay" else self.paid_from
        amount = self.received_amount if self.payment_type == "Pay" else self.paid_amount
        remarks = [
            _("Direct {0} of {1} {2} through {3}").format(
                _(label), _(self.party_account_currency), amount, account
            )
        ]
        if self.reference_no:
            remarks.append(
                _("Transaction reference no {0} dated {1}").format(
                    self.reference_no, self.reference_date
                )
            )
        self.set("remarks", "\n".join(remarks))
