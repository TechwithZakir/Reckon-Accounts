const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

function load() {
    let handlers;
    const moved = new WeakSet();
    const sandbox = {
        __: value => value,
        $: element => ({
            data: (key, value) => value === undefined ? moved.has(element) : moved.add(element),
            after: child => { element.after = child; },
            before: child => { element.before = child; },
        }),
        frappe: {boot: {party_account_types: {Supplier: "Payable", Customer: "Receivable"}},
            ui: {form: {on: (doctype, events) => { assert.equal(doctype, "Payment Entry"); handlers = events; }}}},
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/payment_entry.js"), "utf8"), sandbox);
    return handlers;
}

test("payment labels and required mode follow payment type", () => {
    const events = load();
    const properties = {};
    const dimensions = {};
    const accounts = {};
    const collapsed = [];
    const accountingDimensionsSection = {
        collapse: value => collapsed.push(value),
    };
    const frm = {
        doc: {payment_type: "Receive"},
        layout: {sections_dict: {accounting_dimensions_section: accountingDimensionsSection}},
        fields_dict: {accounting_dimensions_section: {wrapper: dimensions},
            payment_accounts_section: {wrapper: accounts}},
        set_df_property: (field, property, value) => {properties[field + "." + property] = value;},
        toggle_display: () => {},
        set_query: () => {},
    };
    events.refresh(frm);
    assert.equal(properties["paid_from.label"], "Received From Account");
    assert.equal(properties["paid_to.label"], "Received To Account");
    assert.equal(properties["paid_amount.label"], "Received Amount");
    assert.equal(properties["party_section.label"], "Party Details");
    assert.equal(properties["mode_of_payment.reqd"], 1);
    assert.equal("accounting_dimensions_section.collapsible" in properties, false);
    assert.equal(accountingDimensionsSection.expanded_by_user, true);
    assert.deepEqual(collapsed, [false]);
    assert.equal(dimensions.before, accounts);
    frm.doc.payment_type = "Pay";
    events.payment_type(frm);
    assert.equal(properties["party_section.label"], "Party Details");
    assert.equal(properties["paid_amount.label"], "Paid Amount");
});

test("direct expense and income subtypes map to Pay and Receive", () => {
    const events = load();
    const values = [];
    const frm = {
        doc: {payment_type: "Pay", custom_voucher_subtype: "Direct Expense"},
        layout: {sections_dict: {}},
        fields_dict: {},
        set_df_property: () => {},
        toggle_display: () => {},
        set_query: () => {},
        set_value: (field, value) => values.push([field, value]),
    };
    events.custom_voucher_subtype(frm);
    assert.deepEqual(values.slice(0, 1), [["payment_type", "Pay"]]);
    frm.doc.custom_voucher_subtype = "Direct Income";
    frm.doc.payment_type = "Receive";
    events.custom_voucher_subtype(frm);
    assert.ok(values.some(([field, value]) => field === "payment_type" && value === "Receive"));
});
