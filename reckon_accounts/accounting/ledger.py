"""In-memory pagination for one already authorized account/currency scope.

Adapters supply the opening and complete period rows after applying their date,
opening-voucher, cancellation and permission policies. This is not a database
query or a scalable export implementation. Each call uses one materialized input;
separate calls do not promise consistency across concurrent postings.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from reckon_accounts.accounting.balances import Amount, Balance, as_decimal


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    posting_date: date
    debit: Decimal
    credit: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.entry_id, str) or not self.entry_id.strip():
            raise ValueError("A unique entry identity is required")
        if type(self.posting_date) is not date:
            raise ValueError("Posting date must be a date without a time")
        object.__setattr__(self, "debit", as_decimal(self.debit))
        object.__setattr__(self, "credit", as_decimal(self.credit))


@dataclass(frozen=True)
class LedgerRow:
    entry: LedgerEntry
    balance: Balance


@dataclass(frozen=True)
class LedgerPage:
    rows: tuple[LedgerRow, ...]
    opening: Balance
    period_debit: Decimal
    period_credit: Decimal
    closing: Balance
    carry_forward: Balance
    page_closing: Balance
    page: int
    page_size: int
    total_rows: int
    total_pages: int
    has_next: bool


def paginate_ledger(
    entries: Iterable[LedgerEntry], opening: Amount, *, page: int = 1, page_size: int = 100
) -> LedgerPage:
    """Order by date/unique identity and keep full-scope totals on every page.

    Empty scopes have one empty page. Out-of-range pages are rejected. Signed
    debit/credit movements are retained, allowing adapter-approved reversals.
    Adapters must verify that their entry identity supplies the intended tie-breaker.
    """
    if type(page) is not int or page < 1:
        raise ValueError("Page must be a positive integer")
    if type(page_size) is not int or not 1 <= page_size <= 500:
        raise ValueError("Page size must be an integer from 1 to 500")
    opening_balance = Balance(opening)
    ordered = list(entries)
    if any(not isinstance(entry, LedgerEntry) for entry in ordered):
        raise ValueError("Period rows must be LedgerEntry instances")
    if len({entry.entry_id for entry in ordered}) != len(ordered):
        raise ValueError("Duplicate entry identities are not allowed")
    ordered.sort(key=lambda entry: (entry.posting_date, entry.entry_id))
    total_pages = max(1, (len(ordered) + page_size - 1) // page_size)
    if page > total_pages:
        raise ValueError("Page exceeds the available result pages")
    start = (page - 1) * page_size
    stop = start + page_size
    debit = credit = Decimal(0)
    running = opening_balance.net
    carry = page_closing = opening_balance
    rows = []
    for index, entry in enumerate(ordered):
        if index == start:
            carry = Balance(running)
        debit += entry.debit
        credit += entry.credit
        running += entry.debit - entry.credit
        if start <= index < stop:
            page_closing = Balance(running)
            rows.append(LedgerRow(entry, page_closing))
    return LedgerPage(
        tuple(rows),
        opening_balance,
        debit,
        credit,
        Balance(running),
        carry,
        page_closing,
        page,
        page_size,
        len(ordered),
        total_pages,
        page < total_pages,
    )
