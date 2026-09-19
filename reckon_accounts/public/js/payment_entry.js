(() => {
    const labels = {
        Receive: {
            paid_from: __("Received From Account"),
            paid_to: __("Received To Account"),
            paid_amount: __("Received Amount"),
            party_section: __("Received From"),
        },
        Pay: {
            paid_from: __("Account Paid From"),
            paid_to: __("Account Paid To"),
            paid_amount: __("Paid Amount"),
            party_section: __("Payment To"),
        },
        "Internal Transfer": {
            paid_from: __("Account Paid From"),
            paid_to: __("Account Paid To"),
            paid_amount: __("Paid Amount"),
            party_section: __("Payment From / To"),
        },
    };

    function arrange_sections(frm) {
        const dimensions = frm.fields_dict.accounting_dimensions_section?.wrapper;
        const amounts = frm.fields_dict.payment_amounts_section?.wrapper;
        const accounts = frm.fields_dict.payment_accounts_section?.wrapper;
        const remarks = frm.fields_dict.remarks?.wrapper;
        if (amounts && accounts && !$(amounts).data("reckon-moved")) {
            $(accounts).before(amounts);
            $(amounts).data("reckon-moved", true);
        }
        let remarksSection = frm.$wrapper.find(".reckon-custom-remarks-section").first();
        if (!remarksSection.length && amounts) {
            remarksSection = $(
                '<div class="form-section reckon-custom-remarks-section">' +
                    '<div class="section-body">' +
                        '<div class="row">' +
                            '<div class="form-column col-sm-6 reckon-custom-remarks-column"></div>' +
                            '<div class="form-column col-sm-6"></div>' +
                        "</div>" +
                    "</div>" +
                "</div>"
            );
            $(amounts).after(remarksSection);
        }
        if (remarks && remarksSection.length && !$(remarks).data("reckon-moved")) {
            remarksSection.find(".reckon-custom-remarks-column").append(remarks);
            $(remarks).data("reckon-moved", true);
        }
        if (dimensions && remarksSection.length && !$(dimensions).data("reckon-moved")) {
            remarksSection.after(dimensions);
            $(dimensions).data("reckon-moved", true);
        }
    }

    function expand_accounting_dimensions(frm) {
        const section = frm.layout?.sections_dict?.accounting_dimensions_section;
        if (!section?.collapse) {
            return;
        }

        section.expanded_by_user = true;
        section.collapse(false);
    }

    function apply_payment_labels(frm) {
        const selected = labels[frm.doc.payment_type] || labels["Internal Transfer"];
        for (const [fieldname, label] of Object.entries(selected)) {
            frm.set_df_property(fieldname, "label", label);
        }
        frm.set_df_property("mode_of_payment", "reqd", 1);
        frm.set_df_property("custom_remarks", "hidden", 1);
        frm.toggle_display("custom_remarks", false);
        frm.set_df_property("remarks", "label", __("Custom Remarks"));
        frm.set_df_property("remarks", "hidden", 0);
        frm.set_df_property("remarks", "depends_on", "");
        frm.set_df_property("remarks", "read_only", 0);
        frm.set_df_property("remarks", "read_only_depends_on", "");
        frm.toggle_display("remarks", true);
        arrange_sections(frm);
    }

    frappe.ui.form.on("Payment Entry", {
        setup: apply_payment_labels,
        refresh(frm) {
            apply_payment_labels(frm);
            expand_accounting_dimensions(frm);
        },
        payment_type: apply_payment_labels,
        remarks(frm) {
            if (!frm.doc.custom_remarks) {
                frm.set_value("custom_remarks", 1);
            }
        },
    });
})();
