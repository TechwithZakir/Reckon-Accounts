"""Enrichment from already-permitted field dictionaries only."""


def party_name(record, meta):
    title_field = meta.title_field
    return str(record.get(title_field) or record["name"]) if title_field else record["name"]


def voucher_label(doctype, record):
    if doctype == "Journal Entry" and record.get("voucher_type") in (
        "Debit Note",
        "Credit Note",
        "Contra Entry",
    ):
        return {"Contra Entry": "Contra"}.get(record["voucher_type"], record["voucher_type"])
    if doctype == "Payment Entry":
        return {"Receive": "Receipt", "Pay": "Payment", "Internal Transfer": "Contra"}.get(
            record.get("payment_type"), doctype
        )
    if record.get("is_return"):
        return {"Sales Invoice": "Credit Note", "Purchase Invoice": "Debit Note"}.get(
            doctype, doctype
        )
    return doctype


def permitted_particulars(row, peers, account_titles=None):
    """Do not expose raw `against`, which may name inaccessible accounts.

    Peers are permission-checked GL lines in the current balance scope. A full
    source voucher remains the drill-down; no pairwise allocation is invented.
    """
    accounts = sorted({peer["account"] for peer in peers if peer["account"] != row["account"]})
    if not accounts:
        return "See permitted source voucher"
    if len(accounts) == 1:
        return (account_titles or {}).get(accounts[0], accounts[0]) + " (within report scope)"
    return "Multiple Accounts (within report scope)"
