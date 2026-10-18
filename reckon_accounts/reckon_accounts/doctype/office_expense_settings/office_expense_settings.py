from __future__ import annotations

from frappe.model.document import Document

from reckon_accounts.office_expense import validate_office_expense_settings


class OfficeExpenseSettings(Document):
    def validate(self) -> None:
        validate_office_expense_settings(self)
