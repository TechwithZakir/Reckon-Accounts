"""Payment Entry controller registered through ``override_doctype_class``.

Frappe keeps one controller class per doctype, so every Reckon Payment Entry
behaviour lives here as a mixin. Each mixin is inert unless its own fields are set
on the document and otherwise defers to ERPNext through ``super()``.
"""

from __future__ import annotations

from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry as ERPNextPaymentEntry

from reckon_accounts.overrides.direct_voucher import (  # noqa: F401 - kept for old imports
    CASH_BANK_TYPES,
    DIRECT_SUBTYPES,
    DirectVoucherPaymentMixin,
)
from reckon_accounts.overrides.office_expense_payment import OfficeExpensePaymentMixin


class PaymentEntry(OfficeExpensePaymentMixin, DirectVoucherPaymentMixin, ERPNextPaymentEntry):
    """ERPNext Payment Entry with Office Expense payments and direct vouchers."""
