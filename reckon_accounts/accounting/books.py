"""Books and summaries over the same authorized posting dataset as the ledgers."""

import calendar
import csv
import json
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from html import escape
from io import StringIO

from reckon_accounts.accounting.balances import Balance
from reckon_accounts.accounting.catalog import BOOK_REPORTS, VOUCHER_VIEWS
from reckon_accounts.accounting.reporting import _csv_text, columns, context


@dataclass(frozen=True)
class BookResult:
    ledger: object
    # Units are indivisible for pagination: a whole voucher or a summary row.
    units: tuple[tuple[dict, ...], ...]
    notice: str
    page: int

    @property
    def total_pages(self):
        return max(
            1,
            (len(self.units) + self.ledger.filters.page_size - 1) // self.ledger.filters.page_size,
        )

    def rows(self, full=False):
        start = 0 if full else (self.page - 1) * self.ledger.filters.page_size
        stop = len(self.units) if full else start + self.ledger.filters.page_size
        return [row for unit in self.units[start:stop] for row in unit]


def row(ledger, kind, description, **values):
    result = {"row_kind": kind, "description": description, "currency": ledger.currency, **values}
    if result.get("account"):
        titles = dict(ledger.account_titles)
        titles.update(
            {
                section.account: section.account_name or section.account
                for section in ledger.sections
            }
        )
        title = titles.get(result["account"], result["account"])
        result["account_name"] = title
        if description == result["account"]:
            result["description"] = title
    if "balance" in result:
        balance = Balance(result["balance"])
        result.update(
            balance_type=balance.balance_type,
            balance_debit=balance.debit,
            balance_credit=balance.credit,
        )
    return result


def period_postings(ledger):
    return sorted(
        (
            movement.posting
            for section in ledger.sections
            for movement in section.movements
            if ledger.filters.from_date <= movement.posting.posting_date <= ledger.filters.to_date
        ),
        key=lambda item: (item.posting_date, item.creation, item.name),
    )


def months(start, end):
    current = start.replace(day=1)
    while current <= end:
        last = current.replace(day=calendar.monthrange(current.year, current.month)[1])
        yield max(start, current), min(end, last)
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


def monthly_rows(ledger):
    units = []
    for section in ledger.sections:
        running = section.opening
        for start, end in months(ledger.filters.from_date, ledger.filters.to_date):
            movement = [
                item.posting
                for item in section.movements
                if start <= item.posting.posting_date <= end
            ]
            debit = sum((item.debit for item in movement), Decimal(0))
            credit = sum((item.credit for item in movement), Decimal(0))
            opening = running
            running += debit - credit
            units.append(
                (
                    row(
                        ledger,
                        "monthly",
                        start.strftime("%B %Y"),
                        account=section.account,
                        posting_date=start,
                        period_end=end,
                        opening=opening,
                        debit=debit,
                        credit=credit,
                        balance=running,
                    ),
                )
            )
    return units


def group_monthly_rows(ledger):
    grouped = {}
    for unit in monthly_rows(ledger):
        item = unit[0]
        key = item["posting_date"]
        if key not in grouped:
            grouped[key] = row(
                ledger,
                "monthly",
                item["description"],
                account=ledger.filters.account,
                posting_date=key,
                period_end=item["period_end"],
                opening=Decimal(0),
                debit=Decimal(0),
                credit=Decimal(0),
                balance=Decimal(0),
                balance_debit=Decimal(0),
                balance_credit=Decimal(0),
            )
        target = grouped[key]
        for field in ("opening", "debit", "credit", "balance", "balance_debit", "balance_credit"):
            target[field] += item[field]
        target["balance_type"] = Balance(target["balance"]).balance_type
    return [(value,) for _, value in sorted(grouped.items())]


