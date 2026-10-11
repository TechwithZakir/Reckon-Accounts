"""Permission-aware distribution analytics for the distribution workspace."""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

MAX_ROWS = 5000
BUCKETS = (
    ("0 - 30 Days", 0, 30),
    ("31 - 60 Days", 31, 60),
    ("61 - 90 Days", 61, 90),
    ("> 90 Days", 91, None),
)


def build_distribution_dashboard(frappe, filters):
    company = filters["company"]
    start = _as_date(filters["from_date"])
    end = _as_date(filters["to_date"])
    if start > end:
        raise ValueError("From Date cannot be after To Date")
    frappe.has_permission("Company", "read", company, throw=True)
    currency = frappe.db.get_value("Company", company, "default_currency") or "BDT"

    sales = _list_documents(frappe, "Sales Invoice", company, start, end)
    deliveries = _list_documents(frappe, "Delivery Note", company, start, end)
    purchases = _list_documents(frappe, "Purchase Receipt", company, start, end)
    purchase_invoices = _list_documents(
        frappe, "Purchase Invoice", company, None, end
    )
    gl = _gl_summary(frappe, company, start, end)

    posted_sales = [item for item in sales if _posted(item)]
    posted_deliveries = [item for item in deliveries if _posted(item)]
    posted_purchases = [item for item in purchases if _posted(item)]
    sales_total = _total(posted_sales, ("base_grand_total", "grand_total"), signed=True)
    delivery_total = _total(posted_deliveries, ("base_grand_total", "grand_total"), signed=True)
    purchase_total = _total(posted_purchases, ("base_grand_total", "grand_total"), signed=True)
    receivables = _aging_rows(sales, end)
    payables = _aging_rows(purchase_invoices, end)
    profit = gl["income"] - gl["expenses"]

    return {
        "currency": currency,
        "period": {"from_date": start.isoformat(), "to_date": end.isoformat()},
        "kpis": {
            "sales": _number(sales_total),
            "sales_count": len(posted_sales),
            "deliveries": _number(delivery_total),
            "delivery_count": len(posted_deliveries),
            "purchases": _number(purchase_total),
            "purchase_count": len(posted_purchases),
            "expenses": _number(gl["expenses"]),
            "profit": _number(profit),
            "loss": _number(abs(profit) if profit < 0 else 0),
            "receivables": _number(sum(item["amount"] for item in receivables)),
            "payables": _number(sum(item["amount"] for item in payables)),
        },
        "trend": _trend(start, end, posted_sales, posted_deliveries, posted_purchases, gl),
        "sales_reps": _sales_rep_totals(frappe, posted_sales),
        "top_customers": _group_totals(
            posted_sales, ("customer_name", "customer"), ("base_grand_total", "grand_total")
        ),
        "top_suppliers": _group_totals(
            posted_purchases, ("supplier_name", "supplier"), ("base_grand_total", "grand_total")
        ),
        "delivery_status": _status_totals(deliveries),
        "sales_status": _status_totals(sales),
        "purchase_status": _status_totals(purchases),
        "receivables_aging": _aging_summary(receivables),
        "payables_aging": _aging_summary(payables),
        "recent_sales": _recent(posted_sales, "customer_name", "customer", "Sales Invoice"),
        "recent_deliveries": _recent(posted_deliveries, "customer_name", "customer", "Delivery Note"),
    }


def _list_documents(frappe, doctype, company, start, end):
    if not _readable(frappe, doctype):
        return []
    meta = frappe.get_meta(doctype)
    available = {field.fieldname for field in meta.fields}
    requested = {
        "name", "posting_date", "due_date", "docstatus", "status", "is_return",
        "customer", "customer_name", "supplier", "supplier_name", "grand_total",
        "base_grand_total", "outstanding_amount", "paid_amount", "total_qty",
        "per_billed", "per_delivered", "sales_person", "custom_sales_person",
        "custom_sr", "custom_dsr", "sales_representative", "creation",
    }
    fields = sorted((requested & available) | {"name", "posting_date"})
    conditions = {"company": company}
    if "posting_date" not in available:
        return []
    if start is not None:
        conditions["posting_date"] = ["between", [start, end]]
    else:
        conditions["posting_date"] = ["<=", end]
    return frappe.get_list(
        doctype,
        fields=fields,
        filters=conditions,
        order_by="posting_date desc, creation desc",
        limit_page_length=MAX_ROWS,
        ignore_permissions=False,
    )


def _gl_summary(frappe, company, start, end):
    empty = {"income": Decimal(0), "expenses": Decimal(0), "months": defaultdict(dict)}
    if not _readable(frappe, "GL Entry"):
        return empty
    rows = frappe.get_list(
        "GL Entry",
        fields=["name", "posting_date", "account", "debit", "credit", "is_cancelled"],
        filters={
            "company": company,
            "posting_date": ["between", [start, end]],
            "is_cancelled": 0,
        },
        order_by="posting_date asc, name asc",
        limit_page_length=MAX_ROWS,
        ignore_permissions=False,
    )
    accounts = {
        item["name"]: item
        for item in frappe.get_list(
            "Account",
            fields=["name", "root_type", "account_name", "account_type"],
            filters={"name": ["in", sorted({row["account"] for row in rows})]},
            limit_page_length=MAX_ROWS,
            ignore_permissions=False,
        )
    } if rows and _readable(frappe, "Account") else {}
    result = {"income": Decimal(0), "expenses": Decimal(0), "months": defaultdict(dict)}
    for row in rows:
        account = accounts.get(row["account"], {})
        month = _as_date(row["posting_date"]).strftime("%Y-%m")
        debit = _decimal(row.get("debit"))
        credit = _decimal(row.get("credit"))
        if account.get("root_type") == "Income":
            amount = credit - debit
            result["income"] += amount
            result["months"].setdefault(month, {}).setdefault("income", Decimal(0))
            result["months"][month]["income"] += amount
        elif account.get("root_type") == "Expense":
            amount = debit - credit
            result["expenses"] += amount
            result["months"].setdefault(month, {}).setdefault("expenses", Decimal(0))
            result["months"][month]["expenses"] += amount
    return result


