from __future__ import annotations

from frappe.model.document import Document

from reckon_accounts.office_expense import (
    cancel_office_expense_payment_entry,
    create_office_expense_payment_entry,
    validate_office_expense,
)


class OfficeExpense(Document):
    def validate(self) -> None:
        validate_office_expense(self)

    def on_submit(self) -> None:
        create_office_expense_payment_entry(self)

    def on_cancel(self) -> None:
        cancel_office_expense_payment_entry(self)
