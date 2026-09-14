const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

function settings(name) {
    const sandbox = {
        URLSearchParams,
        __: (text) => text,
        frappe: {
            provide: () => {}, query_reports: {},
            defaults: {get_user_default: () => "Co"},
            datetime: {month_start: () => "2026-01-01", get_today: () => "2026-01-31"},
            utils: {escape_html: (text) => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")},
        },
        reckon_accounts: {},
    };
    const source = fs.readFileSync(path.join(__dirname, "../public/js/report_filters.js"), "utf8");
    vm.runInNewContext(source, sandbox);
    return {settings: sandbox.reckon_accounts.report_settings(name), sandbox};
}

test("each report has strict scope controls and correct required account", () => {
    for (const name of ["Party Ledger", "Account Ledger", "General Ledger Custom"]) {
        const {settings: report} = settings(name);
        const fields = report.filters.map((field) => field.fieldname);
        assert.equal(fields.length, new Set(fields).size);
        assert(fields.includes("finance_book") && fields.includes("dimensions"));
        assert.equal(Boolean(report.filters.find((f) => f.fieldname === "account").reqd), false);
    }
});

test("account drill-down retains scope and resets pagination", () => {
    const {settings: report, sandbox} = settings("General Ledger Custom");
    sandbox.frappe.query_report = {get_filter_values: () => ({company: "Co", page: 3,
        from_date: "2026-01-01", finance_book: "Primary", dimensions: '{"project":["A"]}'})};
    const link = report.formatter("AR & Co", 0, {fieldname: "account_name", fieldtype: "Data"}, {row_kind: "entry", account: "ACC-001"});
    assert(link.includes("Account%20Ledger"));
    assert(link.includes("page=1"));
    assert(link.includes("account=ACC-001"));
    assert(link.includes("finance_book=Primary"));
    assert(link.includes("dimensions="));
    assert(link.includes("AR &amp; Co</a>"));
});

test("text and headings escape markup and source link uses framework formatter", () => {
    const {settings: report} = settings("General Ledger Custom");
    assert.equal(report.formatter("<script>", 0, {fieldname: "description", fieldtype: "Data"},
        {row_kind: "party_heading"}), "<strong>&lt;script&gt;</strong>");
    assert.equal(report.formatter("<script>", 0, {fieldname: "remarks", fieldtype: "Data"},
        {row_kind: "entry"}), "&lt;script&gt;");
    assert.equal(report.formatter("JV-1", 0, {fieldname: "voucher_no", fieldtype: "Dynamic Link"},
        {row_kind: "entry"}, (value) => "safe:" + value), "safe:JV-1");
});

test("changing company clears dependent scope and returns to first page", async () => {
    const {settings: report} = settings("General Ledger Custom");
    const changes = {};
    let refreshes = 0;
    const instance = {_no_refresh: false, set_filter_value: async (key, value) => {changes[key] = value;},
        refresh: () => {refreshes++;}};
    await report.filters.find((f) => f.fieldname === "company").on_change(instance);
    assert.equal(changes.page, 1);
    assert.equal(changes.account, "");
    assert.equal(changes.dimensions, "{}");
    assert.equal(refreshes, 1);
    assert.equal(instance._no_refresh, false);
});

test("report includes resolve to valid JS and register each report", () => {
    const base = path.join(__dirname, "../reckon_accounts/report");
    const reports = fs.readdirSync(base).filter((name) => fs.existsSync(path.join(base, name, name + ".json")));
    assert.equal(reports.length, 25);
    for (const dir of reports) {
        let source = fs.readFileSync(path.join(base, dir, dir + ".js"), "utf8");
        source = source.replace(/\{% include "reckon_accounts\/([^\"]+)" %\}/g,
            (_, file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8"));
        new vm.Script(source);
        const metadata = JSON.parse(fs.readFileSync(path.join(base, dir, dir + ".json"), "utf8"));
        assert(source.includes(metadata.report_name));
        assert.equal(metadata.add_total_row, 0);
        assert.equal(metadata.ref_doctype, "GL Entry");
        assert.deepEqual(Array.from(settings(metadata.report_name).settings.filters.filter(f => f.reqd), f => f.fieldname), ["company", "from_date", "to_date"]);
        assert.equal(metadata.module, "Reckon Accounts");
        assert(!metadata.report_name.startsWith("Reckon "));
        assert.notEqual(metadata.report_name, "General Ledger");
    }
});

test("leaving Reckon restores normal export behavior for standard reports", async () => {
    const {settings: config, sandbox} = settings("Day Book");
    let standardExports = 0;
    let fullExports = 0;
    sandbox.open_url_post = () => { fullExports++; };
    sandbox.frappe.request = {url: "/"};
    sandbox.frappe.xcall = async () => ({party_types: ["Customer", "Other"], dimensions: []});
    sandbox.frappe.model = {can_export: () => true};
    const report = {
        report_name: "Day Book",
        export_report: () => {standardExports++;},
        get_filter: () => ({get_value: () => "", df: {}, refresh: () => {}}),
        get_filter_values: () => ({company: "Co"}),
        page: {add_inner_button: () => {}},
    };
    await config.onload(report);
    report.export_report();
    assert.equal(fullExports, 1);
    report.report_name = "General Ledger";
    report.export_report();
    assert.equal(standardExports, 1);
    assert.equal(fullExports, 1);
});

 test("company-wide monthly labels drill into the exact month", () => {
    const {settings: report, sandbox} = settings("Group Monthly Summary");
    sandbox.frappe.query_report = {get_filter_values: () => ({company: "Co", page: 4, finance_book: "Primary"})};
    const link = report.formatter("February 2026", 0, {fieldname: "description"},
        {row_kind: "monthly", posting_date: "2026-02-01", period_end: "2026-02-28"});
    assert(link.includes("Group%20Vouchers"));
    assert(link.includes("from_date=2026-02-01"));
    assert(link.includes("to_date=2026-02-28"));
    assert(link.includes("page=1"));
    assert(!link.includes("account="));
});

test("register entry shortcuts use native drafts and respect create permission", async () => {
    for (const [name, type] of [["Receipt Register", "Receive"], ["Payment Register", "Pay"], ["Contra Register", "Internal Transfer"], ["Journal Register", "Journal Entry"]]) {
        for (const allowed of [true, false]) {
            const {settings: config, sandbox} = settings(name);
            const buttons = {};
            let created;
            sandbox.frappe.model = {can_create: () => allowed};
            sandbox.frappe.new_doc = (doctype, values) => {created = {doctype, values};};
            // Stop after the entry controls; metadata loading is tested separately.
            sandbox.frappe.xcall = async () => {throw new Error("metadata boundary");};
            await assert.rejects(config.onload({page: {add_inner_button: (label, action) => buttons[label] = action}, get_filter_value: () => "Co"}), /metadata boundary/);
            assert.equal(Boolean(buttons["New Entry"]), allowed);
            if (allowed) {
                buttons["New Entry"]();
                assert.equal(created.values.company, "Co");
                assert.equal(created.values.payment_type || created.values.voucher_type, type);
                assert.equal(created.doctype, name === "Journal Register" ? "Journal Entry" : "Payment Entry");
            }
        }
    }
});
