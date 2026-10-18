frappe.ui.form.on("Office Expense Settings", {
  setup(frm) {
    frm.set_query("expense_account", "categories", () => ({
      filters: { company: frm.doc.company, root_type: "Expense", is_group: 0, disabled: 0 },
    }));
    frm.set_query("payment_account", "payment_methods", () => ({
      filters: { company: frm.doc.company, is_group: 0, disabled: 0 },
    }));
    frm.set_query("default_cost_center", () => ({
      filters: { company: frm.doc.company, is_group: 0, disabled: 0 },
    }));
  },
});
