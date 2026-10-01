frappe.pages["accounts-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __("Accounts Dashboard"), single_column: true});
    const company = page.add_field({fieldname: "company", label: __("Company"), fieldtype: "Link",
        options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company")});
    const from_date = page.add_field({fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
        reqd: 1, default: `${frappe.datetime.get_today().slice(0, 4)}-01-01`});
    const to_date = page.add_field({fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
        reqd: 1, default: frappe.datetime.get_today()});
    const body = $("<main class='reckon-dashboard'></main>").appendTo(page.main);

    const escape = value => frappe.utils.escape_html(String(value ?? ""));
    const money = (value, currency) => new Intl.NumberFormat(undefined, {
        style: "currency", currency: currency || "BDT", maximumFractionDigits: 0,
    }).format(Number(value || 0));
    const percent = (value, max) => `${max ? Math.max(0, Math.min(100, value / max * 100)) : 0}%`;

    const renderLoading = () => body.html("<div class='reckon-dashboard-empty'>Loading dashboard...</div>");
    const renderEmpty = message => body.html(`<div class='reckon-dashboard-empty'>${escape(message)}</div>`);

    function kpi(title, value, icon, tone) {
        return `<article class='reckon-kpi reckon-tone-${tone}'><div class='reckon-kpi-icon'>${icon}</div>` +
            `<div><div class='reckon-kpi-label'>${escape(title)}</div><strong>${escape(value)}</strong></div></article>`;
    }

    function trend(data, currency) {
        const max = Math.max(1, ...data.flatMap(item => [item.income, item.expenses]));
        return `<section class='reckon-panel reckon-chart-panel'><header><h2>Income vs Expense</h2>` +
            `<span class='reckon-legend'><i class='income'></i>Income <i class='expense'></i>Expense</span></header>` +
            `<div class='reckon-bars'>${data.map(item => `<div class='reckon-bar-group'>` +
            `<div class='reckon-bar income' style='height:${percent(item.income, max)}' title='${escape(money(item.income, currency))}'></div>` +
            `<div class='reckon-bar expense' style='height:${percent(item.expenses, max)}' title='${escape(money(item.expenses, currency))}'></div>` +
            `<small>${escape(item.label)}</small></div>`).join("")}</div></section>`;
    }

    function cashFlow(data, currency) {
        const max = Math.max(1, ...data.flatMap(item => [Math.abs(item.operating), Math.abs(item.investing), Math.abs(item.financing)]));
        return `<section class='reckon-panel reckon-chart-panel'><header><h2>Cash Flow</h2>` +
            `<span class='reckon-legend'><i class='operating'></i>Operating <i class='investing'></i>Investing <i class='financing'></i>Financing</span></header>` +
            `<div class='reckon-flow-list'>${data.map(item => `<div class='reckon-flow-row'><b>${escape(item.label)}</b>` +
            `<span><i class='operating' style='width:${percent(Math.abs(item.operating), max)}'></i>${escape(money(item.operating, currency))}</span>` +
            `<span><i class='investing' style='width:${percent(Math.abs(item.investing), max)}'></i>${escape(money(item.investing, currency))}</span>` +
            `<span><i class='financing' style='width:${percent(Math.abs(item.financing), max)}'></i>${escape(money(item.financing, currency))}</span></div>`).join("")}</div></section>`;
    }

    function ranking(title, rows, amount_label, currency) {
        return `<section class='reckon-panel'><header><h2>${escape(title)}</h2><button class='btn btn-link btn-xs' data-route='query-report|General Ledger Custom'>View All</button></header>` +
            `<div class='reckon-rankings'>${rows.length ? rows.map(row => `<div><span>${escape(row.name)}</span><b>${escape(money(row.amount, currency))}</b></div>`).join("") : `<p class='text-muted'>No ${escape(amount_label.toLowerCase())} found.</p>`}</div></section>`;
    }

    function aging(title, rows, currency) {
        return `<section class='reckon-panel'><header><h2>${escape(title)}</h2></header>` +
            `<div class='reckon-table-wrap'><table><thead><tr><th>Party</th><th>Outstanding</th><th>Days</th></tr></thead><tbody>` +
            (rows.length ? rows.map(row => `<tr><td>${escape(row.name)}</td><td>${escape(money(row.balance, currency))}</td><td><span class='reckon-days'>${escape(row.days)}</span></td></tr>`).join("") : `<tr><td colspan='3' class='text-muted'>No outstanding balance.</td></tr>`) +
            `</tbody></table></div></section>`;
    }

    function recent(rows, currency) {
        return `<section class='reckon-panel reckon-wide'><header><h2>Recent Accounting Transactions</h2><button class='btn btn-link btn-xs' data-route='query-report|Day Book'>View All</button></header>` +
            `<div class='reckon-table-wrap'><table><thead><tr><th>Date</th><th>Voucher</th><th>Type</th><th>Particulars</th><th>Debit</th><th>Credit</th></tr></thead><tbody>` +
            (rows.length ? rows.map(row => `<tr><td>${escape(row.date)}</td><td>${escape(row.voucher_no)}</td><td>${escape(row.type)}</td><td>${escape(row.particulars)}</td><td>${escape(money(row.debit, currency))}</td><td>${escape(money(row.credit, currency))}</td></tr>`).join("") : `<tr><td colspan='6' class='text-muted'>No transactions in this period.</td></tr>`) +
            `</tbody></table></div></section>`;
    }

    function render(data) {
        const currency = data.currency || "BDT";
        const k = data.kpis;
        body.html(`<div class='reckon-dashboard-heading'><div><h1>Accounts Dashboard</h1><p>Financial position, cash flow, receivables and payables.</p></div>` +
            `<span class='reckon-period'>${escape(data.period.from_date)} to ${escape(data.period.to_date)}</span></div>` +
            `<section class='reckon-kpi-grid'>${kpi("Total Income", money(k.income, currency), "IN", "blue")}${kpi("Total Expenses", money(k.expenses, currency), "EX", "green")}${kpi("Net Profit", money(k.profit, currency), "NP", "gold")}${kpi("Receivables", money(k.receivables, currency), "AR", "red")}${kpi("Payables", money(k.payables, currency), "AP", "purple")}${kpi("Cash in Hand", money(k.cash, currency), "CB", "teal")}</section>` +
            `<section class='reckon-chart-grid'>${trend(data.trend, currency)}${cashFlow(data.cash_flow, currency)}</section>` +
            `<section class='reckon-panel-grid'>${aging("Receivables Aging", data.receivables, currency)}${aging("Payables Aging", data.payables, currency)}<section class='reckon-panel'><header><h2>Bank & Cash Balance</h2></header><div class='reckon-rankings'>${data.cash_balances.length ? data.cash_balances.map(row => `<div><span>${escape(row.name)}</span><b>${escape(money(row.balance, currency))}</b></div>`).join("") : `<p class='text-muted'>No bank or cash balance.</p>`}</div></section></section>` +
            `<section class='reckon-panel-grid'>${ranking("Top Income Accounts", data.top_income, "income accounts", currency)}${ranking("Top Expense Accounts", data.top_expense, "expense accounts", currency)}<section class='reckon-panel'><header><h2>Quick Actions</h2></header><div class='reckon-actions'><button data-action='payment'>Payment Entry</button><button data-action='receipt'>Receipt Entry</button><button data-action='voucher'>Voucher Entry</button><button data-route='query-report|Day Book'>Day Book</button></div></section></section>` +
            recent(data.recent, currency));
    }

    async function refresh() {
        if (!company.get_value() || !from_date.get_value() || !to_date.get_value()) {
            return renderEmpty("Select a company and date range.");
        }
        renderLoading();
        try {
            const data = await frappe.xcall("reckon_accounts.api.dashboard_data", {
                company: company.get_value(), from_date: from_date.get_value(), to_date: to_date.get_value(),
            });
            render(data);
        } catch (error) {
            console.error("Accounts Dashboard failed", error);
            renderEmpty(error.message || "Dashboard data is unavailable.");
        }
    }

    body.on("click.reckonDashboard", "[data-route]", function () {
        const [route, value] = $(this).data("route").split("|");
        frappe.set_route(route, value);
    }).on("click.reckonDashboard", "[data-action]", function () {
        const action = $(this).data("action");
        if (action === "voucher") return frappe.set_route("voucher-entry");
        frappe.new_doc("Payment Entry", {
            company: company.get_value(), posting_date: to_date.get_value(),
            payment_type: action === "payment" ? "Pay" : "Receive",
            custom_voucher_subtype: action === "payment" ? "Direct Expense" : "Direct Income",
        });
    });
    company.$input.add(from_date.$input).add(to_date.$input).on("change.reckonDashboard", refresh);
    refresh();
};
