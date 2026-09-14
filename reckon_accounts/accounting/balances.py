"""Pure ledger arithmetic; source filtering and currency rounding belong to adapters.

Inputs must already share a company, currency, permission scope, and report scope.
Amounts retain source precision. These helpers do not determine opening-entry or
fiscal-year policies and never read or write accounting records.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

Amount = Decimal | int | float | str


def as_decimal(value: Amount) -> Decimal:
    """Convert a finite amount without importing binary float representation noise."""
    if isinstance(value, bool):
        raise ValueError("A boolean is not an accounting amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid accounting amount") from exc
    if not amount.is_finite():
        raise ValueError("Accounting amounts must be finite")
    return amount


@dataclass(frozen=True)
class Balance:
    """Signed ledger balance: positive debit, negative credit."""

    net: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "net", as_decimal(self.net))

    @property
    def debit(self) -> Decimal:
        return max(self.net, Decimal(0))

    @property
    def credit(self) -> Decimal:
        return max(-self.net, Decimal(0))

    @property
    def balance_type(self) -> str:
        return "Dr" if self.net > 0 else "Cr" if self.net < 0 else ""


def net_balance(debit: Amount, credit: Amount) -> Balance:
    """Return debit minus credit, without reversing by account nature."""
    return Balance(as_decimal(debit) - as_decimal(credit))


def closing_balance(opening: Amount, debit: Amount, credit: Amount) -> Balance:
    """Apply period movement to a signed opening or page carry-forward balance."""
    return Balance(as_decimal(opening) + as_decimal(debit) - as_decimal(credit))
