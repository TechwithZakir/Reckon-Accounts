(() => {
    const direct_subtypes = {
        "Direct Expense": {payment_type: "Pay", profit_loss_root_type: "Expense"},
        "Direct Income": {payment_type: "Receive", profit_loss_root_type: "Income"},
    };

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
            party_section: __("Party Details"),
        },
    };

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
        frm.set_df_property("party_section", "label", __("Party Details"));
        frm.set_df_property("mode_of_payment", "reqd", 1);
    }

    function apply_direct_layout(frm) {
        const direct = direct_subtypes[frm.doc.custom_voucher_subtype];
        const direct_mode = Boolean(direct);
        const native_paid_from_visibility =
            'eval:(in_list(["Internal Transfer", "Pay"], doc.payment_type) || doc.party)';
        const native_paid_to_visibility =
            'eval:(in_list(["Internal Transfer", "Receive"], doc.payment_type) || doc.party)';
        const direct_visibility = "eval:doc.payment_type && doc.custom_voucher_subtype";
        const native_amount_visibility = "eval:(doc.paid_to && doc.paid_from)";
        const direct_amount_visibility = "eval:!doc.custom_voucher_subtype";
        frm.set_df_property(
            "paid_from",
            "depends_on",
            direct_mode ? direct_visibility : native_paid_from_visibility,
        );
        frm.set_df_property(
            "paid_to",
            "depends_on",
            direct_mode ? direct_visibility : native_paid_to_visibility,
        );
        frm.set_df_property(
            "payment_amounts_section",
            "depends_on",
            native_amount_visibility,
        );
        for (const fieldname of [
            "received_amount", "received_amount_after_tax", "base_received_amount",
            "base_received_amount_after_tax", "target_exchange_rate",
        ]) {
            frm.set_df_property(fieldname, "depends_on", direct_mode ? direct_amount_visibility : null);
        }
        apply_dimension_visibility(frm, direct_mode, direct_visibility);
        const party_fields = [
            "party_section", "party_type", "party", "party_name", "bank_account",
            "party_bank_account", "contact_person", "contact_email",
            "book_advance_payments_in_separate_party_account", "reconcile_on_advance_payment_date",
            "apply_tds", "tax_withholding_category", "taxes_and_charges_section",
            "purchase_taxes_and_charges_template", "sales_taxes_and_charges_template", "taxes",
            "section_break_60", "base_total_taxes_and_charges", "column_break_61",
            "total_taxes_and_charges", "deductions_or_loss_section", "deductions",
            "section_tax_withholding_entry", "tax_withholding_group", "ignore_tax_withholding_threshold",
            "override_tax_withholding_entries", "tax_withholding_entries", "section_break_14",
            "references", "section_break_34", "total_allocated_amount", "base_total_allocated_amount",
            "unallocated_amount", "difference_amount", "write_off_difference_amount",
        ];
        for (const fieldname of party_fields) frm.toggle_display(fieldname, !direct_mode);

        if (!direct_mode) {
            frm.set_df_property("paid_from", "label", labels[frm.doc.payment_type]?.paid_from || __("Paid From"));
            frm.set_df_property("paid_to", "label", labels[frm.doc.payment_type]?.paid_to || __("Paid To"));
            return;
        }

        const is_expense = frm.doc.custom_voucher_subtype === "Direct Expense";
        frm.set_df_property(
            "payment_accounts_section",
            "label",
            is_expense ? __("Expense Payment Accounts") : __("Income Receipt Accounts"),
        );
        frm.set_df_property("paid_from", "label", is_expense ? __("Paid From (Cash / Bank)") : __("Income Account"));
        frm.set_df_property("paid_to", "label", is_expense ? __("Expense Account") : __("Received To (Cash / Bank)"));
        frm.set_df_property("paid_amount", "label", is_expense ? __("Paid Amount") : __("Received Amount"));
        frm.set_df_property("received_amount", "label", is_expense ? __("Expense Amount") : __("Received Amount"));
    }

    function apply_dimension_visibility(frm, direct_mode, direct_visibility) {
        const dimension_fields = ["accounting_dimensions_section", "cost_center", "project"];
        for (const fieldname of dimension_fields) {
            frm.set_df_property(fieldname, "depends_on", direct_mode ? direct_visibility : null);
            frm.toggle_display(fieldname, true);
        }

        if (!direct_mode) return;
        const section = frm.layout?.sections_dict?.accounting_dimensions_section;
        if (section?.collapse) {
            section.expanded_by_user = true;
            section.collapse(false);
        }
    }

    function set_account_queries(frm) {
        const direct = direct_subtypes[frm.doc.custom_voucher_subtype];
        const standard_account_types = fieldname => {
            if (frm.doc.payment_type === "Internal Transfer") return ["Bank", "Cash"];
            if (fieldname === "paid_from" && frm.doc.payment_type === "Pay") return ["Bank", "Cash"];
            if (fieldname === "paid_to" && frm.doc.payment_type === "Receive") return ["Bank", "Cash"];
            return frm.doc.party_type && frappe.boot.party_account_types
                ? [frappe.boot.party_account_types[frm.doc.party_type]]
                : [];
        };
        frm.set_query("paid_from", () => {
            const filters = {company: frm.doc.company, is_group: 0};
            if (direct?.payment_type === "Receive") filters.root_type = "Income";
            else filters.account_type = ["in", direct ? ["Bank", "Cash"] : standard_account_types("paid_from")];
            return {filters};
        });
        frm.set_query("paid_to", () => {
            const filters = {company: frm.doc.company, is_group: 0};
            if (direct?.payment_type === "Pay") filters.root_type = "Expense";
            else filters.account_type = ["in", direct ? ["Bank", "Cash"] : standard_account_types("paid_to")];
            return {filters};
        });
    }

    function apply_customization(frm) {
        apply_payment_labels(frm);
        apply_direct_layout(frm);
        set_account_queries(frm);
    }

    frappe.ui.form.on("Payment Entry", {
        setup: apply_customization,
        refresh(frm) {
            apply_customization(frm);
            expand_accounting_dimensions(frm);
        },
        payment_type(frm) {
            const direct = direct_subtypes[frm.doc.custom_voucher_subtype];
            if (direct && frm.doc.payment_type !== direct.payment_type) {
                frm.set_value("custom_voucher_subtype", "Party Settlement");
            }
            apply_customization(frm);
        },
        custom_voucher_subtype(frm) {
            const direct = direct_subtypes[frm.doc.custom_voucher_subtype];
            if (direct) {
                frm.set_value("payment_type", direct.payment_type);
                for (const fieldname of ["party_type", "party", "party_name", "paid_from", "paid_to"]) {
                    frm.set_value(fieldname, null);
                }
            }
            apply_customization(frm);
        },
    });
})();
