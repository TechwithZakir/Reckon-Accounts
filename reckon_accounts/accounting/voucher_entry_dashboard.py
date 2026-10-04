"""Permission-aware analytics for the Voucher Entry workspace page."""

from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

VOUCHER_TYPES = (
    ("Payment Entry", "Contra", "contras"),
    ("Payment Entry", "Payment", "payments"),
    ("Payment Entry", "Receipt", "receipts"),
    ("Journal Entry", "Journal", "journals"),
    ("Sales Invoice", "Sales", "sales"),
    ("Purchase Receipt", "Purchase Receipt", "purchases"),
)


def build_voucher_entry_dashboard(frappe, filters):
    """Build voucher analytics using only permission-aware list queries."""
    company = filters["company"]
    start = _as_date(filters["from_date"])
    end = _as_date(filters["to_date"])
    records = []
    by_type = defaultdict(list)

    for doctype, label, key in VOUCHER_TYPES:
        if not frappe.has_permission(doctype, "read"):
            continue
        rows = _list_vouchers(frappe, doctype, company, start, end)
        for row in rows:
            if doctype == "Payment Entry" and not _payment_entry_matches(label, row):
                continue
            item = {
                "doctype": doctype,
                "label": label,
                "key": key,
                "name": row.get("name"),
                "date": _as_date(row.get("posting_date")),
                "owner": row.get("owner") or "Unknown",
                "docstatus": int(row.get("docstatus") or 0),
                "status": row.get("status") or "",
                "source": _source(row),
                "amount": _amount(doctype, row),
                "reference": row.get("reference_no") or row.get("cheque_no") or "",
            }
            records.append(item)
            by_type[key].append(item)

    activity = _activity(records, end)
    trend = _trend(records, start, end)
    distribution = [
        {
            "label": label,
            "key": key,
            "count": len(by_type[key]),
            "amount": _number(sum(item["amount"] for item in by_type[key])),
        }
        for _, label, key in VOUCHER_TYPES
        if by_type[key]
    ]
    sources = _counts(item["source"] for item in records)
    users = _counts(item["owner"] for item in records)
    pending = _pending(records)

    return {
        "period": {"from_date": start.isoformat(), "to_date": end.isoformat()},
        "activity": activity,
        "trend": trend,
        "distribution": distribution,
        "sources": sources,
        "users": users[:5],
        "pending": pending,
        "attention": {
            "drafts": pending["drafts"],
            "pending_approval": pending["pending_approval"],
            "missing_reference": sum(
                item["doctype"] == "Payment Entry" and not item["reference"] for item in records
            ),
            "duplicates": 0,
        },
        "recent_accounts": _recent_accounts(frappe, company, start, end),
    }


def _list_vouchers(frappe, doctype, company, start, end):
    meta = frappe.get_meta(doctype)
    fields = {field.fieldname for field in meta.fields}
    requested = {
        "name",
        "posting_date",
        "owner",
        "docstatus",
        "payment_type",
        "status",
        "source",
        "entry_source",
        "imported_from",
        "reference_no",
        "cheque_no",
        "paid_amount",
        "received_amount",
        "base_paid_amount",
        "base_received_amount",
        "grand_total",
        "base_grand_total",
        "total_debit",
        "total_credit",
    }
    selected = sorted((requested & fields) | {"name", "posting_date"})
    return frappe.get_list(
        doctype,
        fields=selected,
        filters={"company": company, "posting_date": ["between", [start, end]]},
        order_by="posting_date desc, creation desc",
        limit_page_length=5000,
        ignore_permissions=False,
    )


def _recent_accounts(frappe, company, start, end):
    if not frappe.has_permission("GL Entry", "read"):
        return []
    rows = frappe.get_list(
        "GL Entry",
        fields=["account"],
        filters={"company": company, "posting_date": ["between", [start, end]], "is_cancelled": 0},
        limit_page_length=5000,
        ignore_permissions=False,
    )
    counts = Counter(row.get("account") for row in rows if row.get("account"))
    names = list(counts)
    details = {}
    if names and frappe.has_permission("Account", "read"):
        details = {
            row["name"]: row
            for row in frappe.get_list(
                "Account",
                fields=["name", "account_type", "root_type"],
                filters={"name": ["in", names]},
                limit_page_length=min(len(names), 5000),
                ignore_permissions=False,
            )
        }
    return [
        {
            "account": account,
            "name": account,
            "type": details.get(account, {}).get("account_type")
            or details.get(account, {}).get("root_type")
            or "Account",
            "uses": count,
        }
        for account, count in counts.most_common(5)
    ]


def _activity(records, day):
    selected = [item for item in records if item["date"] == day]
    return {
        key: {
            "count": sum(item["key"] == key and item["docstatus"] != 2 for item in selected),
            "amount": _number(sum(item["amount"] for item in selected if item["key"] == key)),
        }
        for _, _, key in VOUCHER_TYPES
    }


def _trend(records, start, end):
    days = (end - start).days + 1
    if days > 31:
        step = max(1, days // 31)
        dates = [start + timedelta(days=index * step) for index in range((days + step - 1) // step)]
        dates[-1] = end
        buckets = [(day, min(end, day + timedelta(days=step - 1))) for day in dates]
    else:
        buckets = [(day, day) for day in (start + timedelta(days=index) for index in range(days))]
    return [
        {
            "date": bucket_start.isoformat(),
            "label": bucket_start.strftime("%d %b"),
            **{
                key: sum(
                    item["key"] == key
                    and item["docstatus"] != 2
                    and bucket_start <= item["date"] <= bucket_end
                    for item in records
                )
                for _, _, key in VOUCHER_TYPES
            },
        }
        for bucket_start, bucket_end in buckets
    ]


def _counts(values):
    counts = Counter(values)
    total = sum(counts.values())
    return [
        {"label": label, "count": count, "percentage": _number(count / total * 100) if total else 0.0}
        for label, count in counts.most_common()
    ]


def _pending(records):
    drafts = [item for item in records if item["docstatus"] == 0]
    pending_approval = [item for item in records if "pending" in item["status"].lower()]
    on_hold = [item for item in records if "hold" in item["status"].lower()]
    cancelled = [item for item in records if item["docstatus"] == 2]
    return {
        "drafts": len(drafts),
        "pending_approval": len(pending_approval),
        "on_hold": len(on_hold),
        "cancelled": len(cancelled),
    }


def _amount(doctype, row):
    fields = {
        "Payment Entry": ("base_paid_amount", "base_received_amount", "paid_amount", "received_amount"),
        "Sales Invoice": ("base_grand_total", "grand_total"),
        "Purchase Receipt": ("base_grand_total", "grand_total"),
        "Journal Entry": ("total_debit", "total_credit"),
    }[doctype]
    for field in fields:
        if row.get(field) not in (None, ""):
            return Decimal(str(row[field]))
    return Decimal(0)


def _payment_entry_matches(label, row):
    return {
        "Contra": "Internal Transfer",
        "Payment": "Pay",
        "Receipt": "Receive",
    }[label] == row.get("payment_type")


def _source(row):
    for field in ("source", "entry_source", "imported_from"):
        if row.get(field):
            return str(row[field])
    return "Manual Entry"


def _as_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _number(value):
    return float(Decimal(value).quantize(Decimal("0.01")))
