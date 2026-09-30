function reckon_accounts_make_voucher_page(wrapper, config) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: config.title, single_column: true});
    const routeOptions = frappe.route_options || {};
    frappe.route_options = null;
    const body = $("<div class='reckon-voucher p-4'></div>").appendTo(page.main);
    const form = $("<div class='container-fluid px-0'></div>").appendTo(body);
    const controls = {};
    const dimensionControls = {};
    let submitting = false;

    const add = (parent, field, column = "col-md-6") => {
        const cell = $(`<div class='${column}'></div>`).appendTo(parent);
        const control = frappe.ui.form.make_control({parent: cell, df: field, render_input: true});
        control.refresh();
        controls[field.fieldname] = control;
        return control;
    };

    const heading = (parent, label) => $("<h4 class='mt-3 mb-3'></h4>").text(__(label)).appendTo(parent);
    const headerGrid = $("<div class='row'></div>").appendTo(form);
    add(headerGrid, {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
        reqd: 1, default: routeOptions.company || frappe.defaults.get_user_default("Company")});
    add(headerGrid, {fieldname: "posting_date", label: __("Posting Date"), fieldtype: "Date",
        reqd: 1, default: routeOptions.posting_date || frappe.datetime.get_today()});

    heading(form, config.detailsTitle || "Payment Details");
    const detailsGrid = $("<div class='row'></div>").appendTo(form);
    add(detailsGrid, {fieldname: "voucher_against", label: __("Voucher Against"), fieldtype: "Select",
        options: [config.directAgainst, config.partyAgainst].join("\n"), reqd: 1,
        default: routeOptions.voucher_against || config.directAgainst});
    add(detailsGrid, {fieldname: "mode_of_payment", label: __("Mode of Payment"), fieldtype: "Link",
        options: "Mode of Payment"});
    add(detailsGrid, {fieldname: "remarks", label: __("Custom Remarks"), fieldtype: "Small Text"}, "col-md-6 offset-md-6");

    const directSection = $("<div class='border-top mt-4 pt-2'></div>").appendTo(form);
    heading(directSection, config.directSectionTitle || "Payment From / To");
    const directGrid = $("<div class='row'></div>").appendTo(directSection);
    const addDirect = field => {
        return add(directGrid, field, field.column || "col-md-6");
    };

    addDirect({fieldname: config.cashField.fieldname, label: config.cashField.label, fieldtype: "Link",
        options: "Account", reqd: 1, get_query: () => ({filters: {
            company: controls.company.get_value(), is_group: 0, account_type: ["in", ["Cash", "Bank"]],
        }})});
    addDirect({fieldname: config.plField.fieldname, label: config.plField.label, fieldtype: "Link",
        options: "Account", reqd: 1, get_query: () => ({filters: {
            company: controls.company.get_value(), is_group: 0, root_type: config.plField.root_type,
        }})});
    addDirect({fieldname: "amount", label: __("Amount"), fieldtype: "Currency", reqd: 1});
    addDirect({fieldname: "cost_center", label: __("Cost Center"), fieldtype: "Link",
        options: "Cost Center", get_query: () => ({filters: {company: controls.company.get_value()}})});
    addDirect({fieldname: "project", label: __("Project"), fieldtype: "Link",
        options: "Project", get_query: () => ({filters: {company: controls.company.get_value()}})});
    addDirect({fieldname: config.counterparty.fieldname, label: config.counterparty.label, fieldtype: "Data"});
    addDirect({fieldname: "reference_number", label: __("Reference Number"), fieldtype: "Data"});
    addDirect({fieldname: "reference_date", label: __("Reference Date"), fieldtype: "Date"});
    const attachment = addDirect({fieldname: "attachment", label: __("Attachment"), fieldtype: "Attach"});

    const dimensionsSection = $("<div class='row'></div>").appendTo(directSection);
    frappe.call({method: "reckon_accounts.api.voucher_accounting_dimensions"}).then(result => {
        for (const dim of result.message || []) {
            const control = add(dimensionsSection, {fieldname: dim.fieldname, label: __(dim.label), fieldtype: "Link", options: dim.doctype});
            dimensionControls[dim.fieldname] = control;
        }
    });

    const resultBox = $("<div class='mt-3'></div>").appendTo(form);
    const submit = page.add_action_item(__("Submit"), () => submitDirect());
    const createAnother = page.add_action_item(__("Create Another"), () => {
        resultBox.empty();
        for (const field of ["amount", config.cashField.fieldname, config.plField.fieldname,
            config.counterparty.fieldname, "reference_number", "reference_date", "remarks", "attachment"]) {
            controls[field]?.set_value("");
        }
    });
    $(createAnother).hide();

    const toggle = () => {
        const direct = controls.voucher_against.get_value() === config.directAgainst;
        directSection.toggle(direct);
        $(submit).toggle(direct);
        if (!direct) {
            openPaymentEntry();
        }
    };

    controls.voucher_against.$input.on("change.reckonVoucher", toggle);
    controls.mode_of_payment.$input.on("change.reckonVoucher", defaultAccount);
    controls.company.$input.on("change.reckonVoucher", defaultAccount);
    toggle();

    async function defaultAccount() {
        const company = controls.company.get_value();
        const mode = controls.mode_of_payment.get_value();
        if (!company || !mode) return;
        const response = await frappe.call({
            method: "reckon_accounts.api.default_payment_account",
            args: {company, mode_of_payment: mode},
        });
        if (response.message) {
            controls[config.cashField.fieldname].set_value(response.message);
        }
    }

    function values() {
        const data = {};
        for (const [field, control] of Object.entries(controls)) {
            data[field] = control.get_value();
        }
        data.dimensions = {};
        for (const [field, control] of Object.entries(dimensionControls)) {
            data.dimensions[field] = control.get_value();
        }
        return data;
    }

    async function submitDirect() {
        if (submitting) return;
        submitting = true;
        resultBox.empty();
        try {
            const response = await frappe.call({
                method: config.submitMethod,
                args: {values: config.buildValues(values())},
            });
            showResult(response.message);
            if (attachment.get_value()) {
                await attachFile(attachment.get_value(), response.message);
            }
            $(createAnother).show();
        } finally {
            submitting = false;
        }
    }

    function showResult(result) {
        const rows = (result.accounts || []).map(row => {
            const type = row.debit ? "Dr" : "Cr";
            const amount = format_currency(row.debit || row.credit);
            return $("<div></div>").text(`${row.account} ${type} ${amount}`);
        });
        const view = $("<button type='button' class='btn btn-primary btn-sm mr-2'></button>")
            .text(__("View Accounting Entry"))
            .on("click", () => frappe.set_route("Form", result.doctype, result.name));
        const print = $("<button type='button' class='btn btn-default btn-sm'></button>")
            .text(__("Print Voucher"))
            .on("click", () => frappe.set_route("print", result.doctype, result.name, config.title));
        resultBox.append(
            $("<div class='alert alert-success'></div>").append(
                $("<h4></h4>").text(config.success),
                $("<div class='font-weight-bold mb-2'></div>").text(result.voucher_number),
                rows,
                $("<div class='mt-3'></div>").append(view, print),
            ),
        );
    }

    function openPaymentEntry() {
        if (!frappe.model.can_create("Payment Entry")) {
            return frappe.msgprint(__("You do not have permission to create Payment Entry."));
        }
        frappe.new_doc("Payment Entry", {
            company: controls.company.get_value(),
            posting_date: controls.posting_date.get_value(),
            payment_type: config.partyPaymentType,
        });
    }

    async function attachFile(fileUrl, target) {
        const found = await frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "File",
                filters: {file_url: fileUrl},
                fields: ["name"],
                limit_page_length: 1,
            },
        });
        const file = found.message?.[0]?.name;
        if (!file) return;
        await frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: "File",
                name: file,
                fieldname: {
                    attached_to_doctype: target.doctype,
                    attached_to_name: target.name,
                    attached_to_field: null,
                },
            },
        });
    }
}