def group_summary_units(ledger, permissions):
    """Roll up once to permitted immediate children of the selected account group."""
    selected = ledger.filters.account
    grouped = {}
    for section in ledger.sections:
        child = section.account
        visited = set()
        while child != selected:
            if child in visited:
                raise ValueError("Account hierarchy contains a cycle")
            visited.add(child)
            record = permissions.require("Account", child)
            if "parent_account" not in record:
                raise ValueError("Account parent is not readable")
            parent = record.get("parent_account")
            if not parent or parent == selected:
                break
            if permissions.get("Account", parent) is None:
                child = section.account
                break
            child = parent
        if child not in grouped:
            grouped[child] = row(
                ledger,
                "summary",
                child,
                account=child,
                opening=Decimal(0),
                is_group=bool(permissions.require("Account", child).get("is_group")),
                debit=Decimal(0),
                credit=Decimal(0),
                balance=Decimal(0),
                balance_debit=Decimal(0),
                balance_credit=Decimal(0),
            )
        target = grouped[child]
        target["opening"] += section.opening
        target["debit"] += section.debit
        target["credit"] += section.credit
        target["balance"] += section.closing
        target["balance_debit"] += Balance(section.closing).debit
        target["balance_credit"] += Balance(section.closing).credit
        target["balance_type"] = Balance(target["balance"]).balance_type
    return tuple((record,) for _, record in sorted(grouped.items()))


def voucher_units(ledger, selected_keys=None):
    vouchers = defaultdict(list)
    for posting in period_postings(ledger):
        key = (posting.voucher_type, posting.voucher_no)
        if selected_keys is None or key in selected_keys:
            vouchers[key].append(posting)
    result = []
    for (doctype, name), postings in sorted(
        vouchers.items(), key=lambda item: (min(p.posting_date for p in item[1]), item[0])
    ):
        lines = [
            row(
                ledger,
                "voucher_heading",
                "Permitted voucher lines; completeness not asserted",
                voucher_type=doctype,
                voucher_no=name,
                posting_date=postings[0].posting_date,
            )
        ]
        for posting in postings:
            lines.extend(
                [
                    row(
                        ledger,
                        "party_heading",
                        posting.party_name or posting.party or "Entries without party",
                    ),
                    row(ledger, "account_heading", posting.account, account=posting.account),
                    row(
                        ledger,
                        "entry",
                        posting.particulars,
                        posting_date=posting.posting_date,
                        account=posting.account,
                        party=posting.party,
                        party_name=posting.party_name,
                        voucher_type=doctype,
                        voucher_no=name,
                        voucher_label=posting.voucher_label,
                        debit=posting.debit,
                        credit=posting.credit,
                        remarks=posting.remarks,
                        gl_entry=posting.name,
                    ),
                ]
            )
        lines.append(
            row(
                ledger,
                "voucher_total",
                "Permitted voucher totals",
                debit=sum((p.debit for p in postings), Decimal(0)),
                credit=sum((p.credit for p in postings), Decimal(0)),
            )
        )
        result.append(tuple(lines))
    return result


