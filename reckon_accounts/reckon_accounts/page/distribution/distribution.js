frappe.pages["distribution"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __("Distribution Dashboard"), single_column: true});
    const company = page.add_field({fieldname: "company", label: __("Company"), fieldtype: "Link",
        options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")});
    const from_date = page.add_field({fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
        reqd: 1, default: frappe.datetime.month_start()});
    const to_date = page.add_field({fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
        reqd: 1, default: frappe.datetime.get_today()});
    const body = $("<main class='reckon-distribution-page'></main>").appendTo(page.main);
    const escape = value => frappe.utils.escape_html(String(value ?? ""));
    const number = value => new Intl.NumberFormat(undefined, {maximumFractionDigits: 0}).format(Number(value || 0));
    const money = (value, currency) => new Intl.NumberFormat(undefined, {
        style: "currency", currency: currency || "BDT", maximumFractionDigits: 0,
    }).format(Number(value || 0));
    const percent = (value, max) => `${Math.min(100, Math.max(0, Number(value || 0) / Math.max(1, max) * 100))}%`;

    function kpi(label, value, detail, tone, action) {
        return `<article class='distribution-kpi ${tone}' ${action ? `data-open-list='${action}'` : ""}><span class='distribution-kpi-icon'>${label.slice(0, 2).toUpperCase()}</span><div><small>${escape(label)}</small><strong>${escape(value)}</strong><em>${escape(detail)}</em></div></article>`;
    }

    function trend(data, currency) {
        const max = Math.max(1, ...data.flatMap(row => [row.sales, row.deliveries, row.purchases, row.expenses]));
        return `<section class='distribution-panel distribution-wide'><header><div><h2>Sales, Delivery &amp; Purchase Trend</h2><p>Posted transaction values in the selected period.</p></div><span class='distribution-legend'><i class='sales'></i>Sales <i class='delivery'></i>Delivery <i class='purchase'></i>Purchase <i class='expense'></i>Expense</span></header><div class='distribution-chart'>${data.map(row => `<div class='distribution-chart-column' title='${escape(`${row.label}: ${money(row.sales, currency)} sales`)}'><div class='distribution-bars'><i class='sales' style='height:${percent(row.sales, max)}'></i><i class='delivery' style='height:${percent(row.deliveries, max)}'></i><i class='purchase' style='height:${percent(row.purchases, max)}'></i><i class='expense' style='height:${percent(row.expenses, max)}'></i></div><small>${escape(row.label)}</small></div>`).join("")}</div></section>`;
    }

    function profitPanel(data, currency) {
        const max = Math.max(1, ...data.map(row => Math.abs(row.profit || 0)));
        return `<section class='distribution-panel'><header><div><h2>Profit &amp; Loss</h2><p>Income and expense movement from the ledger.</p></div></header><div class='distribution-profit-list'>${data.map(row => `<div><span>${escape(row.label)}</span><i><em class='${row.profit < 0 ? "loss" : "profit"}' style='width:${percent(Math.abs(row.profit), max)}'></em></i><b class='${row.profit < 0 ? "loss-text" : "profit-text"}'>${escape(money(row.profit, currency))}</b></div>`).join("")}</div></section>`;
    }

    function ranking(title, rows, currency, empty, action) {
        const max = Math.max(1, ...rows.map(row => Number(row.amount || 0)));
        return `<section class='distribution-panel'><header><h2>${escape(title)}</h2>${action ? `<button class='btn btn-link btn-xs' data-open-list='${action}'>View All</button>` : ""}</header><div class='distribution-ranking'>${rows.length ? rows.map(row => `<div><span title='${escape(row.name)}'>${escape(row.name)}</span><b>${escape(money(row.amount, currency))}</b><i><em style='width:${percent(row.amount, max)}'></em></i></div>`).join("") : `<p class='text-muted'>${escape(empty)}</p>`}</div></section>`;
    }

    function statusPanel(title, rows) {
        const total = rows.reduce((sum, row) => sum + Number(row.count || 0), 0);
        return `<section class='distribution-panel'><header><h2>${escape(title)}</h2></header><div class='distribution-status-list'>${rows.length ? rows.map(row => `<div><span>${escape(row.label)}</span><b>${escape(row.count)}</b><small>${total ? `${Math.round(row.count / total * 100)}%` : "0%"}</small></div>`).join("") : `<p class='text-muted'>No records in this period.</p>`}</div></section>`;
    }

    function aging(title, rows, currency, tone) {
        const total = rows.reduce((sum, row) => sum + Number(row.amount || 0), 0);
        let offset = 0;
        const colors = ["#2dba72", "#f2a329", "#ed7652", "#ed5c68"];
        const stops = rows.map((row, index) => { const start = offset; offset += total ? row.amount / total * 100 : 0; return `${colors[index]} ${start}% ${offset}%`; }).join(", ");
        return `<section class='distribution-panel'><header><h2>${escape(title)}</h2></header><div class='distribution-aging'><div class='distribution-donut ${tone}' style='background:conic-gradient(${stops || "#e8eef5 0 100%"})'><div><strong>${escape(money(total, currency))}</strong><small>Total</small></div></div><div class='distribution-aging-list'>${rows.map((row, index) => `<div><span><i style='background:${colors[index]}'></i>${escape(row.label)}</span><b>${escape(money(row.amount, currency))}</b><small>${escape(Number(row.percentage || 0).toFixed(0))}%</small></div>`).join("")}</div></div></section>`;
    }

    function recent(title, rows, action) {
        return `<section class='distribution-panel distribution-wide'><header><h2>${escape(title)}</h2>${action ? `<button class='btn btn-link btn-xs' data-open-list='${action}'>View All</button>` : ""}</header><div class='distribution-table-wrap'><table><thead><tr><th>Date</th><th>Document</th><th>Party</th><th>Amount</th><th>Status</th></tr></thead><tbody>${rows.length ? rows.map(row => `<tr><td>${escape(row.date)}</td><td class='distribution-document'>${escape(row.name)}</td><td>${escape(row.party)}</td><td>${escape(row.amount)}</td><td><span class='distribution-status'>${escape(row.status)}</span></td></tr>`).join("") : `<tr><td colspan='5' class='text-muted'>No transactions in this period.</td></tr>`}</tbody></table></div></section>`;
    }

    function render(data) {
        const currency = data.currency || "BDT";
        const k = data.kpis || {};
        body.html(`<div class='distribution-heading'><div><h1>Distribution Dashboard</h1><p>Sales force, delivery, purchasing, profitability and collection performance.</p></div><div class='distribution-period'><strong>${escape(data.period.from_date)} to ${escape(data.period.to_date)}</strong><small>Company distribution overview</small></div></div>` +
            `<section class='distribution-kpi-grid'>${kpi("Sales", money(k.sales, currency), `${number(k.sales_count)} posted invoices`, "sales-kpi", "Sales Invoice")}${kpi("Delivery", money(k.deliveries, currency), `${number(k.delivery_count)} delivery notes`, "delivery-kpi", "Delivery Note")}${kpi("Purchase", money(k.purchases, currency), `${number(k.purchase_count)} purchase receipts`, "purchase-kpi", "Purchase Receipt")}${kpi("Expense", money(k.expenses, currency), "GL expense movement", "expense-kpi")}${kpi(k.profit < 0 ? "Loss" : "Profit", money(Math.abs(k.profit), currency), k.profit < 0 ? "Net loss" : "Net profit", k.profit < 0 ? "loss-kpi" : "profit-kpi")}${kpi("Receivable", money(k.receivables, currency), "Open customer balance", "receivable-kpi", "Sales Invoice")}${kpi("Payable", money(k.payables, currency), "Open supplier balance", "Purchase Invoice")}</section>` +
            `<section class='distribution-grid distribution-chart-grid'>${trend(data.trend || [], currency)}${profitPanel(data.trend || [], currency)}</section>` +
            `<section class='distribution-grid'>${ranking("SR / DSR Performance", data.sales_reps || [], currency, "No sales representative data found.")}${ranking("Top Customers", data.top_customers || [], currency, "No sales found.", "Sales Invoice")}${statusPanel("Delivery Status", data.delivery_status || [])}</section>` +
            `<section class='distribution-grid'>${aging("Receivables Aging", data.receivables_aging || [], currency, "receivable-aging")}${aging("Payables Aging", data.payables_aging || [], currency, "payable-aging")}${ranking("Top Suppliers", data.top_suppliers || [], currency, "No purchase receipts found.", "Purchase Receipt")}</section>` +
            `<section class='distribution-grid'>${statusPanel("Sales Invoice Status", data.sales_status || [])}${statusPanel("Purchase Receipt Status", data.purchase_status || [])}${recent("Recent Sales", data.recent_sales || [], "Sales Invoice")}</section>` +
            `<section class='distribution-grid distribution-action-grid'><section class='distribution-panel'><header><h2>Quick Actions</h2></header><div class='distribution-actions'><button data-new-doc='Sales Invoice'>New Sales Invoice</button><button data-new-doc='Delivery Note'>New Delivery Note</button><button data-new-doc='Purchase Receipt'>New Purchase Receipt</button><button data-new-doc='Payment Entry'>New Payment Entry</button></div></section><section class='distribution-panel distribution-note'><h2>Distribution Scope</h2><p>Figures use permission-checked submitted transactions and the selected company and date range. SR/DSR values use invoice fields or Sales Team allocation when configured.</p></section></section>`);
    }

    function openList(doctype) {
        frappe.route_options = {company: company.get_value(), posting_date: ["between", [from_date.get_value(), to_date.get_value()]]};
        frappe.set_route("List", doctype, "List");
    }

    function openNew(doctype) {
        frappe.new_doc(doctype, {company: company.get_value(), posting_date: to_date.get_value()});
    }

    async function refresh() {
        if (!company.get_value() || !from_date.get_value() || !to_date.get_value()) return;
        body.html("<div class='distribution-loading'><span class='spinner'></span>Loading distribution analytics...</div>");
        try {
            const data = await frappe.xcall("reckon_accounts.api.distribution_dashboard_data", {
                company: company.get_value(), from_date: from_date.get_value(), to_date: to_date.get_value(),
            });
            render(data);
        } catch (error) {
            console.error("Distribution Dashboard failed", error);
            body.html(`<div class='distribution-loading'><strong>Distribution dashboard unavailable</strong><span>${escape(error?.message || __("Distribution analytics data is unavailable."))}</span></div>`);
        }
    }

    body.on("click.reckonDistribution", "[data-open-list]", function () { openList($(this).data("open-list")); })
        .on("click.reckonDistribution", "[data-new-doc]", function () { openNew($(this).data("new-doc")); });
    page.set_primary_action(__("Refresh"), refresh, "refresh");
    company.$input.add(from_date.$input).add(to_date.$input).on("change.reckonDistribution", refresh);
    refresh();
};
