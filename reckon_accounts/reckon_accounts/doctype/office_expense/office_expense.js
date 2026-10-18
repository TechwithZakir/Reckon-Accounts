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
    frm.set_query("cost_center", () => ({
      query: "reckon_accounts.office_expense.get_office_expense_cost_centers",
      filters: { company: frm.doc.company },
    }));
    frm.set_query("cost_center", "items", () => ({
      query: "reckon_accounts.office_expense.get_office_expense_cost_centers",
      filters: { company: frm.doc.company },
    }));
    frm.set_query("project", () => ({
      query: "reckon_accounts.office_expense.get_office_expense_projects",
      filters: { company: frm.doc.company },
    }));
  },
  onload(frm) {
    frm.__officeExpenseCostCenter = frm.doc.cost_center;
  },
  refresh(frm) {
    loadOfficeExpenseDefaults(frm);
    updateOfficeExpenseTotal(frm);
  },
  company(frm) {
    frm.__officeExpenseDefaultsLoaded = false;
    frm.set_value("project", null);
    frm.set_value("cost_center", null);
    loadOfficeExpenseDefaults(frm);
  },
  cost_center(frm) {
    // Rows that followed the expense's cost center keep following it.
    const previous = frm.__officeExpenseCostCenter;
    (frm.doc.items || []).forEach((row) => {
      if (!row.cost_center || row.cost_center === previous) {
        row.cost_center = frm.doc.cost_center;
      }
    });
    frm.__officeExpenseCostCenter = frm.doc.cost_center;
    frm.refresh_field("items");
  },
  validate(frm) {
    updateOfficeExpenseTotal(frm);
  },
});

frappe.ui.form.on("Office Expense Item", {
  items_add(frm, cdt, cdn) {
    if (frm.doc.cost_center) {
      frappe.model.set_value(cdt, cdn, "cost_center", frm.doc.cost_center);
    }
  },
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
      if (frm.doc.docstatus === 0 && !frm.doc.cost_center && settings.default_cost_center) {
        frm.set_value("cost_center", settings.default_cost_center);
      }
      if (frm.is_new() && !frm.doc.items.length) {
        const row = frm.add_child("items");
        row.expense_category = settings.default_expense_account;
        row.cost_center = frm.doc.cost_center || settings.default_cost_center;
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
