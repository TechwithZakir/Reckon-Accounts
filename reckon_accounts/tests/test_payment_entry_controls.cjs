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
        }),
        frappe: {ui: {form: {on: (doctype, events) => { assert.equal(doctype, "Payment Entry"); handlers = events; }}}},
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/js/payment_entry.js"), "utf8"), sandbox);
    return handlers;
}

test("payment labels and required mode follow payment type", () => {
    const events = load();
    const properties = {};
    const amounts = {};
    const dimensions = {};
    const frm = {
        doc: {payment_type: "Receive"},
        fields_dict: {payment_amounts_section: {wrapper: amounts}, accounting_dimensions_section: {wrapper: dimensions}},
        set_df_property: (field, property, value) => {properties[field + "." + property] = value;},
    };
    events.payment_type(frm);
    assert.equal(properties["paid_from.label"], "Received From Account");
    assert.equal(properties["paid_to.label"], "Received To Account");
    assert.equal(properties["paid_amount.label"], "Received Amount");
    assert.equal(properties["party_section.label"], "Received From");
    assert.equal(properties["mode_of_payment.reqd"], 1);
    assert.equal(amounts.after, dimensions);
    frm.doc.payment_type = "Pay";
    events.payment_type(frm);
    assert.equal(properties["party_section.label"], "Payment To");
    assert.equal(properties["paid_amount.label"], "Paid Amount");
});