def make_book(ledger, *, page=1, selected_keys=None, current_assets=None, current_liabilities=None):
    kind = BOOK_REPORTS[ledger.report_name]
    notice = "All values cover permitted records only. Refresh recalculates backdated postings."
    units = []
    if kind in VOUCHER_VIEWS:
        if kind == "statistics":
            groups = defaultdict(set)
            for posting in period_postings(ledger):
                groups[posting.voucher_type].add(posting.voucher_no)
            units = [
                (
                    row(
                        ledger,
                        "statistics",
                        doctype,
                        voucher_type=doctype,
                        voucher_count=len(names),
                    ),
                )
                for doctype, names in sorted(groups.items())
            ]
            notice += " Counts are distinct posted vouchers, not GL lines; drafts and non-posting vouchers are excluded."
        else:
            units = voucher_units(ledger, selected_keys)
            notice += " Pagination keeps voucher lines together. Source permissions may restrict visible lines; no completeness claim is made."
    elif kind in {"monthly", "group_monthly"}:
        units = group_monthly_rows(ledger) if kind == "group_monthly" else monthly_rows(ledger)
        notice += " Months without movement retain their carried balance. Account rows are not double-counted across hierarchy levels."
    elif kind in {"cash_bank_summary", "bank_summary", "group_summary", "receipts_payments"}:
        for section in ledger.sections:
            units.append(
                (
                    row(
                        ledger,
                        "summary",
                        section.account,
                        account=section.account,
                        opening=section.opening,
                        debit=section.debit,
                        credit=section.credit,
                        balance=section.closing,
                    ),
                )
            )
        if kind == "receipts_payments":
            notice += " Debit/credit are gross cash/bank movements, including internal transfers; they are not external cash flow."
    elif kind == "funds_flow":
        assets, liabilities = set(current_assets or []), set(current_liabilities or [])
        if not assets or not liabilities or assets & liabilities:
            raise ValueError("Select distinct current asset and current liability account groups")
        opening_wc = closing_wc = Decimal(0)
        for section in ledger.sections:
            change = section.closing - section.opening
            if section.account in assets | liabilities:
                opening_wc += section.opening
                closing_wc += section.closing
                units.append(
                    (
                        row(
                            ledger,
                            "working_capital",
                            section.account,
                            account=section.account,
                            opening=section.opening,
                            balance=section.closing,
                            working_capital_change=change,
                        ),
                    )
                )
            else:
                units.append(
                    (
                        row(
                            ledger,
                            "funds",
                            section.account,
                            account=section.account,
                            sources=max(-change, Decimal(0)),
                            applications=max(change, Decimal(0)),
                        ),
                    )
                )
        units.append(
            (
                row(
                    ledger,
                    "working_capital_total",
                    "Net working capital (signed assets plus liabilities)",
                    opening=opening_wc,
                    balance=closing_wc,
                    working_capital_change=closing_wc - opening_wc,
                ),
            )
        )
        notice += " Sources/applications are net movements outside the explicitly selected current groups; this is a working-capital funds statement, not cash flow. Permission restrictions can leave the statement incomplete."
    elif kind in {"negative_cash", "exceptions"}:
        for section in ledger.sections:
            credit_normal = section.account_root_type in {"Liability", "Equity", "Income"}
            if kind == "exceptions" and section.account_root_type not in {
                "Asset",
                "Expense",
                "Liability",
                "Equity",
                "Income",
            }:
                raise ValueError("Account nature is required for ledger exceptions")
            direction = -1 if kind == "exceptions" and credit_normal else 1
            label = "Unexpected debit" if direction == -1 else "Credit"
            if section.opening * direction < 0:
                units.append(
                    (
                        row(
                            ledger,
                            "exception",
                            label + " opening balance",
                            account=section.account,
                            posting_date=ledger.filters.from_date,
                            balance=section.opening,
                        ),
                    )
                )
            days = {}
            for movement in section.movements:
                days[movement.posting.posting_date] = movement.running
            for day, balance in sorted(days.items()):
                if balance * direction < 0:
                    units.append(
                        (
                            row(
                                ledger,
                                "exception",
                                label + " end-of-day balance",
                                account=section.account,
                                posting_date=day,
                                balance=balance,
                            ),
                        )
                    )
        notice += " Flags balances opposite the expected account nature at opening and on transaction days; these are review candidates, not proof of accounting errors."
    elif kind in {"cash", "bank"}:
        # Ledger pagination already repeats section headings/carry-forward.
        paged = replace(ledger, filters=replace(ledger.filters, page=page))
        if page > paged.total_pages:
            raise ValueError("Page exceeds available results")
        return paged
    else:
        raise ValueError("Unsupported book view")
    result = BookResult(ledger, tuple(units), notice, page)
    if page > result.total_pages:
        raise ValueError("Page exceeds available results")
    return result


