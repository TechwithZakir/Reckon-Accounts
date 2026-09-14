"""Shared Script Report presentation and server-generated full CSV exports."""

import csv
import json
from dataclasses import asdict
from decimal import Decimal
from html import escape
from io import StringIO

from reckon_accounts.accounting.service import display_rows


def columns(precision):
    specifications = [
        ("description", "Particulars / section", "Data", 250),
        ("posting_date", "Posting Date", "Date", 110),
        ("voucher_label", "Voucher", "Data", 120),
        ("voucher_type", "Source Type", "Data", 130),
        ("voucher_no", "Source Voucher", "Dynamic Link", 160),
        ("account_name", "Ledger Account", "Data", 180),
        ("account", "Account ID", "Data", 180),
        ("party_name", "Party Name", "Data", 150),
        ("debit", "Debit", "Currency", 120),
        ("credit", "Credit", "Currency", 120),
        ("balance", "Signed Balance", "Currency", 130),
        ("balance_type", "Dr / Cr", "Data", 65),
        ("balance_debit", "Balance Dr", "Currency", 120),
        ("balance_credit", "Balance Cr", "Currency", 120),
        ("remarks", "Narration", "Data", 250),
        ("row_kind", "Row Type", "Data", 100),
        ("currency", "Currency", "Data", 80),
        ("gl_entry", "GL Entry", "Data", 130),
        ("party_type", "Party Type", "Data", 100),
        ("party", "Party ID", "Data", 130),
    ]
    result = []
    for fieldname, label, fieldtype, width in specifications:
        column = dict(fieldname=fieldname, label=label, fieldtype=fieldtype, width=width)
        if fieldtype == "Currency":
            column.update(options="currency", precision=precision)
        elif fieldtype == "Dynamic Link":
            column["options"] = "voucher_type"
        if fieldname in ("row_kind", "currency", "gl_entry", "party_type", "party", "account"):
            column["hidden"] = 1
        result.append(column)
    return result


def context(result):
    values = asdict(result.filters)
    values["dimensions"] = dict(result.filters.dimensions)
    titles = dict(result.account_titles)
    titles.update(
        {section.account: section.account_name or section.account for section in result.sections}
    )
    if values.get("account"):
        values["account"] = titles.get(values["account"], values["account"])
    for section in result.sections:
        if values.get("party") and section.key[2] == values["party"]:
            values["party"] = section.party_heading
            break
    return {key: value for key, value in values.items() if value is not None}


def message(result):
    scope = escape(json.dumps(context(result), default=str, ensure_ascii=False))
    return (
        f"<div><strong>{escape(result.filters.balance_label)} — {escape(result.currency)}</strong>"
        f"<p>Page {result.filters.page} of {result.total_pages}; "
        f"{result.total_rows} permitted period entries. Totals cover the full permitted scope. "
        "Each section has its own running balance.</p>"
        "<p>Only entries with permitted accounts, parties, dimensions and source vouchers are included. "
        "Opening vouchers follow the site General Ledger policy and may fall outside the date range. "
        "Refresh recalculates backdated changes. Use Export Full Ledger for all entries; "
        "printing and the standard framework export contain the displayed page.</p>"
        f"<details><summary>Active filters</summary><pre>{scope}</pre></details>"
        f"<small>Generated {escape(result.generated_at)}</small></div>"
    )


def report_tuple(result):
    summary = [
        dict(
            label=key.replace("_", " ").title(),
            value=value,
            datatype="Currency",
            currency=result.currency,
            indicator="Blue",
        )
        for key, value in result.totals().items()
    ]
    page_notice = {
        "row_kind": "scope",
        "description": (
            f"PAGE {result.filters.page}/{result.total_pages} — {result.filters.balance_label}; "
            "Export Full Ledger includes all permitted entries"
        ),
        "currency": result.currency,
    }
    return (
        columns(result.precision),
        [page_notice, *display_rows(result)],
        message(result),
        None,
        summary,
        True,
    )


def _csv_text(value):
    """Prevent formulas in textual identifiers/narration, preserving numeric cells."""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def export_csv(result):
    """One result materialization for every exported section; no page re-queries."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([result.report_name, "Full permitted ledger", result.currency])
    writer.writerow(["Generated", result.generated_at])
    writer.writerow(["Balance scope", result.filters.balance_label])
    for key, value in context(result).items():
        if key not in ("page", "page_size"):
            writer.writerow([key, _csv_text(json.dumps(value, default=str, ensure_ascii=False))])
    writer.writerow(
        ["Policy", "Permission-restricted scope; opening vouchers follow site GL settings"]
    )
    writer.writerow([])
    fields = columns(result.precision)
    writer.writerow([field["label"] for field in fields])
    for row in display_rows(result, full=True):
        cells = []
        for field in fields:
            value = row.get(field["fieldname"], "")
            if isinstance(value, (Decimal, int, float)) and not isinstance(value, bool):
                cells.append(str(value))
            else:
                cells.append(_csv_text(value))
        writer.writerow(cells)
    return "\ufeff" + output.getvalue()


def execute_report(report_name, filters=None):
    import frappe

    from reckon_accounts.accounting.adapters import LedgerAdapter, get_gateway
    from reckon_accounts.api import normalize_report_filters

    try:
        result = LedgerAdapter(get_gateway()).run(report_name, normalize_report_filters(filters))
        return report_tuple(result)
    except ValueError as exc:
        frappe.throw(str(exc))
