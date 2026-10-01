"""Version-compatible Payment Entry metadata customizations."""

import json

import frappe

THREE_COLUMN_BREAKS = (
    ("custom_column_break_payment_header", "mode_of_payment"),
    ("custom_column_break_party", "contact_email"),
    ("custom_column_break_accounts", "paid_to_account_currency"),
    ("custom_column_break_amount", "received_amount"),
    ("custom_column_break_writeoff", "unallocated_amount"),
    ("custom_column_break_transaction", "reference_date"),
    ("custom_column_break_dimensions", "cost_center"),
    ("custom_column_break_more_information", "print_heading"),
)


def configure_payment_entry():
    """Sync the Payment Entry field order and three-column section breaks."""
    if not frappe.db.exists("DocType", "Payment Entry"):
        return

    meta = frappe.get_meta("Payment Entry", cached=False)
    field_order = [field.fieldname for field in meta.fields]
    if "remarks" not in field_order or "mode_of_payment" not in field_order:
        return

    _move_after(field_order, "custom_voucher_subtype", "payment_type")
    _move_after(field_order, "custom_column_break_payment_header", "mode_of_payment")
    _move_after(field_order, "remarks", "custom_column_break_payment_header")
    for fieldname, anchor in THREE_COLUMN_BREAKS[1:]:
        _move_after(field_order, fieldname, anchor)
    _move_after(
        field_order,
        "book_advance_payments_in_separate_party_account",
        "custom_column_break_party",
    )
    _move_after(
        field_order,
        "reconcile_on_advance_payment_date",
        "book_advance_payments_in_separate_party_account",
    )
    _move_after(field_order, "apply_tds", "reconcile_on_advance_payment_date")
    frappe.make_property_setter(
        {
            "doctype": "Payment Entry",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Small Text",
            "value": json.dumps(field_order),
        },
        is_system_generated=False,
    )
    frappe.clear_cache(doctype="Payment Entry")


def _move_after(field_order, fieldname, anchor):
    """Place an optional custom field after its anchor without breaking older sites."""
    if fieldname not in field_order or anchor not in field_order:
        return
    field_order.remove(fieldname)
    field_order.insert(field_order.index(anchor) + 1, fieldname)
