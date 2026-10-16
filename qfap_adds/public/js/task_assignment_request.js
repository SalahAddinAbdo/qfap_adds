frappe.ui.form.on("Task Assignment Request", {
  refresh(frm) {
    const locked = ["Approved","Rejected","Applied","Application Failed"].includes(frm.doc.workflow_state);
    ["subject","description","requested_assignee","project","parent_task","priority","exp_start_date","exp_end_date","expected_time","request_reason"].forEach(f => frm.set_df_property(f,"read_only",locked ? 1 : 0));
    if (frm.doc.created_task) frm.add_custom_button(__("Open Created Task"), () => frappe.set_route("Form","Task",frm.doc.created_task));
  }
});
