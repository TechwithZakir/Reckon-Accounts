frappe.pages["payment-voucher"].on_page_load = function (wrapper) {
    reckon_accounts_make_voucher_page(wrapper, {
        title: __("Payment Voucher"),
        directAgainst: "Direct Expense",
        partyAgainst: "Supplier / Payable",
        partyPaymentType: "Pay",
        submitMethod: "reckon_accounts.api.direct_payment_voucher",
        success: __("Payment Voucher Created Successfully"),
        cashField: {fieldname: "paid_from", label: __("Paid From")},
        plField: {fieldname: "expense_account", label: __("Expense Account"), root_type: "Expense"},
        counterparty: {fieldname: "paid_to", label: __("Paid To / Beneficiary")},
        partyButton: __("Open Supplier Payment Entry"),
        buildValues(values) {
            return {
                company: values.company,
                posting_date: values.posting_date,
                mode_of_payment: values.mode_of_payment,
                paid_from: values.paid_from,
                expense_account: values.expense_account,
                amount: values.amount,
                cost_center: values.cost_center,
                project: values.project,
                paid_to: values.paid_to,
                reference_number: values.reference_number,
                reference_date: values.reference_date,
                remarks: values.remarks,
                ...values.dimensions,
            };
        },
    });
};
