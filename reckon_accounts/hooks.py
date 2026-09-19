"""App registration; accounting controllers and postings remain with ERPNext."""

app_name = "reckon_accounts"
app_title = "Reckon Accounts"
app_publisher = "Reckon Technologies Ltd."
app_description = "Tally-oriented accounting reports and navigation for ERPNext"
app_logo_url = "/assets/reckon_accounts/images/reckon-accounts-icon.png"
app_icon_url = app_logo_url
app_icon_title = "Reckon Accounts"
app_icon_route = "/desk/reckon-accounts"

add_to_apps_screen = [
    {
        "name": app_name,
        "logo": app_logo_url,
        "title": app_title,
        "route": app_icon_route,
        "desk_route": app_icon_route,
        "has_permission": "reckon_accounts.api.check_app_permission",
        "sequence_id": 20,
    }
]

required_apps = ["erpnext"]
after_install = "reckon_accounts.access_control.setup_roles_and_permissions"
after_migrate = ["reckon_accounts.access_control.setup_roles_and_permissions"]

# Extend the standard form without changing ERPNext source files.
doctype_js = {"Payment Entry": "public/js/payment_entry.js"}
