frappe.provide("reckon_accounts");

reckon_accounts.report_settings = function (report_name) {
    const api = "reckon_accounts.api.";
    const search = (scope_field, report = frappe.query_report) => ({
        query: api + "search_records",
        filters: {
            report_name, scope_field,
            company: report.get_filter_value("company"),
            party_type: report.get_filter_value("party_type"),
            voucher_type: report.get_filter_value("voucher_type"),
        },
    });
    const link = (fieldname, label, options, extra = {}) => ({
        fieldname, label: __(label), fieldtype: "Link", options,
        get_query: () => search(fieldname), ...extra,
    });
    const filters = [
        link("company", "Company", "Company", {reqd: 1, default: frappe.defaults.get_user_default("Company")}),
        {fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
            default: frappe.datetime.month_start()},
        {fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1,
            default: frappe.datetime.get_today()},
        link("fiscal_year", "Fiscal Year", "Fiscal Year"),
        link("account", "Ledger Account / Group", "Account"),
        {fieldname: "party_type", label: __("Party Type"), fieldtype: "Select", options: [""]},
        {fieldname: "party", label: __("Party"), fieldtype: "Dynamic Link", options: "party_type",
            get_query: () => search("party"), depends_on: "eval:doc.party_type && doc.party_type !== 'Other'"},
        {fieldname: "only_entries_without_party", label: __("Only Entries Without Party"),
            fieldtype: "Check", default: 0},
        link("voucher_type", "Source Voucher Type", "DocType"),
        {fieldname: "voucher_no", label: __("Source Voucher No"), fieldtype: "Dynamic Link",
            options: "voucher_type", get_query: () => search("voucher_no"), depends_on: "voucher_type"},
        {fieldname: "payment_type", label: __("Payment Type"), fieldtype: "Select",
            options: ["", "Receive", "Pay", "Internal Transfer"]},
        link("mode_of_payment", "Mode of Payment", "Mode of Payment"),
        {fieldname: "reference_no", label: __("Cheque / Reference"), fieldtype: "Data"},
        link("finance_book", "Finance Book", "Finance Book"),
        {fieldname: "include_default_book_entries", label: __("Include Default Book Entries"),
            fieldtype: "Check", default: 0},
        {fieldname: "show_opening_entries", label: __("Show Opening Vouchers as Movement"),
            fieldtype: "Check", default: 0},
        {fieldname: "currency_mode", label: __("Currency Mode"), fieldtype: "Select",
            options: [{label: __("Company currency"), value: "company"},
                {label: __("Account currency"), value: "account"}], default: "company"},
        {fieldname: "page", label: __("Page"), fieldtype: "Int", default: 1},
        {fieldname: "page_size", label: __("Entries per page"), fieldtype: "Int", default: 100},
        {fieldname: "dimensions", label: __("Dimensions"), fieldtype: "Data", hidden: 1, default: "{}"},
    ];
    if (report_name === "Funds Flow") {
        filters.push(link("current_assets_group", "Current Assets Group", "Account"));
        filters.push(link("current_liabilities_group", "Current Liabilities Group", "Account"));
    }
    if (report_name === "Party Summary") {
        filters.push(link("customer_group", "Customer Group", "Customer Group"));
        filters.push(link("supplier_group", "Supplier Group", "Supplier Group"));
        filters.push(link("territory", "Territory", "Territory"));
        filters.push({fieldname: "group_by", label: __("Group By"), fieldtype: "Select",
            options: ["Party", "Party Type", "Account Head", "customer_group", "supplier_group", "territory"], default: "Party"});
    }
    // Changing a balance filter returns to page 1; paging itself keeps the scope.
    for (const filter of filters) {
        if (filter.fieldname !== "page") {
            filter.on_change = async (report) => {
                if (report._no_refresh) return;
                report._no_refresh = true;
                try {
                    if (filter.fieldname === "party_type") await report.set_filter_value("party", "");
                    if (filter.fieldname === "voucher_type") await report.set_filter_value("voucher_no", "");
                    if (filter.fieldname === "company") {
                        for (const name of ["account", "party", "voucher_no", "finance_book", "fiscal_year"])
                            await report.set_filter_value(name, "");
                        if (report_name === "Funds Flow") {
                            await report.set_filter_value("current_assets_group", "");
                            await report.set_filter_value("current_liabilities_group", "");
                        }
                        await report.set_filter_value("dimensions", "{}");
                    }
                    await report.set_filter_value("page", 1);
                } finally { report._no_refresh = false; }
                return report.refresh();
            };
        }
    }
    return {
        filters,
        async onload(report) {
            const entries = {
                "Receipt Register": ["Payment Entry", "payment_type", "Receive"],
                "Payment Register": ["Payment Entry", "payment_type", "Pay"],
                "Contra Register": ["Payment Entry", "payment_type", "Internal Transfer"],
                "Journal Register": ["Journal Entry", "voucher_type", "Journal Entry"],
            };
            const entry = entries[report_name];
            if (entry && frappe.model.can_create(entry[0])) {
                report.page.add_inner_button(__("New Entry"), () => {
                    const company = report.get_filter_value("company");
                    if (!company) {
                        frappe.msgprint(__("Select Company before creating an entry."));
                        return;
                    }
                    frappe.new_doc(entry[0], {company, [entry[1]]: entry[2]});
                });
            }
            const options = await frappe.xcall(api + "filter_options", {report_name});
            const partyControl = report.get_filter("party_type");
            const selected = partyControl.get_value();
            partyControl.df.options = ["", ...options.party_types];
            partyControl.refresh();
            if (selected) await partyControl.set_value(selected);
            const exportFull = () => {
                const values = report.get_filter_values(true);
                if (!values) return;
                open_url_post(frappe.request.url, {
                    cmd: api + "export_ledger", report_name, filters: JSON.stringify(values),
                });
            };
            // QueryReport is reused when navigating to standard reports. Do not
            // leave their Export action bound to a previous Reckon report.
            if (!report._reckon_original_export) report._reckon_original_export = report.export_report.bind(report);
            report.export_report = function () {
                if (this.report_name === report_name) return exportFull();
                return this._reckon_original_export();
            };
            if (frappe.model.can_export("GL Entry"))
                report.page.add_inner_button(__("Export Full Ledger"), exportFull);
            report.page.add_inner_button(__("Previous Page"), () => {
                const page = report.get_filter_value("page") || 1;
                if (page > 1) report.set_filter_value("page", page - 1);
            });
            report.page.add_inner_button(__("Next Page"), () => {
                report.set_filter_value("page", (report.get_filter_value("page") || 1) + 1);
            });
            report.page.add_inner_button(__("Dimensions"), () => {
                const current = JSON.parse(report.get_filter_value("dimensions") || "{}");
                const fields = [];
                for (const dimension of options.dimensions) {
                    fields.push({fieldname: dimension.fieldname, label: dimension.label,
                        fieldtype: "MultiSelectList", options: dimension.doctype,
                        default: (current[dimension.fieldname] || []).filter(value => value !== null),
                        get_data: async (txt) => {
                            const query = search(dimension.fieldname, report);
                            const data = await frappe.xcall(query.query, {
                                doctype: dimension.doctype, txt: txt || "", searchfield: "name",
                                start: 0, page_len: 20, filters: query.filters,
                            });
                            return data.map(([value, description]) => ({value, description}));
                        }});
                    fields.push({fieldname: dimension.fieldname + "__blank", fieldtype: "Check",
                        label: __("Include blank {0}", [dimension.label]),
                        default: (current[dimension.fieldname] || []).includes(null) ? 1 : 0});
                }
                const dialog = new frappe.ui.Dialog({title: __("Accounting Dimensions"), fields,
                    primary_action_label: __("Apply"), primary_action: async (values) => {
                        const chosen = {};
                        for (const dimension of options.dimensions) {
                            const names = [...(values[dimension.fieldname] || [])];
                            if (values[dimension.fieldname + "__blank"]) names.push(null);
                            if (names.length) chosen[dimension.fieldname] = names;
                        }
                        dialog.hide();
                        await report.set_filter_value("dimensions", JSON.stringify(chosen));
                    }});
                dialog.show();
            });
        },
        formatter(value, row, column, data, default_formatter) {
            const safe = frappe.utils.escape_html(String(value ?? ""));
            if (column.fieldname === "party_name" && data?.row_kind === "party_summary") {
                const scope = {...frappe.query_report.get_filter_values(), account: data.account,
                    party_type: data.party_type || "", party: data.party || "", page: 1};
                for (const key of ["customer_group", "supplier_group", "territory", "group_by"]) delete scope[key];
                if (!data.party) scope.only_entries_without_party = 1;
                const query = new URLSearchParams();
                for (const [key, selected] of Object.entries(scope)) {
                    if (selected !== null && selected !== undefined) query.set(key, String(selected));
                }
                const href = "/app/query-report/" + encodeURIComponent("Party Ledger") + "?" + query;
                return `<a href="${frappe.utils.escape_html(href)}">${safe}</a>`;
            }
            if (column.fieldname === "description" && data?.row_kind === "monthly") {
                const scope = {...frappe.query_report.get_filter_values(),
                    from_date: data.posting_date, to_date: data.period_end, page: 1};
                if (data.account) scope.account = data.account;
                delete scope.current_assets_group;
                delete scope.current_liabilities_group;
                const target = report_name === "Group Monthly Summary" ? "Group Vouchers" : "Account Ledger";
                const query = new URLSearchParams();
                for (const [key, selected] of Object.entries(scope)) {
                    if (selected !== null && selected !== undefined) query.set(key, String(selected));
                }
                const href = "/app/query-report/" + encodeURIComponent(target) + "?" + query;
                return `<a href="${frappe.utils.escape_html(href)}">${safe}</a>`;
            }
            if (["party_heading", "account_heading"].includes(data?.row_kind)) {
                return column.fieldname === "description" ? `<strong>${safe}</strong>` : "";
            }
            if (column.fieldname === "account_name" && value && data?.account &&
                ["entry", "monthly", "summary", "exception", "funds", "working_capital"].includes(data?.row_kind)) {
                const scope = {...frappe.query_report.get_filter_values(), account: data.account, page: 1};
                delete scope.current_assets_group;
                delete scope.current_liabilities_group;
                if (data.row_kind === "monthly") {
                    scope.from_date = data.posting_date;
                    scope.to_date = data.period_end;
                }
                const query = new URLSearchParams();
                for (const [key, selected] of Object.entries(scope)) {
                    if (selected !== null && selected !== undefined) query.set(key, String(selected));
                }
                const target = report_name === "Group Summary" && data.is_group ? "Group Summary" : report_name === "Bank Summary" ? "Bank Book" : "Account Ledger";
                // A group summary may be drilled into until it reaches one ledger account.
                const href = "/app/query-report/" + encodeURIComponent(target) + "?" + query;
                return `<a href="${frappe.utils.escape_html(href)}">${safe}</a>`;
            }
            if (column.fieldname === "voucher_type" && data?.row_kind === "statistics") {
                const scope = {...frappe.query_report.get_filter_values(), voucher_type: value, page: 1};
                const href = "/app/query-report/" + encodeURIComponent("Day Book") + "?" + new URLSearchParams(scope);
                return `<a href="${frappe.utils.escape_html(href)}">${safe}</a>`;
            }
            if (column.fieldtype === "Data") return safe;
            // The framework formatter supplies escaped, real-source Dynamic Links.
            return default_formatter(value, row, column, data);
        },
    };
};
