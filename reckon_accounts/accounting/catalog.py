"""Custom Tally-style views; standard financial statements stay in ERPNext."""

BOOK_REPORTS = {
    "Day Book": "vouchers",
    "Cash Book": "cash",
    "Bank Book": "bank",
    "Cash Bank Summary": "cash_bank_summary",
    "Bank Summary": "bank_summary",
    "Ledger Monthly Summary": "monthly",
    "Group Summary": "group_summary",
    "Group Monthly Summary": "group_monthly",
    "Group Vouchers": "group_vouchers",
    "Receipt Register": "receipt",
    "Payment Register": "payment",
    "Contra Register": "contra",
    "Journal Register": "journal",
    "Debit Note Register": "debit_note",
    "Credit Note Register": "credit_note",
    "Voucher Statistics": "statistics",
    "Receipts and Payments": "receipts_payments",
    "Negative Cash": "negative_cash",
    "Ledger Exceptions": "exceptions",
    "Funds Flow": "funds_flow",
}

VOUCHER_VIEWS = {
    "vouchers",
    "group_vouchers",
    "receipt",
    "payment",
    "contra",
    "journal",
    "debit_note",
    "credit_note",
    "statistics",
}
ACCOUNT_TYPES = {
    "cash": {"Cash"},
    "bank": {"Bank"},
    "negative_cash": {"Cash"},
    "cash_bank_summary": {"Cash", "Bank"},
    "bank_summary": {"Bank"},
    "receipts_payments": {"Cash", "Bank"},
}
SOURCE_LABELS = {
    "receipt": {"Receipt"},
    "payment": {"Payment"},
    "contra": {"Contra"},
    "journal": {"Journal Entry"},
    "debit_note": {"Debit Note"},
    "credit_note": {"Credit Note"},
}
