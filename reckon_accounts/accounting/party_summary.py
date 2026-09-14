"""Party/account balances with permission-checked master classifications."""

import json

from reckon_accounts.accounting.balances import Balance
from reckon_accounts.accounting.books import BookResult, row

CLASSIFICATIONS = {
    "customer_group": ("Customer", "Customer Group"),
    "supplier_group": ("Supplier", "Supplier Group"),
    "territory": ("Customer", "Territory"),
}


def summarize(ledger, permissions, options, *, page=1):
    grouping = options.get("group_by") or "Party"
    if grouping not in {"Party", "Party Type", "Account Head", *CLASSIFICATIONS}:
        raise ValueError("Unsupported Party Summary grouping")
    for field, (_, doctype) in CLASSIFICATIONS.items():
        if options.get(field):
            permissions.require(doctype, options[field])
    groups = {}
    for section in ledger.sections:
        _, party_type, party = section.key
        values = {}
        for field, (owner, doctype) in CLASSIFICATIONS.items():
            if not options.get(field) and grouping != field:
                continue
            value = None
            if party_type == owner and party:
                master = permissions.require(owner, party)
                if field not in master:
                    raise ValueError("Party classification field is unavailable or not readable")
                value = master[field]
                if value:
                    permissions.require(doctype, value)
            values[field] = value
        if any(
            options.get(field) and values.get(field) != options[field] for field in CLASSIFICATIONS
        ):
            continue
        key = (
            section.key
            if grouping == "Party"
            else (
                party_type
                if grouping == "Party Type"
                else section.account
                if grouping == "Account Head"
                else values.get(grouping) or "Unclassified"
            )
        )
        if key not in groups:
            groups[key] = row(
                ledger,
                "party_summary" if grouping == "Party" else "summary_group",
                section.party_heading if grouping == "Party" else str(key),
                account=section.account if grouping in {"Party", "Account Head"} else "",
                party_type=party_type if grouping == "Party" else "",
                party=party if grouping == "Party" else "",
                party_name=section.party_heading if grouping == "Party" else "",
                opening=0,
                opening_debit=0,
                opening_credit=0,
                debit=0,
                credit=0,
                balance=0,
                balance_debit=0,
                balance_credit=0,
                receivable=0,
                payable=0,
            )
        target = groups[key]
        for field, amount in {
            "opening": section.opening,
            "opening_debit": Balance(section.opening).debit,
            "opening_credit": Balance(section.opening).credit,
            "debit": section.debit,
            "credit": section.credit,
            "balance": section.closing,
            "balance_debit": Balance(section.closing).debit,
            "balance_credit": Balance(section.closing).credit,
            "receivable": Balance(section.closing).debit,
            "payable": Balance(section.closing).credit,
        }.items():
            target[field] += amount
        target["balance_type"] = Balance(target["balance"]).balance_type
    result = BookResult(
        ledger,
        tuple((value,) for value in groups.values()),
        "Permitted GL balances; receivable/payable columns are debit/credit balances, "
        "not bill-wise outstanding. Classification selections match exact masters. "
        "Summary filters: " + json.dumps(options),
        page,
    )
    if page > result.total_pages:
        raise ValueError("Page exceeds available summary groups")
    return result
