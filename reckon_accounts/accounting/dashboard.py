"""Permission-aware dashboard summaries built from the authorized ledger scope."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from reckon_accounts.accounting.adapters import LedgerAdapter


def build_dashboard(gateway, filters):
    """Return the Accounts Dashboard payload without bypassing report permissions."""
    result = LedgerAdapter(gateway).run("General Ledger Custom", filters, full=True)
    account_details = _account_details(gateway, result.sections)
    postings = [movement.posting for section in result.sections for movement in section.movements]
    months = _months(result.filters.from_date, result.filters.to_date)

    income = Decimal(0)
    expenses = Decimal(0)
    income_by_month = defaultdict(Decimal)
    expenses_by_month = defaultdict(Decimal)
    cash_flow = defaultdict(lambda: defaultdict(Decimal))
    income_accounts = defaultdict(Decimal)
    expense_accounts = defaultdict(Decimal)
    transactions = {}

    for posting in postings:
        month = posting.posting_date.strftime("%Y-%m")
        root_type = posting.account_root_type or account_details.get(posting.account, {}).get(
            "root_type", ""
        )
        account_type = account_details.get(posting.account, {}).get("account_type", "")
        if root_type == "Income":
            amount = posting.credit - posting.debit
            if amount > 0:
                income += amount
                income_by_month[month] += amount
                income_accounts[posting.account_name or posting.account] += amount
        elif root_type == "Expense":
            amount = posting.debit - posting.credit
            if amount > 0:
                expenses += amount
                expenses_by_month[month] += amount
                expense_accounts[posting.account_name or posting.account] += amount

        if account_type in {"Bank", "Cash"}:
            category = _cash_flow_category(root_type)
            cash_flow[month][category] += posting.debit - posting.credit

        key = (posting.voucher_type, posting.voucher_no)
        transaction = transactions.setdefault(
            key,
            {
                "date": posting.posting_date.isoformat(),
                "voucher_no": posting.voucher_no,
                "type": posting.voucher_label or posting.voucher_type,
                "particulars": posting.particulars,
                "debit": Decimal(0),
                "credit": Decimal(0),
            },
        )
        transaction["debit"] += posting.debit
        transaction["credit"] += posting.credit
        transaction["date"] = max(transaction["date"], posting.posting_date.isoformat())

    receivables = _party_balances(result.sections, account_details, "Receivable", result.filters.to_date)
    payables = _party_balances(result.sections, account_details, "Payable", result.filters.to_date)
    cash_balances = _account_balances(result.sections, account_details, {"Bank", "Cash"})

    return {
        "currency": result.currency,
        "period": {
            "from_date": result.filters.from_date.isoformat(),
            "to_date": result.filters.to_date.isoformat(),
        },
        "kpis": {
            "income": _number(income),
            "expenses": _number(expenses),
            "profit": _number(income - expenses),
            "receivables": _number(sum(item["balance"] for item in receivables)),
            "payables": _number(sum(item["balance"] for item in payables)),
            "cash": _number(sum(item["balance"] for item in cash_balances)),
        },
        "trend": [
            {
                "month": month,
                "label": _month_label(month),
                "income": _number(income_by_month[month]),
                "expenses": _number(expenses_by_month[month]),
            }
            for month in months
        ],
        "cash_flow": [
            {
                "month": month,
                "label": _month_label(month),
                "operating": _number(cash_flow[month]["operating"]),
                "investing": _number(cash_flow[month]["investing"]),
                "financing": _number(cash_flow[month]["financing"]),
            }
            for month in months
        ],
        "receivables": receivables[:5],
        "payables": payables[:5],
        "cash_balances": cash_balances[:5],
        "top_income": _top_accounts(income_accounts),
        "top_expense": _top_accounts(expense_accounts),
        "recent": [
            {
                **item,
                "debit": _number(item["debit"]),
                "credit": _number(item["credit"]),
            }
            for item in sorted(transactions.values(), key=lambda item: item["date"], reverse=True)[:8]
        ],
    }


def _account_details(gateway, sections):
    names = sorted({section.account for section in sections})
    if not names:
        return {}
    records = gateway.list_records(
        "Account", filters={"name": ["in", names]}, limit=min(len(names), 5000)
    )
    return {record["name"]: record for record in records}


def _party_balances(sections, account_details, account_type, as_of):
    balances = defaultdict(lambda: {"balance": Decimal(0), "date": as_of})
    for section in sections:
        if account_details.get(section.account, {}).get("account_type") != account_type:
            continue
        party = next((movement.posting for movement in section.movements if movement.posting.party), None)
        if not party:
            continue
        key = party.party_name or party.party
        item = balances[key]
        item["balance"] += abs(section.closing)
        if party.posting_date < item["date"]:
            item["date"] = party.posting_date
    return sorted(
        [
            {
                "name": name,
                "balance": _number(item["balance"]),
                "days": max(0, (as_of - item["date"]).days),
            }
            for name, item in balances.items()
            if item["balance"]
        ],
        key=lambda item: item["balance"],
        reverse=True,
    )


def _account_balances(sections, account_details, account_types):
    balances = defaultdict(Decimal)
    for section in sections:
        if account_details.get(section.account, {}).get("account_type") in account_types:
            balances[section.account_name or section.account] += abs(section.closing)
    return sorted(
        [{"name": name, "balance": _number(balance)} for name, balance in balances.items() if balance],
        key=lambda item: item["balance"],
        reverse=True,
    )


def _top_accounts(values):
    return [
        {"name": name, "amount": _number(amount)}
        for name, amount in sorted(values.items(), key=lambda item: item[1], reverse=True)[:5]
    ]


def _cash_flow_category(root_type):
    return {"Asset": "investing", "Equity": "financing", "Liability": "financing"}.get(
        root_type, "operating"
    )


def _months(start, end):
    current = start.replace(day=1)
    values = []
    while current <= end:
        values.append(current.strftime("%Y-%m"))
        current = current.replace(year=current.year + (current.month == 12), month=1 if current.month == 12 else current.month + 1)
    return values


def _month_label(value):
    return date.fromisoformat(value + "-01").strftime("%b")


def _number(value):
    return float(Decimal(value).quantize(Decimal("0.01")))