def _trend(start, end, sales, deliveries, purchases, gl):
    months = []
    current = start.replace(day=1)
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        current = current.replace(
            year=current.year + (current.month == 12),
            month=1 if current.month == 12 else current.month + 1,
        )
    rows = []
    for month in months:
        item = gl["months"].get(month, {})
        rows.append({
            "month": month,
            "label": _month_label(month),
            "sales": _number(_month_total(sales, month)),
            "deliveries": _number(_month_total(deliveries, month)),
            "purchases": _number(_month_total(purchases, month)),
            "expenses": _number(item.get("expenses", 0)),
            "profit": _number(item.get("income", 0) - item.get("expenses", 0)),
        })
    return rows


def _sales_rep_totals(frappe, invoices):
    totals = defaultdict(Decimal)
    direct_fields = ("custom_dsr", "custom_sr", "sales_representative", "custom_sales_person", "sales_person")
    for invoice in invoices:
        representative = next((invoice.get(field) for field in direct_fields if invoice.get(field)), None)
        if representative:
            totals[str(representative)] += _signed(invoice, ("base_grand_total", "grand_total"))
    if not totals and invoices and _readable(frappe, "Sales Team"):
        rows = frappe.get_list(
            "Sales Team",
            fields=["parent", "sales_person", "allocated_percentage"],
            filters={"parent": ["in", [item["name"] for item in invoices]], "parenttype": "Sales Invoice"},
            limit_page_length=MAX_ROWS,
            ignore_permissions=False,
        )
        by_invoice = defaultdict(list)
        for row in rows:
            if row.get("sales_person"):
                by_invoice[row["parent"]].append(row)
        for invoice in invoices:
            for row in by_invoice.get(invoice["name"], []):
                share = _decimal(row.get("allocated_percentage")) / 100
                totals[row["sales_person"]] += _signed(invoice, ("base_grand_total", "grand_total")) * share
    return _ranked(totals)


def _aging_rows(rows, as_of):
    result = []
    for row in rows:
        if not _posted(row):
            continue
        amount = _decimal(row.get("outstanding_amount"))
        if not amount:
            amount = _signed(row, ("base_grand_total", "grand_total")) - _decimal(row.get("paid_amount"))
        amount = abs(amount)
        if not amount:
            continue
        due = _as_date(row.get("due_date") or row.get("posting_date"))
        result.append({"amount": amount, "days": max(0, (as_of - due).days)})
    return result


def _aging_summary(rows):
    values = [{"label": label, "amount": Decimal(0), "count": 0} for label, _, _ in BUCKETS]
    for row in rows:
        for index, (_, low, high) in enumerate(BUCKETS):
            if row["days"] >= low and (high is None or row["days"] <= high):
                values[index]["amount"] += row["amount"]
                values[index]["count"] += 1
                break
    total = sum(item["amount"] for item in values)
    return [
        {**item, "amount": _number(item["amount"]), "percentage": _number(item["amount"] / total * 100) if total else 0}
        for item in values
    ]


def _group_totals(rows, name_fields, amount_fields):
    totals = defaultdict(Decimal)
    for row in rows:
        name = next((row.get(field) for field in name_fields if row.get(field)), "Unassigned")
        totals[str(name)] += _signed(row, amount_fields)
    return _ranked(totals)


def _ranked(values, limit=5):
    return [{"name": name, "amount": _number(amount)} for name, amount in sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _status_totals(rows):
    counts = Counter((row.get("status") or ("Submitted" if _posted(row) else "Draft")) for row in rows)
    return [{"label": label, "count": count} for label, count in counts.most_common()]


def _recent(rows, name_field, fallback_field, doctype):
    result = []
    for row in rows[:8]:
        result.append({
            "date": str(row.get("posting_date")),
            "name": row.get("name"),
            "doctype": doctype,
            "party": row.get(name_field) or row.get(fallback_field) or "-",
            "amount": _number(_signed(row, ("base_grand_total", "grand_total"))),
            "status": row.get("status") or "Submitted",
        })
    return result


def _month_total(rows, month):
    return sum((_signed(row, ("base_grand_total", "grand_total")) for row in rows if _as_date(row["posting_date"]).strftime("%Y-%m") == month), Decimal(0))


def _total(rows, fields, signed=False):
    return sum((_signed(row, fields) if signed else _decimal(row.get(fields[0])) for row in rows), Decimal(0))


def _signed(row, fields):
    value = next((_decimal(row.get(field)) for field in fields if row.get(field) not in (None, "")), Decimal(0))
    return -value if row.get("is_return") else value


def _decimal(value):
    return Decimal(str(value or 0))


def _number(value):
    return float(_decimal(value).quantize(Decimal("0.01")))


def _posted(row):
    return int(row.get("docstatus") or 0) == 1


def _readable(frappe, doctype):
    return bool(frappe.db.exists("DocType", doctype)) and frappe.has_permission(doctype, "read")


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _month_label(month):
    return date.fromisoformat(month + "-01").strftime("%b")
