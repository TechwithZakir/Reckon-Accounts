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
    const compactMoney = (value, currency) => new Intl.NumberFormat(undefined, {
        style: "currency", currency: currency || "BDT", notation: "compact", maximumFractionDigits: 1,
    }).format(Number(value || 0));
    const percent = (value, max) => `${max ? Math.max(0, Math.min(100, Math.abs(value) / max * 100)) : 0}%`;
    const renderLoading = () => body.html("<div class='reckon-dashboard-empty'><span class='spinner'></span>Loading analytics...</div>");
    const renderEmpty = message => body.html(`<div class='reckon-dashboard-empty'><strong>Dashboard unavailable</strong><span>${escape(message)}</span></div>`);

    function kpi(title, key, icon, tone, data, currency) {
        const change = data.comparison && data.comparison[key];
        const isBalance = ["receivables", "payables"].includes(key);
        const favorable = change === null ? false : isBalance ? change <= 0 : change >= 0;
        const changeLabel = change === null ? "New" : `${change >= 0 ? "+" : ""}${Number(change).toFixed(1)}%`;
        const changeClass = change === null ? "neutral" : favorable ? "positive" : "negative";
        return `<article class='reckon-kpi reckon-tone-${tone}'>` +
            `<div class='reckon-kpi-icon'>${icon}</div><div class='reckon-kpi-copy'>` +
            `<div class='reckon-kpi-label'>${escape(title)}</div><strong>${escape(money(data.kpis[key], currency))}</strong>` +
            `<small class='reckon-change ${changeClass}'>${changeClass === "positive" ? "&#8593;" : changeClass === "negative" ? "&#8595;" : ""} ${escape(changeLabel)} <em>vs previous period</em></small>` +
            `</div></article>`;
    }

    function legend(items) {
        return `<span class='reckon-legend'>${items.map(item => `<i class='${item[0]}'></i>${escape(item[1])}`).join("")}</span>`;
    }

    function barChart(data, currency) {
        const max = Math.max(1, ...data.flatMap(item => [item.income, item.expenses]));
        return `<section class='reckon-panel reckon-chart-panel'><header><h2>Income vs Expense</h2>` +
            legend([["income", "Income"], ["expense", "Expense"]]) + `</header>` +
            `<div class='reckon-axis'><span>${escape(compactMoney(max, currency))}</span><span>${escape(compactMoney(max / 2, currency))}</span><span>0</span></div>` +
            `<div class='reckon-bar-chart'>${data.map(item => `<div class='reckon-bar-group' title='${escape(`${item.label}: ${money(item.income, currency)} income, ${money(item.expenses, currency)} expense`)}'>` +
                `<div class='reckon-bar income' style='height:${percent(item.income, max)}'></div><div class='reckon-bar expense' style='height:${percent(item.expenses, max)}'></div><small>${escape(item.label)}</small></div>`).join("")}</div></section>`;
    }

    function profitTrend(data, currency) {
        const max = Math.max(1, ...data.flatMap(item => [item.income, item.expenses, Math.abs(item.profit)]));
        return `<section class='reckon-panel reckon-chart-panel'><header><h2>Profit &amp; Loss Trend</h2>` +
            legend([["income", "Income"], ["expense", "Expense"], ["profit", "Net Profit"]]) + `</header>` +
            `<div class='reckon-axis'><span>${escape(compactMoney(max, currency))}</span><span>${escape(compactMoney(max / 2, currency))}</span><span>0</span></div>` +
            `<div class='reckon-bar-chart reckon-profit-chart'>${data.map(item => `<div class='reckon-bar-group' title='${escape(`${item.label}: ${money(item.profit, currency)} profit`)}'>` +
                `<div class='reckon-bar income' style='height:${percent(item.income, max)}'></div><div class='reckon-bar expense' style='height:${percent(item.expenses, max)}'></div><div class='reckon-bar profit' style='height:${percent(item.profit, max)}'></div><small>${escape(item.label)}</small></div>`).join("")}</div></section>`;
    }

    function cashFlow(data, currency) {
        const max = Math.max(1, ...data.flatMap(item => [Math.abs(item.operating), Math.abs(item.investing), Math.abs(item.financing)]));
        return `<section class='reckon-panel reckon-chart-panel'><header><h2>Cash Flow</h2>` +
            legend([["operating", "Operating"], ["investing", "Investing"], ["financing", "Financing"]]) + `</header>` +
            `<div class='reckon-axis reckon-axis-negative'><span>${escape(compactMoney(max, currency))}</span><span>0</span><span>-${escape(compactMoney(max, currency))}</span></div>` +
            `<div class='reckon-bar-chart reckon-cash-chart'>${data.map(item => `<div class='reckon-bar-group' title='${escape(`${item.label}: ${money(item.operating, currency)} operating`)}'>` +
                `<div class='reckon-bar operating' style='height:${percent(item.operating, max)}'></div><div class='reckon-bar investing' style='height:${percent(item.investing, max)}'></div><div class='reckon-bar financing' style='height:${percent(item.financing, max)}'></div><small>${escape(item.label)}</small></div>`).join("")}</div></section>`;
    }

    function aging(title, rows, currency, tone) {
        const total = rows.reduce((sum, row) => sum + Number(row.amount || 0), 0);
        const colors = ["#2dbb72", "#f3a522", "#ee7d4d", "#ef5c68"];
        let offset = 0;
        const stops = rows.map((row, index) => {
            const start = offset;
            offset += Number(row.percentage || 0);
            return `${colors[index]} ${start}% ${offset}%`;
        }).join(", ");
        return `<section class='reckon-panel reckon-aging-panel'><header><h2>${escape(title)}</h2><button class='btn btn-link btn-xs' data-route='query-report|${tone === "receivable" ? "Accounts Receivable" : "Accounts Payable"}'>View All</button></header>` +
            `<div class='reckon-aging-body'><div class='reckon-donut' style='background:conic-gradient(${stops || "#e8edf4 0 100%"})'><div><strong>${escape(money(total, currency))}</strong><small>Total ${tone === "receivable" ? "Receivables" : "Payables"}</small></div></div>` +
            `<div class='reckon-aging-list'>${rows.map((row, index) => `<div><span><i style='background:${colors[index]}'></i>${escape(row.label)}</span><b>${escape(money(row.amount, currency))}</b><small>${escape(Number(row.percentage || 0).toFixed(0))}%</small></div>`).join("")}</div></div></section>`;
    }

    function balances(rows, currency) {
        const total = rows.reduce((sum, row) => sum + Number(row.balance || 0), 0);
        return `<section class='reckon-panel'><header><h2>Bank &amp; Cash Balance</h2><button class='btn btn-link btn-xs' data-route='query-report|Bank Summary'>View All</button></header>` +
            `<div class='reckon-balance-list'>${rows.length ? rows.map(row => `<div><span>${escape(row.name)}</span><b>${escape(money(row.balance, currency))}</b></div>`).join("") : `<p class='text-muted'>No bank or cash balance.</p>`}</div>` +
            `<div class='reckon-total-row'><span>Total Balance</span><strong>${escape(money(total, currency))}</strong></div></section>`;
    }

    function ranking(title, rows, currency, tone) {
        const max = Math.max(1, ...rows.map(row => Number(row.amount || 0)));
        return `<section class='reckon-panel'><header><h2>${escape(title)}</h2><button class='btn btn-link btn-xs' data-route='query-report|General Ledger Custom'>View All</button></header>` +
            `<div class='reckon-ranking-list'>${rows.length ? rows.map(row => `<div><span title='${escape(row.name)}'>${escape(row.name)}</span><b>${escape(money(row.amount, currency))}</b><i class='${tone}'><em style='width:${percent(row.amount, max)}'></em></i></div>`).join("") : `<p class='text-muted'>No accounts found.</p>`}</div></section>`;
    }

    function accountSummary(rows, currency) {
        return `<section class='reckon-panel'><header><h2>Account Balance Summary</h2><button class='btn btn-link btn-xs' data-route='doctype|Account'>View All</button></header>` +
            `<div class='reckon-table-wrap'><table><thead><tr><th>Account Type</th><th>Accounts</th><th>Balance</th></tr></thead><tbody>` +
            (rows.length ? rows.map(row => `<tr><td><span class='reckon-type-dot ${escape(row.type.toLowerCase())}'></span>${escape(row.type)}</td><td>${escape(row.accounts)}</td><td>${escape(money(row.balance, currency))}</td></tr>`).join("") : `<tr><td colspan='3' class='text-muted'>No account balances.</td></tr>`) +
            `</tbody></table></div></section>`;
    }

    function recent(rows, currency, count) {
        return `<section class='reckon-panel reckon-wide'><header><div><h2>Recent Accounting Transactions</h2><p class='reckon-panel-subtitle'>${escape(count)} transactions in the selected period</p></div><button class='btn btn-link btn-xs' data-route='query-report|Day Book'>View All</button></header>` +
            `<div class='reckon-table-wrap'><table><thead><tr><th>Date</th><th>Voucher No.</th><th>Type</th><th>Account / Party</th><th>Debit</th><th>Credit</th><th>Status</th></tr></thead><tbody>` +
            (rows.length ? rows.map(row => `<tr><td>${escape(row.date)}</td><td class='reckon-link'>${escape(row.voucher_no)}</td><td>${escape(row.type)}</td><td>${escape(row.particulars || "-")}</td><td>${escape(money(row.debit, currency))}</td><td>${escape(money(row.credit, currency))}</td><td><span class='reckon-status'>${escape(row.status || "Posted")}</span></td></tr>`).join("") : `<tr><td colspan='7' class='text-muted'>No transactions in this period.</td></tr>`) +
            `</tbody></table></div></section>`;
    }

    function quickActions() {
        return `<section class='reckon-panel'><header><h2>Quick Actions</h2></header><div class='reckon-actions'>` +
            `<button data-action='voucher'><span>+</span>Create Voucher</button><button data-action='receipt'><span>&#8593;</span>Receive Payment</button>` +
            `<button data-action='payment'><span>&#8595;</span>Make Payment</button><button data-route='query-report|Day Book'><span>&#9776;</span>Day Book</button>` +
            `</div></section>`;
    }

    function render(data) {
        const currency = data.currency || "BDT";
        body.html(`<div class='reckon-dashboard-heading'><div><h1>Accounts Dashboard</h1><p>Realtime financial overview of your business performance.</p></div>` +
            `<div class='reckon-dashboard-meta'><span>${escape(data.period.from_date)} to ${escape(data.period.to_date)}</span><small>${escape(data.previous_period.from_date)} to ${escape(data.previous_period.to_date)} previous period</small></div></div>` +
            `<section class='reckon-kpi-grid'>${kpi("Total Income", "income", "IN", "blue", data, currency)}${kpi("Total Expenses", "expenses", "EX", "red", data, currency)}${kpi("Net Profit", "profit", "NP", "gold", data, currency)}${kpi("Outstanding Receivables", "receivables", "AR", "orange", data, currency)}${kpi("Outstanding Payables", "payables", "AP", "purple", data, currency)}${kpi("Cash in Hand", "cash", "CB", "green", data, currency)}</section>` +
            `<section class='reckon-chart-grid'>${barChart(data.trend, currency)}${profitTrend(data.trend, currency)}${cashFlow(data.cash_flow, currency)}</section>` +
            `<section class='reckon-panel-grid'>${aging("Receivables Aging", data.receivables_aging, currency, "receivable")}${aging("Payables Aging", data.payables_aging, currency, "payable")}${balances(data.cash_balances, currency)}</section>` +
            `<section class='reckon-panel-grid'>${ranking("Top Income Accounts", data.top_income, currency, "income-fill")}${ranking("Top Expense Accounts", data.top_expense, currency, "expense-fill")}${accountSummary(data.account_balance_summary, currency)}</section>` +
            `<section class='reckon-panel-grid reckon-action-grid'>${quickActions()}<div class='reckon-analytics-note'><strong>Analytics scope</strong><span>All summaries respect the selected company, date range, accounting dimensions, and report permissions.</span></div></section>` +
            recent(data.recent, currency, data.transaction_count));
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
            const message = error && (error.message || error.exception);
            renderEmpty(message || __("Dashboard data is unavailable."));
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
    page.set_primary_action(__("Refresh"), refresh, "refresh");
    company.$input.add(from_date.$input).add(to_date.$input).on("change.reckonDashboard", refresh);
    refresh();
};
