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
    const accounts = {};
    const customRemarks = {};
    const collapsed = [];
    const accountingDimensionsSection = {
        collapse: value => collapsed.push(value),
    };
    const frm = {
        doc: {payment_type: "Receive"},
        layout: {sections_dict: {accounting_dimensions_section: accountingDimensionsSection}},
        fields_dict: {payment_amounts_section: {wrapper: amounts},
            accounting_dimensions_section: {wrapper: dimensions},
            payment_accounts_section: {wrapper: accounts},
            custom_remarks: {wrapper: customRemarks}},
        set_df_property: (field, property, value) => {properties[field + "." + property] = value;},
        toggle_display: (field, visible) => {properties[field + ".visible"] = visible;},
    };
    events.refresh(frm);
    assert.equal(properties["paid_from.label"], "Received From Account");
    assert.equal(properties["paid_to.label"], "Received To Account");
    assert.equal(properties["paid_amount.label"], "Received Amount");
    assert.equal(properties["party_section.label"], "Received From");
    assert.equal(properties["mode_of_payment.reqd"], 1);
    assert.equal(properties["custom_remarks.hidden"], 0);
    assert.equal(properties["custom_remarks.depends_on"], "");
    assert.equal(properties["custom_remarks.visible"], true);
    assert.equal("accounting_dimensions_section.collapsible" in properties, false);
    assert.equal(accountingDimensionsSection.expanded_by_user, true);
    assert.deepEqual(collapsed, [false]);
    assert.equal(accounts.before, amounts);
    assert.equal(amounts.after, customRemarks);
    assert.equal(customRemarks.after, dimensions);
    frm.doc.payment_type = "Pay";
    events.payment_type(frm);
    assert.equal(properties["party_section.label"], "Payment To");
    assert.equal(properties["paid_amount.label"], "Paid Amount");
});
