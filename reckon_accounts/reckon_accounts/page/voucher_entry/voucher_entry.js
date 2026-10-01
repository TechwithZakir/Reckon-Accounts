frappe.pages["voucher-entry"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __("Voucher Entry"), single_column: true});
    const company = page.add_field({fieldname: "company", label: __("Company"), fieldtype: "Link",
        options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")});
    const from_date = page.add_field({fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
        reqd: 1, default: frappe.datetime.get_today()});
    const to_date = page.add_field({fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
        reqd: 1, default: frappe.datetime.get_today()});
    const body = $("<main class='reckon-voucher-page'></main>").appendTo(page.main);

    const escape = value => frappe.utils.escape_html(String(value ?? ""));
    const money = value => new Intl.NumberFormat(undefined, {
        style: "currency", currency: "BDT", maximumFractionDigits: 0,
    }).format(Number(value || 0));
    const entries = [
        {key: "F4", label: "Contra", description: "New Contra Entry", icon: "<>", tone: "green", doctype: "Payment Entry", defaults: {payment_type: "Internal Transfer"}},
        {key: "F5", label: "Payment", description: "New Payment Entry", icon: "$", tone: "red", doctype: "Payment Entry", defaults: {payment_type: "Pay", custom_voucher_subtype: "Direct Expense"}},
        {key: "F6", label: "Receipt", description: "New Receipt Entry", icon: "&#8595;", tone: "teal", doctype: "Payment Entry", defaults: {payment_type: "Receive", custom_voucher_subtype: "Direct Income"}},
        {key: "F7", label: "Journal", description: "New Journal Entry", icon: "=", tone: "blue", doctype: "Journal Entry", defaults: {voucher_type: "Journal Entry"}},
        {key: "F8", label: "Sales", description: "New Sales Entry", icon: "&#9632;", tone: "orange", doctype: "Sales Invoice", defaults: {}},
        {key: "F9", label: "Purchase", description: "New Purchase Entry", icon: "&#9632;", tone: "purple", doctype: "Purchase Invoice", defaults: {}},
    ];
    const reports = ["Day Book", "Cash Book", "Bank Book", "Party Ledger", "General Ledger Custom", "Payment Register", "Receipt Register", "Trial Balance", "Balance Sheet", "Profit and Loss Statement", "Trial Balance for Party", "Item-wise Sales Register", "Item-wise Purchase Register", "Sales Register", "Purchase Register"];
    const actions = {};

    function openEntry(entry) {
        if (!frappe.model.can_create(entry.doctype)) return frappe.msgprint(__("You do not have permission to create this voucher."));
        if (!company.get_value() || !to_date.get_value()) return frappe.msgprint(__("Select Company and To Date."));
        frappe.new_doc(entry.doctype, {...entry.defaults, company: company.get_value(), posting_date: to_date.get_value()});
    }

    function openList(entry) {
        if (!frappe.model.can_read(entry.doctype)) return frappe.msgprint(__("You do not have permission to view these vouchers."));
        frappe.route_options = {company: company.get_value(), posting_date: ["between", [from_date.get_value(), to_date.get_value()]], ...entry.defaults};
        frappe.set_route("List", entry.doctype, "List");
    }

    function openReport(report) {
        frappe.route_options = {company: company.get_value(), from_date: from_date.get_value(), to_date: to_date.get_value()};
        frappe.set_route("query-report", report);
    }

    function entryCards() {
        return entries.map(entry => {
            const allowed = frappe.model.can_create(entry.doctype);
            actions[entry.key] = () => openEntry(entry);
            return `<button class='reckon-voucher-card reckon-tone-${entry.tone}' data-entry='${entry.key}' ${allowed ? "" : "disabled"}>` +
                `<span class='reckon-voucher-icon'>${entry.icon}</span><span><b>${escape(entry.key)} - ${escape(entry.label)}</b><small>${escape(entry.description)}</small></span></button>`;
        }).join("");
    }

    function listCards() {
        return entries.map(entry => `<button class='reckon-list-card' data-list='${entry.key}' ${frappe.model.can_read(entry.doctype) ? "" : "disabled"}>` +
            `<span class='reckon-list-icon'>&#9776;</span>${escape(entry.label)} List</button>`).join("");
    }

    function activityCards(data) {
        const cards = [
            ["receipts", "Receipts", "teal"], ["payments", "Payments", "red"], ["journals", "Journals", "blue"],
            ["sales", "Sales Invoices", "orange"], ["purchases", "Purchase Invoices", "purple"],
        ];
        return cards.map(([key, label, tone]) => `<article class='reckon-activity-card reckon-tone-${tone}'><span class='reckon-activity-icon'>${key.slice(0, 2).toUpperCase()}</span><div><small>${escape(label)}</small><strong>${escape(data.activity[key]?.count || 0)}</strong><b>${escape(money(data.activity[key]?.amount || 0))}</b></div></article>`).join("");
    }

    function trend(data) {
        const max = Math.max(1, ...data.flatMap(row => [row.contras, row.payments, row.receipts, row.journals, row.sales, row.purchases]));
        const series = [["contras", "Contra", "contra"], ["payments", "Payment", "payment"], ["receipts", "Receipt", "receipt"], ["journals", "Journal", "journal"], ["sales", "Sales", "sales"], ["purchases", "Purchase", "purchase"]];
        return `<section class='reckon-voucher-panel reckon-trend-panel'><header><h2>Voucher Volume Trend</h2><span class='reckon-voucher-legend'>${series.map(item => `<i class='${item[2]}'></i>${item[1]}`).join("")}</span></header>` +
            `<div class='reckon-trend-chart'>${data.map(row => `<div class='reckon-trend-day' title='${escape(row.label)}'>${series.map(item => `<i class='${item[2]}' style='height:${Math.max(2, row[item[0]] / max * 100)}%'></i>`).join("")}<small>${escape(row.label)}</small></div>`).join("")}</div></section>`;
    }

    function distribution(rows) {
        const total = rows.reduce((sum, row) => sum + row.count, 0);
        const colors = ["#28b67a", "#328bea", "#f4a324", "#ef5b68", "#8858e8", "#18aab0"];
        let offset = 0;
        const stops = rows.map((row, index) => { const start = offset; offset += total ? row.count / total * 100 : 0; return `${colors[index]} ${start}% ${offset}%`; }).join(", ");
        return `<section class='reckon-voucher-panel'><header><h2>Voucher Type Distribution</h2></header><div class='reckon-distribution'><div class='reckon-voucher-donut' style='background:conic-gradient(${stops || "#e8edf4 0 100%"})'><strong>${escape(total)}</strong><small>Vouchers</small></div><div class='reckon-distribution-list'>${rows.length ? rows.map((row, index) => `<div><span><i style='background:${colors[index]}'></i>${escape(row.label)}</span><b>${escape(row.count)}</b><small>${escape(Number(row.percentage || 0).toFixed(0))}%</small></div>`).join("") : `<span class='text-muted'>No vouchers in this period.</span>`}</div></div></section>`;
    }

    function sourcePanel(rows) {
        const max = Math.max(1, ...rows.map(row => row.count));
        return `<section class='reckon-voucher-panel'><header><h2>Entry Source</h2></header><div class='reckon-source-list'>${rows.length ? rows.map((row, index) => `<div><span>${escape(row.label)}</span><i><em class='source-${index}' style='width:${row.count / max * 100}%'></em></i><b>${escape(row.count)}</b><small>${escape(Number(row.percentage || 0).toFixed(0))}%</small></div>`).join("") : `<span class='text-muted'>No source data.</span>`}</div></section>`;
    }

    function usersPanel(rows) {
        const max = Math.max(1, ...rows.map(row => row.count));
        return `<section class='reckon-voucher-panel'><header><h2>User Wise Voucher Entry (Top 5)</h2></header><div class='reckon-user-list'>${rows.length ? rows.map(row => `<div><span title='${escape(row.label)}'>${escape(row.label)}</span><i><em style='width:${row.count / max * 100}%'></em></i><b>${escape(row.count)}</b></div>`).join("") : `<span class='text-muted'>No voucher data.</span>`}</div></section>`;
    }

    function pendingPanel(data) {
        const rows = [["Draft Vouchers", data.pending.drafts, "draft", "List"], ["Pending Approval", data.pending.pending_approval, "pending", "List"], ["On Hold", data.pending.on_hold, "hold", "List"], ["Cancelled (This Period)", data.pending.cancelled, "cancelled", "List"]];
        return `<section class='reckon-voucher-panel'><header><h2>Draft &amp; Pending Vouchers</h2></header><div class='reckon-pending-list'>${rows.map(row => `<button data-status='${row[2]}'><span class='pending-${row[2]}'>!</span><span>${escape(row[0])}</span><b>${escape(row[1])}</b><em>&#8250;</em></button>`).join("")}</div></section>`;
    }

    function recentAccounts(rows) {
        return `<section class='reckon-voucher-panel'><header><h2>Recent Accounts Used</h2><button class='btn btn-link btn-xs' data-report='General Ledger Custom'>View All</button></header><div class='reckon-mini-table'><table><thead><tr><th>Account</th><th>Type</th><th>Times Used</th></tr></thead><tbody>${rows.length ? rows.map(row => `<tr><td>${escape(row.name)}</td><td>${escape(row.type)}</td><td>${escape(row.uses)}</td></tr>`).join("") : `<tr><td colspan='3' class='text-muted'>No accounts used.</td></tr>`}</tbody></table></div></section>`;
    }

    function reportsPanel() {
        return `<section class='reckon-voucher-reports'><header><h2>Reports</h2><span>Quick access to commonly used accounting reports.</span></header><div>${reports.map(report => `<button data-report='${escape(report)}'>${escape(report)}</button>`).join("")}<button data-report='accounting'>Financial Reports (ERPNext)</button></div></section>`;
    }

    function render(data) {
        body.html(`<div class='reckon-voucher-heading'><div><span class='reckon-step'>1</span><div><h1>Voucher Entry</h1><p>Choose a voucher to open a new entry. Review, save and submit in the entry form.</p></div></div><button class='btn btn-primary' data-refresh='1'>&#8635; Refresh Analytics</button></div>` +
            `<section class='reckon-voucher-section'><div class='reckon-voucher-grid'>${entryCards()}</div></section>` +
            `<section class='reckon-voucher-section'><div class='reckon-voucher-heading reckon-subheading'><div><span class='reckon-step'>2</span><div><h2>Voucher Lists</h2><p>Open existing vouchers for review, edit or print.</p></div></div></div><div class='reckon-list-grid'>${listCards()}</div></section>` +
            `<section class='reckon-voucher-section'><div class='reckon-voucher-heading reckon-subheading'><div><span class='reckon-step'>3</span><div><h2>Today's Activity</h2><p>Summary for ${escape(data.period.to_date)}.</p></div></div></div><div class='reckon-activity-grid'>${activityCards(data)}</div></section>` +
            `<section class='reckon-voucher-section'><div class='reckon-voucher-heading reckon-subheading'><div><span class='reckon-step'>4</span><div><h2>Voucher Entry Analytics</h2><p>Operational insights to help you enter vouchers accurately and efficiently.</p></div></div><div class='reckon-range-buttons'><button data-range='7'>Last 7 Days</button><button data-range='30'>Last 30 Days</button><button data-range='90'>Last 3 Months</button></div></div><div class='reckon-analytics-grid'>${trend(data.trend)}${distribution(data.distribution)}${sourcePanel(data.sources)}${usersPanel(data.users)}${pendingPanel(data)}${recentAccounts(data.recent_accounts)}</div></section>` +
            `<section class='reckon-voucher-section'><div class='reckon-voucher-heading reckon-subheading'><div><span class='reckon-step'>5</span><div><h2>Attention Required</h2></div></div></div><div class='reckon-attention-grid'>${[["Unposted Draft Vouchers", data.attention.drafts, "draft"], ["Vouchers Pending Approval", data.attention.pending_approval, "pending"], ["Vouchers With Missing Reference", data.attention.missing_reference, "reference"], ["Duplicate Voucher Number", data.attention.duplicates, "duplicate"]].map(row => `<button data-status='${row[2]}'><span class='attention-${row[2]}'>!</span><span>${escape(row[0])}<b>${escape(row[1])}</b></span><em>&#8250;</em></button>`).join("")}</div></section>` +
            reportsPanel());
    }

    async function refresh() {
        if (!company.get_value() || !from_date.get_value() || !to_date.get_value()) return;
        body.html("<div class='reckon-voucher-loading'><span class='spinner'></span>Loading voucher analytics...</div>");
        try {
            const data = await frappe.xcall("reckon_accounts.api.voucher_entry_data", {
                company: company.get_value(), from_date: from_date.get_value(), to_date: to_date.get_value(),
            });
            render(data);
        } catch (error) {
            console.error("Voucher Entry analytics failed", error);
            body.html(`<div class='reckon-voucher-loading'><strong>Analytics unavailable</strong><span>${escape(error?.message || __("Voucher analytics data is unavailable."))}</span></div>`);
        }
    }

    function applyRange(days) {
        const end = new Date(`${to_date.get_value()}T00:00:00`);
        end.setDate(end.getDate() - Number(days) + 1);
        from_date.set_value(end.toISOString().slice(0, 10));
        refresh();
    }

    body.on("click.reckonVoucherEntry", "[data-entry]", function () { actions[$(this).data("entry")](); })
        .on("click.reckonVoucherEntry", "[data-list]", function () { openList(entries.find(entry => entry.key === $(this).data("list"))); })
        .on("click.reckonVoucherEntry", "[data-report]", function () { const report = $(this).data("report"); report === "accounting" ? frappe.set_route("accounting") : openReport(report); })
        .on("click.reckonVoucherEntry", "[data-range]", function () { applyRange($(this).data("range")); })
        .on("click.reckonVoucherEntry", "[data-refresh]", refresh)
        .on("click.reckonVoucherEntry", "[data-status]", function () { frappe.set_route("List", "Payment Entry", "List"); });
    page.set_primary_action(__("Refresh Analytics"), refresh, "refresh");
    company.$input.add(from_date.$input).add(to_date.$input).on("change.reckonVoucherEntry", refresh);
    $(document).off("keydown.reckonVoucherEntry").on("keydown.reckonVoucherEntry", event => {
        if (frappe.get_route()[0] !== "voucher-entry" || $(".modal:visible").length || event.ctrlKey || event.altKey || event.metaKey || event.shiftKey || event.repeat) return;
        if (actions[event.key]) { event.preventDefault(); event.stopImmediatePropagation(); actions[event.key](); }
    });
    refresh();
};
