"""Deterministic grouped ledgers over adapter-authorized, scoped GL records."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from reckon_accounts.accounting.balances import Balance, as_decimal
from reckon_accounts.accounting.catalog import BOOK_REPORTS
from reckon_accounts.accounting.filters import LedgerFilters

REPORTS = {
    "Party Ledger": "party",
    "Account Ledger": "account",
    "General Ledger Custom": "general",
}
REPORTS.update(BOOK_REPORTS)


@dataclass(frozen=True)
class Posting:
    name: str
    posting_date: date
    creation: datetime
    account: str
    debit: Decimal
    credit: Decimal
    party_type: str = ""
    party: str = ""
    party_name: str = ""
    voucher_type: str = ""
    voucher_no: str = ""
    voucher_label: str = ""
    remarks: str = ""
    particulars: str = ""
    is_opening: bool = False
    account_root_type: str = ""
    account_name: str = ""

    def __post_init__(self):
        if not self.name or not self.account:
            raise ValueError("Posting identity and ledger account are required")
        if type(self.posting_date) is not date or type(self.creation) is not datetime:
            raise ValueError("Posting date and creation timestamp must be normalized")
        object.__setattr__(self, "debit", as_decimal(self.debit))
        object.__setattr__(self, "credit", as_decimal(self.credit))


@dataclass(frozen=True)
class Movement:
    posting: Posting
    running: Decimal


@dataclass(frozen=True)
class Section:
    key: tuple[str, str, str]
    party_heading: str
    account: str
    opening: Decimal
    debit: Decimal
    credit: Decimal
    closing: Decimal
    movements: tuple[Movement, ...]
    account_root_type: str = ""
    account_name: str = ""


@dataclass(frozen=True)
class LedgerResult:
    report_name: str
    filters: LedgerFilters
    currency: str
    precision: int
    sections: tuple[Section, ...]
    generated_at: str
    account_titles: tuple[tuple[str, str], ...] = ()

    @property
    def total_rows(self):
        return sum(len(section.movements) for section in self.sections)

    @property
    def total_pages(self):
        return max(1, (self.total_rows + self.filters.page_size - 1) // self.filters.page_size)

    def totals(self):
        """Sum detail-side balances without netting opposite parties/accounts."""
        result = dict.fromkeys(
            (
                "opening_debit",
                "opening_credit",
                "debit",
                "credit",
                "closing_debit",
                "closing_credit",
            ),
            Decimal(0),
        )
        for section in self.sections:
            for prefix in ("opening", "closing"):
                balance = Balance(getattr(section, prefix))
                result[prefix + "_debit"] += balance.debit
                result[prefix + "_credit"] += balance.credit
            result["debit"] += section.debit
            result["credit"] += section.credit
        return result


def validate_report_scope(report_name: str, filters: LedgerFilters):
    if report_name not in REPORTS:
        raise ValueError("Unknown Reckon report")


def build_ledger(
    report_name: str,
    filters: LedgerFilters,
    postings: Iterable[Posting],
    *,
    currency: str,
    precision: int,
    round_amount: Callable[[Decimal], Decimal],
    generated_at: str,
    ignore_opening_check: bool = False,
) -> LedgerResult:
    """Use the inspected v15/v16 GL opening classification; no statement policy.

    Adapters exclude cancelled rows and apply scope and authorization before this
    function. Opening vouchers may fall after to_date when the site does not ignore
    the opening check, matching the reference GL. Period Closing Vouchers remain
    included. Rounding is supplied by the installed framework for presentation.
    """
    validate_report_scope(report_name, filters)
    groups = {}
    identities = set()
    for posting in postings:
        if posting.name in identities:
            raise ValueError("Duplicate GL identity")
        identities.add(posting.name)
        if posting.posting_date > filters.to_date and (
            ignore_opening_check or not posting.is_opening
        ):
            continue
        group_party = REPORTS[report_name] in {"party", "general"} and filters.party_type != "Other"
        key = (
            posting.account,
            posting.party_type if group_party else "",
            posting.party if group_party else "",
        )
        groups.setdefault(key, []).append(posting)
    sections = []
    for key, records in sorted(groups.items()):
        records.sort(key=lambda row: (row.posting_date, row.creation, row.name))
        opening = debit = credit = Decimal(0)
        period = []
        for row in records:
            if row.posting_date < filters.from_date or (
                row.is_opening and not filters.show_opening_entries
            ):
                opening += row.debit - row.credit
            else:
                period.append(row)
        running = opening
        movements = []
        for row in period:
            debit += row.debit
            credit += row.credit
            running += row.debit - row.credit
            movements.append(Movement(row, round_amount(running)))
        title = records[0].party_name or key[2] or "Entries without party"
        if REPORTS[report_name] not in {"party", "general"} or filters.party_type == "Other":
            title = "Entries without party" if filters.only_entries_without_party else "All parties"
        sections.append(
            Section(
                key,
                title,
                key[0],
                round_amount(opening),
                round_amount(debit),
                round_amount(credit),
                round_amount(running),
                tuple(movements),
                records[0].account_root_type,
                records[0].account_name or key[0],
            )
        )
    result = LedgerResult(report_name, filters, currency, precision, tuple(sections), generated_at)
    if filters.page > result.total_pages:
        raise ValueError("Page exceeds available results; return to page 1 after changing filters")
    return result


def display_rows(result: LedgerResult, *, full: bool = False) -> list[dict]:
    """Paginate movements, repeating mandatory headings and full section totals.

    Summary and heading rows do not consume the transaction page size. A group
    with only opening activity appears on page 1. Exports call once with full=True.
    """
    start = 0 if full else (result.filters.page - 1) * result.filters.page_size
    stop = result.total_rows if full else start + result.filters.page_size
    offset = 0
    rows = []

    def add(kind, label="", **values):
        rows.append({"row_kind": kind, "description": label, "currency": result.currency, **values})

    for section in result.sections:
        count = len(section.movements)
        low, high = max(0, start - offset), min(count, stop - offset)
        selected = section.movements[low:high] if high > low else ()
        opening_only = not count and (full or result.filters.page == 1)
        offset += count
        if not selected and not opening_only:
            continue
        add("party_heading", section.party_heading)
        add(
            "account_heading",
            section.account_name or section.account,
            account=section.account,
            account_name=section.account_name or section.account,
        )
        add("opening", "Full-scope opening", balance=section.opening)
        carry = section.movements[low - 1].running if selected and low else section.opening
        if selected:
            add("carry", "Page carry-forward", balance=carry)
        for movement in selected:
            posting = movement.posting
            add(
                "entry",
                posting.particulars,
                posting_date=posting.posting_date,
                gl_entry=posting.name,
                account=posting.account,
                account_name=posting.account_name or posting.account,
                party_type=posting.party_type,
                party=posting.party,
                party_name=posting.party_name,
                voucher_type=posting.voucher_type,
                voucher_no=posting.voucher_no,
                voucher_label=posting.voucher_label,
                debit=posting.debit,
                credit=posting.credit,
                balance=movement.running,
                remarks=posting.remarks,
            )
        if selected:
            add("page_closing", "Page ending balance", balance=selected[-1].running)
        add("period", "Full-period movement", debit=section.debit, credit=section.credit)
        add("closing", "Full-scope closing", balance=section.closing)
    for row in rows:
        if "balance" in row:
            balance = Balance(row["balance"])
            row.update(
                balance_type=balance.balance_type,
                balance_debit=balance.debit,
                balance_credit=balance.credit,
            )
    return rows
