"""Version-compatible Payment Entry metadata customizations."""

import json

import frappe


def configure_payment_entry():
    """Place standard Remarks after Mode of Payment without client-side layout code."""
    if not frappe.db.exists("DocType", "Payment Entry"):
        return

    meta = frappe.get_meta("Payment Entry", cached=False)
    field_order = [field.fieldname for field in meta.fields]
    if "remarks" not in field_order or "mode_of_payment" not in field_order:
        return

    field_order.remove("remarks")
    field_order.insert(field_order.index("mode_of_payment") + 1, "remarks")
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
