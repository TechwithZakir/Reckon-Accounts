frappe.ui.form.on("Office Expense", {
  setup(frm) {
    frm.set_query("payment_method", () => ({
      query: "reckon_accounts.office_expense.get_office_expense_payment_methods",
      filters: { company: frm.doc.company },
    }));
    frm.set_query("expense_category", "items", () => ({
      query: "reckon_accounts.office_expense.get_office_expense_categories",
      filters: { company: frm.doc.company },
    }));
  },
  refresh(frm) {
    loadOfficeExpenseDefaults(frm);
    updateOfficeExpenseTotal(frm);
  },
  company(frm) {
    frm.__officeExpenseDefaultsLoaded = false;
    loadOfficeExpenseDefaults(frm);
  },
  validate(frm) {
    updateOfficeExpenseTotal(frm);
  },
});

frappe.ui.form.on("Office Expense Item", {
  amount(frm) {
    updateOfficeExpenseTotal(frm);
  },
});

function loadOfficeExpenseDefaults(frm) {
  if (frm.__officeExpenseDefaultsLoading || frm.__officeExpenseDefaultsLoaded) return;
  frm.__officeExpenseDefaultsLoading = true;
  frappe
    .call({
      method: "reckon_accounts.office_expense.get_office_expense_defaults",
      args: { company: frm.doc.company || null },
    })
    .then((response) => {
      const settings = response.message || {};
      if (!settings.configured) {
        frm.set_intro(
          __("Office Expense Setup is required before an expense can be submitted."),
          "orange"
        );
        return;
      }
      frm.__officeExpenseDefaultsLoaded = true;
      if (!frm.doc.payment_method) frm.set_value("payment_method", settings.default_payment_method);
      if (frm.is_new() && !frm.doc.items.length) {
        const row = frm.add_child("items");
        row.expense_category = settings.default_expense_account;
        frm.refresh_field("items");
      }
    })
    .finally(() => {
      frm.__officeExpenseDefaultsLoading = false;
    });
}

function updateOfficeExpenseTotal(frm) {
  const total = (frm.doc.items || []).reduce((sum, row) => sum + flt(row.amount), 0);
  frm.doc.total_amount = total;
  frm.refresh_field("total_amount");
}
