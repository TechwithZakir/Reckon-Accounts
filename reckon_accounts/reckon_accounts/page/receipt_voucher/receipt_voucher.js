frappe.pages["receipt-voucher"].on_page_load = function (wrapper) {
    reckon_accounts_make_voucher_page(wrapper, {
        title: __("Receipt Voucher"),
        directAgainst: "Direct Income",
        partyAgainst: "Customer / Receivable",
        partyPaymentType: "Receive",
        submitMethod: "reckon_accounts.api.direct_receipt_voucher",
        success: __("Receipt Voucher Created Successfully"),
        cashField: {fieldname: "received_to", label: __("Received To")},
        plField: {fieldname: "income_account", label: __("Income Account"), root_type: "Income"},
        counterparty: {fieldname: "received_from", label: __("Received From / Source")},
        partyButton: __("Open Customer Receipt Entry"),
        buildValues(values) {
            return {
                company: values.company,
                posting_date: values.posting_date,
                mode_of_payment: values.mode_of_payment,
                received_to: values.received_to,
                income_account: values.income_account,
                amount: values.amount,
                cost_center: values.cost_center,
                project: values.project,
                received_from: values.received_from,
                reference_number: values.reference_number,
                reference_date: values.reference_date,
                remarks: values.remarks,
                ...values.dimensions,
            };
        },
    });
};
