frappe.ui.form.on("Task Management Settings", {
  refresh(frm) {
    frm.trigger("toggle_schedule_fields");
    if (!frm.is_new() && frappe.user.has_role("Task Management Administrator")) {
      frm.add_custom_button(__("Send Task Summary Now"), () => {
        frappe.confirm(__("Send the task summary now using the current recipients and template?"), () => {
          frappe.call({
            method: "qfap_adds.qfap_adds.task_management.scheduler.send_task_summary_now",
            freeze: true,
            freeze_message: __("Queueing task summary..."),
            callback: r => {
              if (r.message) frappe.msgprint({ title: __("Task Summary"), message: JSON.stringify(r.message), indicator: "green" });
              frm.reload_doc();
            }
          });
        });
      });
    }
  },
  summary_schedule_enabled(frm) { frm.trigger("toggle_schedule_fields"); },
  summary_frequency(frm) { frm.trigger("toggle_schedule_fields"); },
  toggle_schedule_fields(frm) {
    const enabled = !!frm.doc.summary_schedule_enabled;
    frm.toggle_display("summary_weekly_day", enabled && frm.doc.summary_frequency === "Weekly");
    frm.toggle_display("summary_monthly_day", enabled && frm.doc.summary_frequency === "Monthly");
  }
});
