const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

function load() {
    let handlers;
    const sandbox = {
        __: value => value,
        frappe: {boot: {party_account_types: {Supplier: "Payable", Customer: "Receivable"}},
            ui: {form: {on: (doctype, events) => { assert.equal(doctype, "Payment Entry"); handlers = events; }}}},
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/payment_entry.js"), "utf8"), sandbox);
    return handlers;
}

test("payment labels and required mode follow payment type", () => {
    const events = load();
    const properties = {};
    const collapsed = [];
    const accountingDimensionsSection = {
        collapse: value => collapsed.push(value),
    };
    const frm = {
        doc: {payment_type: "Receive"},
        layout: {sections_dict: {accounting_dimensions_section: accountingDimensionsSection}},
        fields_dict: {},
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
    assert.equal(properties["payment_amounts_section.depends_on"], "eval:(doc.paid_to && doc.paid_from)");
    assert.equal(properties["received_amount.depends_on"], null);
    assert.equal("accounting_dimensions_section.collapsible" in properties, false);
    assert.equal(accountingDimensionsSection.expanded_by_user, true);
    assert.deepEqual(collapsed, [false]);
    frm.doc.payment_type = "Pay";
    events.payment_type(frm);
    assert.equal(properties["party_section.label"], "Party Details");
    assert.equal(properties["paid_amount.label"], "Paid Amount");
});

test("direct expense and income subtypes map to Pay and Receive", () => {
    const events = load();
    const values = [];
    const properties = {};
    const frm = {
        doc: {payment_type: "Pay", custom_voucher_subtype: "Direct Expense"},
        layout: {sections_dict: {}},
        fields_dict: {},
        set_df_property: (field, property, value) => {properties[field + "." + property] = value;},
        toggle_display: () => {},
        set_query: () => {},
        set_value: (field, value) => values.push([field, value]),
    };
    events.custom_voucher_subtype(frm);
    assert.deepEqual(values.slice(0, 1), [["payment_type", "Pay"]]);
    assert.equal(properties["payment_amounts_section.depends_on"], "eval:(doc.paid_to && doc.paid_from)");
    assert.equal(properties["received_amount.depends_on"], "eval:!doc.custom_voucher_subtype");
    frm.doc.custom_voucher_subtype = "Direct Income";
    frm.doc.payment_type = "Receive";
    events.custom_voucher_subtype(frm);
    assert.ok(values.some(([field, value]) => field === "payment_type" && value === "Receive"));
});

test("direct subtype options expose the new labels without changing stored values", () => {
    const source = fs.readFileSync(path.join(__dirname, "../public/js/payment_entry.js"), "utf8");
    assert(source.includes('"Direct Expense": __("Expense (Non-party)")'));
    assert(source.includes('"Direct Income": __("Income (Non-party)")'));
    assert(source.includes("this.value"));
});
