frappe.ui.form.on("Task Assignment Request", {
  setup(frm) {
    frm.set_query("requested_assignee", () => ({ filters: { status: "Active" } }));
    frappe.call({ method: "qfap_adds.qfap_adds.task_management.api.task_assignment_scope", callback: r => {
      frm.__working_hours_per_day = flt((r.message || {}).working_hours_per_day || 8);
      calculate_request_schedule(frm, false);
    }});
  },
  refresh(frm) {
    const locked = ["Approved", "Rejected", "Applied", "Application Failed"].includes(frm.doc.workflow_state);
    ["subject", "description", "requested_assignee", "company", "task_type", "project", "parent_task", "priority", "exp_start_date", "exp_end_date", "expected_time", "request_reason"]
      .forEach(fieldname => frm.set_df_property(fieldname, "read_only", locked ? 1 : 0));
    if (!locked) {
      frm.set_intro(__("Complete all fields marked with an asterisk before submitting the request for approval. The approved request will automatically create and assign the Task to the selected Employee."), "blue");
    }
    calculate_request_schedule(frm, false);
    if (frm.doc.created_task) frm.add_custom_button(__("Open Created Task"), () => frappe.set_route("Form", "Task", frm.doc.created_task));
  },
  requested_assignee(frm) {
    if (!frm.doc.requested_assignee) return;
    frappe.db.get_value("Employee", frm.doc.requested_assignee, ["company", "user_id"]).then(r => {
      const employee = r.message || {};
      if (!frm.doc.company && employee.company) frm.set_value("company", employee.company);
      if (!employee.user_id) frappe.msgprint(__("The selected Employee is not linked to a User."));
    });
  },
  exp_start_date(frm) { calculate_request_schedule(frm, true); },
  exp_end_date(frm) { calculate_request_schedule(frm, true); }
});

function calculate_request_schedule(frm, forceHours) {
  if (!frm.doc.exp_start_date || !frm.doc.exp_end_date) return;
  const start = frappe.datetime.str_to_obj(frm.doc.exp_start_date);
  const end = frappe.datetime.str_to_obj(frm.doc.exp_end_date);
  if (!start || !end || end < start) return;
  const startDate = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  const endDate = new Date(end.getFullYear(), end.getMonth(), end.getDate());
  const days = Math.round((endDate - startDate) / 86400000) + 1;
  frm.set_value("expected_days", flt(days, 2));
  if (forceHours || flt(frm.doc.expected_time || 0) <= 0) {
    frm.set_value("expected_time", flt(days * flt(frm.__working_hours_per_day || 8), 2));
  }
}