def run_book(adapter, report_name, filters, *, full=False, export=False):
    from reckon_accounts.accounting.filters import parse_ledger_filters

    filters = dict(filters)
    mapping = {
        key: filters.pop(key, None) for key in ("current_assets_group", "current_liabilities_group")
    }
    if BOOK_REPORTS[report_name] != "funds_flow" and any(mapping.values()):
        raise ValueError("Current group mapping is only valid for Funds Flow")
    parsed = parse_ledger_filters(filters)
    kind = BOOK_REPORTS[report_name]
    if kind in VOUCHER_VIEWS and parsed.currency_mode != "company":
        raise ValueError("Voucher views require company currency")
    query_filters = dict(filters, page=1)
    if kind in VOUCHER_VIEWS:
        query_filters["show_opening_entries"] = True
    ledger = adapter.run(report_name, query_filters, full=True, export=export)
    assets = liabilities = None
    if kind == "funds_flow":
        from reckon_accounts.accounting.dimensions import expand_selection

        if (
            parsed.currency_mode != "company"
            or parsed.account
            or parsed.party
            or parsed.party_type
            or parsed.filtered_balance
        ):
            raise ValueError(
                "Funds Flow requires company currency and no account, party or voucher restriction"
            )
        selections = []
        for key, root_type in (
            ("current_assets_group", "Asset"),
            ("current_liabilities_group", "Liability"),
        ):
            name = mapping[key]
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Select current asset and current liability groups")
            record = adapter.permissions.require("Account", name)
            if not record.get("is_group") or record.get("root_type") != root_type:
                raise ValueError("Current groups must be Asset and Liability groups respectively")
            selections.append(
                expand_selection(
                    adapter.gateway, adapter.permissions, "Account", [name], parsed.company
                )
            )
        assets, liabilities = selections
    keys = {(p.voucher_type, p.voucher_no) for p in period_postings(ledger)}
    if kind in VOUCHER_VIEWS - {"statistics"} and keys:
        # Select matching vouchers, then expand to every permitted line in the company.
        # Date and finance/dimension/account filters select vouchers, not their detail lines.
        expanded = dict(query_filters)
        for key in (
            "account",
            "party",
            "party_type",
            "dimensions",
            "only_entries_without_party",
            "finance_book",
            "include_default_book_entries",
        ):
            expanded.pop(key, None)
        # Adapter's private voucher expansion performs an identity-constrained read.
        ledger = adapter.run(report_name, expanded, full=True, export=export, voucher_keys=keys)
        ledger = replace(ledger, filters=replace(parsed, page=1, show_opening_entries=True))
    result = make_book(
        ledger,
        page=1 if full else parsed.page,
        selected_keys=keys,
        current_assets=assets,
        current_liabilities=liabilities,
    )
    if kind == "group_summary":
        # Validate page against the rolled-up units, not the ungrouped accounts.
        result = replace(result, units=group_summary_units(ledger, adapter.permissions))
        if result.page > result.total_pages:
            raise ValueError("Page exceeds available groups")
    if kind == "funds_flow":
        result = replace(
            result,
            notice=result.notice
            + " Current groups: "
            + str(mapping["current_assets_group"])
            + " / "
            + str(mapping["current_liabilities_group"]),
        )
    return result


def book_columns(precision):
    return columns(precision) + [
        {"fieldname": "is_group", "label": "Account Group", "fieldtype": "Check", "hidden": 1},
        {
            "fieldname": "opening",
            "label": "Opening",
            "fieldtype": "Currency",
            "options": "currency",
            "precision": precision,
        },
        {"fieldname": "period_end", "label": "Period End", "fieldtype": "Date"},
        {"fieldname": "voucher_count", "label": "Vouchers", "fieldtype": "Int"},
        *[
            {
                "fieldname": name,
                "label": label,
                "fieldtype": "Currency",
                "options": "currency",
                "precision": precision,
            }
            for name, label in (
                ("sources", "Sources"),
                ("applications", "Applications"),
                ("working_capital_change", "Working Capital Change"),
            )
        ],
    ]


def book_tuple(result):
    from reckon_accounts.accounting.reporting import report_tuple

    if not isinstance(result, BookResult):
        return report_tuple(result)
    scope = escape(json.dumps(context(result.ledger), default=str))
    notice = f"Page {result.page}/{result.total_pages}. " + result.notice
    return (
        book_columns(result.ledger.precision),
        [row(result.ledger, "scope", notice), *result.rows()],
        f"<p>{escape(notice)}</p><details><summary>Active filters</summary><pre>{scope}</pre></details>",
        None,
        [],
        True,
    )


def book_csv(result):
    from reckon_accounts.accounting.reporting import export_csv

    if not isinstance(result, BookResult):
        return export_csv(result)
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([result.ledger.report_name, "Full permitted result"])
    writer.writerow([result.notice])
    writer.writerow(["Filters", _csv_text(json.dumps(context(result.ledger), default=str))])
    fields = book_columns(result.ledger.precision)
    writer.writerow([field["label"] for field in fields])
    for record in result.rows(full=True):
        writer.writerow(
            [
                str(record.get(field["fieldname"], ""))
                if isinstance(record.get(field["fieldname"]), (Decimal, int, float))
                else _csv_text(record.get(field["fieldname"], ""))
                for field in fields
            ]
        )
    return "\ufeff" + output.getvalue()


def execute(report_name, filters=None):
    import frappe

    from reckon_accounts.accounting.adapters import LedgerAdapter, get_gateway
    from reckon_accounts.api import normalize_report_filters

    try:
        return book_tuple(
            run_book(LedgerAdapter(get_gateway()), report_name, normalize_report_filters(filters))
        )
    except ValueError as exc:
        frappe.throw(str(exc))
