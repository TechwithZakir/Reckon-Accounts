"""Repair the Frappe 16 desktop icon created from the workspace."""

import frappe

LABEL = "Reckon Accounts"
APP_NAME = "reckon_accounts"
APP_ROUTE = "/desk/reckon-accounts"
ICON_URL = "/assets/reckon_accounts/images/reckon-accounts-icon.png"


def execute():
    if not frappe.db.exists("DocType", "Desktop Icon"):
        return

    meta = frappe.get_meta("Desktop Icon")
    fields = {field.fieldname for field in meta.fields}
    values = {
        "icon_type": "App",
        "link_type": "External",
        "link": APP_ROUTE,
        "logo_url": ICON_URL,
        "icon_image": ICON_URL,
        "hidden": 0,
        # Frappe creates add_to_apps_screen icons as non-standard database records.
        # Marking this as standard without a desktop_icon JSON file lets sync remove it.
        "standard": 0,
        "app": APP_NAME,
        "restrict_removal": 1,
        "parent_icon": None,
        "link_to": None,
        "sidebar": None,
    }
    values = {field: value for field, value in values.items() if field in fields}

    if frappe.db.exists("Desktop Icon", LABEL):
        frappe.db.set_value("Desktop Icon", LABEL, values, update_modified=False)
    else:
        frappe.get_doc({"doctype": "Desktop Icon", "label": LABEL, **values}).insert()

    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_key("bootinfo")
