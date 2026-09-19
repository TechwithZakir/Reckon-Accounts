"""Keep the Frappe 16 workspace desktop icon and its custom image in sync."""

import frappe

LABEL = "Reckon Accounts"
ICON_URL = "/assets/reckon_accounts/images/reckon-accounts-icon.png"


def execute():
    if not frappe.db.exists("DocType", "Desktop Icon"):
        return

    meta = frappe.get_meta("Desktop Icon")
    fields = {field.fieldname for field in meta.fields}
    values = {
        "icon_type": "Link",
        "link_type": "Workspace Sidebar",
        "link_to": LABEL,
        "link": None,
        "logo_url": ICON_URL,
        "icon_image": ICON_URL,
        "hidden": 0,
        "standard": 0,
        "app": None,
        "restrict_removal": 1,
        "parent_icon": None,
        "sidebar": None,
    }
    values = {field: value for field, value in values.items() if field in fields}

    if frappe.db.exists("Desktop Icon", LABEL):
        frappe.db.set_value("Desktop Icon", LABEL, values, update_modified=False)
    else:
        frappe.get_doc({"doctype": "Desktop Icon", "label": LABEL, **values}).insert()

    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_key("bootinfo")
