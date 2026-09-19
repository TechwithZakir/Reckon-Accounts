"""App registration; accounting controllers and postings remain with ERPNext."""

app_name = "reckon_accounts"
app_title = "Reckon Accounts"
app_publisher = "Reckon Technologies Ltd."
app_description = "Tally-oriented accounting reports and navigation for ERPNext"

required_apps = ["erpnext"]

# Extend the standard form without changing ERPNext source files.
doctype_js = {"Payment Entry": "public/js/payment_entry.js"}
