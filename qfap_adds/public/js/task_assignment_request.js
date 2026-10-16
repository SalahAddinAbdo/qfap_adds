frappe.ui.form.on("Task Assignment Request", {
  setup(frm) {
    frm.set_query("requested_assignee", () => ({ filters: { status: "Active" } }));
  },

  requested_assignee(frm) {
    if (!frm.doc.requested_assignee) return;
    frappe.db.get_value("Employee", frm.doc.requested_assignee, ["company", "user_id"]).then(r => {
      const employee = r.message || {};
      if (!frm.doc.company && employee.company) frm.set_value("company", employee.company);
      if (!employee.user_id) frappe.msgprint(__("The selected Employee is not linked to a User."));
    });
  },

  refresh(frm) {
    const locked = ["Approved", "Rejected", "Applied", "Application Failed"].includes(frm.doc.workflow_state);
    ["subject", "description", "requested_assignee", "company", "task_type", "project", "parent_task", "priority", "exp_start_date", "exp_end_date", "expected_time", "request_reason"]
      .forEach(fieldname => frm.set_df_property(fieldname, "read_only", locked ? 1 : 0));
    if (frm.doc.created_task) {
      frm.add_custom_button(__("Open Created Task"), () => frappe.set_route("Form", "Task", frm.doc.created_task));
    }
  }
});
