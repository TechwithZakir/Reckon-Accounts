{% include "reckon_accounts/public/js/report_filters.js" %}
frappe.query_reports["Receipts and Payments"] = reckon_accounts.report_settings("Receipts and Payments");
