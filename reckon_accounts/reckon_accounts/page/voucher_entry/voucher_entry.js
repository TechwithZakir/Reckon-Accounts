frappe.pages["voucher-entry"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __("Voucher Entry"), single_column: true});
    const company = page.add_field({fieldname: "company", label: __("Company"),
        fieldtype: "Link", options: "Company", reqd: 1,
        default: frappe.defaults.get_user_default("Company")});
    const date = page.add_field({fieldname: "posting_date", label: __("Posting Date"),
        fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()});
    const entries = [
        ["F4", "Contra", "Payment Entry", {payment_type: "Internal Transfer"}],
        ["F5", "Payment", "Payment Entry", {payment_type: "Pay"}],
        ["F6", "Receipt", "Payment Entry", {payment_type: "Receive"}],
        ["F7", "Journal", "Journal Entry", {voucher_type: "Journal Entry"}],
        ["F8", "Sales", "Sales Invoice", {}],
        ["F9", "Purchase", "Purchase Invoice", {}],
    ];
    const body = $("<div class='p-4'></div>").appendTo(page.main);
    $("<p class='text-muted'></p>").text(__("Choose a voucher to open a new entry. Review, save and submit in the entry form.")).appendTo(body);
    const grid = $("<div></div>").css({display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px"}).appendTo(body);
    const actions = {};
    for (const [key, label, doctype, defaults] of entries) {
        const open = () => {
            if (!frappe.model.can_create(doctype)) return frappe.msgprint(__("You do not have permission to create this voucher."));
            if (!company.get_value() || !date.get_value()) return frappe.msgprint(__("Select Company and Posting Date."));
            frappe.new_doc(doctype, {...defaults, company: company.get_value(), posting_date: date.get_value()});
        };
        actions[key] = open;
        $("<button type='button' class='btn btn-default p-4 text-left'></button>")
            .text(key + " · " + __(label)).prop("disabled", !frappe.model.can_create(doctype))
            .on("click", open).appendTo(grid);
    }
    page.add_inner_button(__("Day Book"), () => {
        frappe.route_options = {company: company.get_value(), from_date: date.get_value(), to_date: date.get_value()};
        frappe.set_route("query-report", "Day Book");
    });
    // One namespaced handler, active only on this route and outside dialogs.
    $(document).off("keydown.reckonVoucherEntry").on("keydown.reckonVoucherEntry", event => {
        if (frappe.get_route()[0] !== "voucher-entry" || $(".modal:visible").length ||
            event.ctrlKey || event.altKey || event.metaKey || event.shiftKey || event.repeat) return;
        if (actions[event.key]) {
            event.preventDefault();
            event.stopImmediatePropagation();
            actions[event.key]();
        }
    });
};
