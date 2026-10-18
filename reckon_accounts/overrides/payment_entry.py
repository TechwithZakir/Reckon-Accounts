"""Payment Entry controller registered through ``override_doctype_class``.

Frappe keeps one controller class per doctype: the hook of the last installed app
wins. Reckon Distribution also overrides Payment Entry, so this class includes
Distribution's Office Expense mixin whenever that app is on the bench. Its controller
does the same with ``DirectVoucherPaymentMixin``, so both behaviours apply whichever
hook wins. Each mixin is inert unless its own fields are set on the document.
"""

from __future__ import annotations

import importlib

from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry as ERPNextPaymentEntry

from reckon_accounts.overrides.direct_voucher import (  # noqa: F401 - kept for old imports
    CASH_BANK_TYPES,
    DIRECT_SUBTYPES,
    DirectVoucherPaymentMixin,
)


def _optional_mixin(module_path, name):
    """Return ``name`` from ``module_path``, or None when that module is not installed."""
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        # Only a missing app (or an older version without this module) is optional;
        # a broken import inside an installed module must still fail loudly.
        if exc.name and (module_path == exc.name or module_path.startswith(f"{exc.name}.")):
            return None
        raise
    return getattr(module, name)


# Same base order as Reckon Distribution's controller, so the MRO does not depend
# on which app's hook Frappe picks.
_MIXINS = tuple(
    mixin
    for mixin in (
        _optional_mixin(
            "reckon_distribution.overrides.office_expense_payment", "OfficeExpensePaymentMixin"
        ),
        DirectVoucherPaymentMixin,
    )
    if mixin
)


class PaymentEntry(*_MIXINS, ERPNextPaymentEntry):
    """ERPNext Payment Entry with direct vouchers and, when present, Office Expense."""
