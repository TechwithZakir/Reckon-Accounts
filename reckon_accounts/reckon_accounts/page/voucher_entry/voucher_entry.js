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

    const list_grid = $("<div class='mt-2'></div>").css({display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px"}).appendTo(body);
    for (const [, label, doctype, defaults] of entries) {
        const open_list = () => {
            if (!frappe.model.can_read(doctype)) {
                return frappe.msgprint(__("You do not have permission to view these vouchers."));
            }
            frappe.route_options = {...defaults};
            if (company.get_value()) frappe.route_options.company = company.get_value();
            frappe.set_route("List", doctype, "List");
        };
        $("<button type='button' class='btn btn-link text-left'></button>")
            .text(__(label + " List"))
            .prop("disabled", !frappe.model.can_read(doctype))
            .on("click", open_list)
            .appendTo(list_grid);
    }

    $("<h4 class='mt-5 mb-3'></h4>").text(__("Today's Activity")).appendTo(body);
    const counts = $("<div></div>").css({display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px"}).appendTo(body);
    const count_cards = [
        ["Payment Entry", {payment_type: "Receive"}, "Receipts"],
        ["Payment Entry", {payment_type: "Pay"}, "Payments"],
        ["Journal Entry", {}, "Journals"],
        ["Sales Invoice", {}, "Sales Invoices"],
        ["Purchase Invoice", {}, "Purchase Invoices"],
    ];
    const refresh_counts = async () => {
        counts.empty();
        for (const [doctype, extra, label] of count_cards) {
            if (!frappe.model.can_read(doctype)) continue;
            const filters = {company: company.get_value(), posting_date: date.get_value(), docstatus: ["<", 2], ...extra};
            let value = "—";
            try { value = await frappe.db.count(doctype, {filters}); } catch (error) {
                console.warn("Reckon Accounts count unavailable", doctype, error);
            }
            $("<div class='card p-3'></div>").append(
                $("<div class='text-muted small'></div>").text(__(label)),
                $("<div class='h3 mb-0'></div>").text(value),
            ).appendTo(counts);
        }
    };
    company.$input.on("change.reckonVoucherEntry", refresh_counts);
    date.$input.on("change.reckonVoucherEntry", refresh_counts);
    refresh_counts();

    $("<h4 class='mt-5 mb-3'></h4>").text(__("Reports")).appendTo(body);
    const reports = $("<div></div>").css({display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "10px"}).appendTo(body);
    const report_names = ["Day Book", "Cash Book", "Bank Book", "Party Ledger",
        "General Ledger Custom", "Payment Register", "Receipt Register", "Trial Balance",
        "Balance Sheet", "Profit and Loss Statement", "Trial Balance for Party",
        "Item-wise Sales Register", "Item-wise Purchase Register", "Sales Register", "Purchase Register"];
    for (const report_name of report_names) {
        $("<button type='button' class='btn btn-default text-left'></button>").text(__(report_name))
            .on("click", () => {
                frappe.route_options = {company: company.get_value(),
                    from_date: date.get_value(), to_date: date.get_value()};
                frappe.set_route("query-report", report_name);
            }).appendTo(reports);
    }
    $("<button type='button' class='btn btn-default text-left'></button>")
        .text(__("Financial Reports (ERPNext)"))
        .on("click", () => frappe.set_route("accounting"))
        .appendTo(reports);
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
