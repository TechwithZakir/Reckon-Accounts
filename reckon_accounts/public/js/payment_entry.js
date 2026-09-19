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
        if (amounts && accounts && !$(amounts).data("reckon-moved")) {
            $(accounts).before(amounts);
            $(amounts).data("reckon-moved", true);
        }
        if (dimensions && amounts && !$(dimensions).data("reckon-moved")) {
            $(amounts).after(dimensions);
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
        arrange_sections(frm);
    }

    frappe.ui.form.on("Payment Entry", {
        setup: apply_payment_labels,
        refresh(frm) {
            apply_payment_labels(frm);
            expand_accounting_dimensions(frm);
        },
        payment_type: apply_payment_labels,
    });
})();
