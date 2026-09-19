"""Strict structural validation for the ledger scope.

Successful parsing does not authorize a query or verify master records. The future
site adapter must check company/account/party ownership, permissions and supported
voucher and party types. Unsupported options fail instead of disappearing.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class LedgerFilters:
    company: str
    from_date: date
    to_date: date
    account: str | None = None
    party_type: str | None = None
    party: str | None = None
    voucher_type: str | None = None
    voucher_no: str | None = None
    payment_type: str | None = None
    mode_of_payment: str | None = None
    reference_no: str | None = None
    fiscal_year: str | None = None
    finance_book: str | None = None
    include_default_book_entries: bool = False
    show_opening_entries: bool = False
    dimensions: tuple[tuple[str, tuple[str | None, ...]], ...] = field(default_factory=tuple)
    only_entries_without_party: bool = False
    currency_mode: str = "company"
    page: int = 1
    page_size: int = 100

    @property
    def filtered_balance(self) -> bool:
        """Voucher filters affect opening, movement and closing, not only rows."""
        return any(
            (
                self.voucher_type,
                self.voucher_no,
                self.payment_type,
                self.mode_of_payment,
                self.reference_no,
            )
        )

    @property
    def balance_label(self) -> str:
        return "Filtered balance" if self.filtered_balance else "Balance"

    def balance_scope(self) -> dict:
        """Return calculation filters shared by opening/movement/export adapters.

        Period boundaries and pagination are deliberately separate: adapters use
        from_date/to_date with their verified opening and movement policies.
        """
        return {
            key: getattr(self, key)
            for key in (
                "company",
                "account",
                "party_type",
                "party",
                "voucher_type",
                "voucher_no",
                "payment_type",
                "mode_of_payment",
                "reference_no",
                "only_entries_without_party",
                "currency_mode",
                "finance_book",
                "include_default_book_entries",
                "dimensions",
            )
        }


def _text(values: Mapping, key: str, *, required: bool = False) -> str | None:
    value = values.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _date(values: Mapping, key: str) -> date:
    value = values.get(key)
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(f"{key} must be a date or YYYY-MM-DD string")


def parse_ledger_filters(values: Mapping) -> LedgerFilters:
    """Validate a mapping; accept explicit null for absent optional link filters.

    Dimensions accept a mapping of field names to lists of names (null means blank).
    Site adapters validate metadata, ownership, fiscal bounds and currency scope.
    Even empty unknown keys are rejected. UI adapters must remove unselected
    optional inputs or normalize them to null before parsing.
    """
    if not isinstance(values, Mapping):
        raise ValueError("Ledger filters must be a mapping")
    allowed = set(LedgerFilters.__dataclass_fields__)
    if any(key not in allowed for key in values):
        raise ValueError("Unsupported ledger filter")
    company = _text(values, "company", required=True)
    start, end = _date(values, "from_date"), _date(values, "to_date")
    if start > end:
        raise ValueError("from_date must not be later than to_date")
    links = {
        key: _text(values, key)
        for key in (
            "account",
            "party_type",
            "party",
            "voucher_type",
            "voucher_no",
            "payment_type",
            "mode_of_payment",
            "reference_no",
            "fiscal_year",
            "finance_book",
        )
    }
    if links["party"] and not links["party_type"]:
        raise ValueError("party requires party_type")
    if links["voucher_no"] and not links["voucher_type"]:
        raise ValueError("voucher_no requires voucher_type")
    no_party = values.get("only_entries_without_party", False)
    if type(no_party) is not bool:
        raise ValueError("only_entries_without_party must be a boolean")
    if no_party and (links["party"] or links["party_type"] not in (None, "Other")):
        raise ValueError("Party filters conflict with only_entries_without_party")
    if links["party_type"] == "Other":
        if links["party"]:
            raise ValueError("Other must not specify a party")
    if links["payment_type"] not in (None, "Receive", "Pay", "Internal Transfer"):
        raise ValueError("Unsupported payment_type")
    if links["payment_type"] and links["voucher_type"] not in (None, "Payment Entry"):
        raise ValueError("payment_type requires Payment Entry voucher scope")
    currency = values.get("currency_mode", "company")
    if currency not in ("company", "account"):
        raise ValueError("currency_mode must be company or account")
    if currency == "account" and not links["account"]:
        raise ValueError("Account currency requires a single ledger account")
    flags = {}
    for key in ("include_default_book_entries", "show_opening_entries"):
        flags[key] = values.get(key, False)
        if type(flags[key]) is not bool:
            raise ValueError(f"{key} must be a boolean")
    dimensions = values.get("dimensions", {})
    if not isinstance(dimensions, Mapping) or len(dimensions) > 20:
        raise ValueError("dimensions must be a mapping of at most 20 fields")
    parsed_dimensions = []
    for key, selections in dimensions.items():
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError("Invalid dimension field name")
        if not isinstance(selections, (list, tuple)) or not 1 <= len(selections) <= 100:
            raise ValueError("Each dimension requires 1 to 100 selections")
        normalized = []
        for selection in selections:
            if selection is not None and (not isinstance(selection, str) or not selection.strip()):
                raise ValueError("Dimension selections must be names or null for blank")
            normalized.append(selection.strip() if selection is not None else None)
        parsed_dimensions.append((key, tuple(dict.fromkeys(normalized))))
    page, size = values.get("page", 1), values.get("page_size", 100)
    if type(page) is not int or page < 1:
        raise ValueError("page must be a positive integer")
    if type(size) is not int or not 1 <= size <= 500:
        raise ValueError("page_size must be an integer from 1 to 500")
    return LedgerFilters(
        company=company,
        from_date=start,
        to_date=end,
        **links,
        only_entries_without_party=no_party,
        currency_mode=currency,
        page=page,
        page_size=size,
        dimensions=tuple(sorted(parsed_dimensions)),
        **flags,
    )
