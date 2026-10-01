"""Permission-aware dashboard summaries built from the authorized ledger scope."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from reckon_accounts.accounting.adapters import LedgerAdapter


def build_dashboard(gateway, filters):
    """Return the Accounts Dashboard payload without bypassing report permissions."""
    adapter = LedgerAdapter(gateway)
    result = adapter.run("General Ledger Custom", filters, full=True)
    current = _summarize(result, gateway)

    previous_filters = _previous_period_filters(filters)
    previous_result = adapter.run("General Ledger Custom", previous_filters, full=True)
    previous = _summarize(previous_result, gateway)

    return {
        "currency": result.currency,
        "period": {
            "from_date": result.filters.from_date.isoformat(),
            "to_date": result.filters.to_date.isoformat(),
        },
        "previous_period": {
            "from_date": previous_result.filters.from_date.isoformat(),
            "to_date": previous_result.filters.to_date.isoformat(),
        },
        "kpis": current["kpis"],
        "comparison": {
            key: _percent_change(current["kpis"][key], previous["kpis"][key])
            for key in current["kpis"]
        },
        "trend": current["trend"],
        "cash_flow": current["cash_flow"],
        "receivables": current["receivables"][:5],
        "payables": current["payables"][:5],
        "receivables_aging": _aging_summary(current["receivables"]),
        "payables_aging": _aging_summary(current["payables"]),
        "cash_balances": current["cash_balances"][:5],
        "account_balance_summary": current["account_balance_summary"],
        "account_heads": current["account_heads"],
        "top_income": current["top_income"],
        "top_expense": current["top_expense"],
        "recent": current["recent"],
        "transaction_count": current["transaction_count"],
    }


def _summarize(result, gateway):
    account_details = _account_details(gateway, result.sections)
    postings = [movement.posting for section in result.sections for movement in section.movements]
    months = _months(result.filters.from_date, result.filters.to_date)

    income = Decimal(0)
    expenses = Decimal(0)
    income_by_month = defaultdict(Decimal)
    expenses_by_month = defaultdict(Decimal)
    cash_flow = defaultdict(lambda: defaultdict(Decimal))
    income_accounts = {}
    expense_accounts = {}
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
                _add_account_amount(income_accounts, posting.account, posting.account_name, amount)
        elif root_type == "Expense":
            amount = posting.debit - posting.credit
            if amount > 0:
                expenses += amount
                expenses_by_month[month] += amount
                _add_account_amount(expense_accounts, posting.account, posting.account_name, amount)

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
                "status": "Posted",
            },
        )
        transaction["debit"] += posting.debit
        transaction["credit"] += posting.credit
        transaction["date"] = max(transaction["date"], posting.posting_date.isoformat())

    receivables = _party_balances(result.sections, account_details, "Receivable", result.filters.to_date)
    payables = _party_balances(result.sections, account_details, "Payable", result.filters.to_date)
    cash_balances = _account_balances(result.sections, account_details, {"Bank", "Cash"})

    return {
        "kpis": {
            "income": _number(income),
            "expenses": _number(expenses),
            "profit": _number(income - expenses),
            "receivables": _number(sum(Decimal(str(item["balance"])) for item in receivables)),
            "payables": _number(sum(Decimal(str(item["balance"])) for item in payables)),
            "cash": _number(sum(Decimal(str(item["balance"])) for item in cash_balances)),
        },
        "trend": [
            {
                "month": month,
                "label": _month_label(month),
                "income": _number(income_by_month[month]),
                "expenses": _number(expenses_by_month[month]),
                "profit": _number(income_by_month[month] - expenses_by_month[month]),
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
        "receivables": receivables,
        "payables": payables,
        "cash_balances": cash_balances,
        "account_balance_summary": _account_balance_summary(result.sections, account_details),
        "account_heads": _account_heads(result.sections, account_details),
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
        "transaction_count": len(transactions),
    }


def _previous_period_filters(filters):
    start = _as_date(filters["from_date"])
    end = _as_date(filters["to_date"])
    span = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span - 1)
    return {
        **filters,
        "from_date": previous_start.isoformat(),
        "to_date": previous_end.isoformat(),
        "page": 1,
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
    names = {}
    for section in sections:
        if account_details.get(section.account, {}).get("account_type") in account_types:
            balances[section.account] += abs(section.closing)
            names[section.account] = section.account_name or section.account
    return sorted(
        [
            {"account": account, "name": names[account], "balance": _number(balance)}
            for account, balance in balances.items()
            if balance
        ],
        key=lambda item: item["balance"],
        reverse=True,
    )


def _account_balance_summary(sections, account_details):
    values = defaultdict(lambda: {"accounts": set(), "balance": Decimal(0)})
    for section in sections:
        root_type = section.account_root_type or account_details.get(section.account, {}).get(
            "root_type", "Other"
        ) or "Other"
        values[root_type]["accounts"].add(section.account)
        values[root_type]["balance"] += abs(section.closing)
    order = ("Asset", "Liability", "Equity", "Income", "Expense", "Other")
    return [
        {
            "type": root_type,
            "accounts": len(values[root_type]["accounts"]),
            "balance": _number(values[root_type]["balance"]),
        }
        for root_type in order
        if root_type in values
    ]


def _account_heads(sections, account_details):
    values = {}
    for section in sections:
        account = section.account
        item = values.setdefault(
            account,
            {
                "account": account,
                "name": section.account_name or account,
                "root_type": section.account_root_type
                or account_details.get(account, {}).get("root_type", "Other")
                or "Other",
                "balance": Decimal(0),
            },
        )
        item["balance"] += abs(section.closing)
    return sorted(
        [
            {**item, "balance": _number(item["balance"])}
            for item in values.values()
            if item["balance"]
        ],
        key=lambda item: item["balance"],
        reverse=True,
    )


def _aging_summary(rows):
    buckets = [
        ("0 - 30 Days", 0, 30),
        ("31 - 60 Days", 31, 60),
        ("61 - 90 Days", 61, 90),
        ("> 90 Days", 91, None),
    ]
    values = [{"label": label, "amount": Decimal(0), "count": 0} for label, _, _ in buckets]
    for row in rows:
        for index, (_, low, high) in enumerate(buckets):
            if row["days"] >= low and (high is None or row["days"] <= high):
                values[index]["amount"] += Decimal(str(row["balance"]))
                values[index]["count"] += 1
                break
    total = sum(item["amount"] for item in values)
    return [
        {
            "label": item["label"],
            "amount": _number(item["amount"]),
            "count": item["count"],
            "percentage": _number(item["amount"] / total * 100) if total else 0.0,
        }
        for item in values
    ]


def _add_account_amount(values, account, name, amount):
    item = values.setdefault(account, {"account": account, "name": name or account, "amount": Decimal(0)})
    item["amount"] += amount


def _top_accounts(values):
    return [
        {**item, "amount": _number(item["amount"])}
        for item in sorted(values.values(), key=lambda item: item["amount"], reverse=True)[:5]
    ]


def _cash_flow_category(root_type):
    return {"Asset": "investing", "Equity": "financing", "Liability": "financing"}.get(
        root_type, "operating"
    )


def _percent_change(current, previous):
    current = Decimal(str(current))
    previous = Decimal(str(previous))
    if not previous:
        return 0.0 if not current else None
    return _number((current - previous) / abs(previous) * 100)


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _months(start, end):
    current = start.replace(day=1)
    values = []
    while current <= end:
        values.append(current.strftime("%Y-%m"))
        current = current.replace(
            year=current.year + (current.month == 12),
            month=1 if current.month == 12 else current.month + 1,
        )
    return values


def _month_label(value):
    return date.fromisoformat(value + "-01").strftime("%b")


def _number(value):
    return float(Decimal(value).quantize(Decimal("0.01")))
