frappe.ui.form.on("Task Management Settings", {
  refresh(frm) {
    frm.trigger("toggle_schedule_fields");
    if (frm.is_new() || !frappe.user.has_role("Task Management Administrator")) return;
    frm.add_custom_button(__("Preview Task Summary"), () => open_summary_dialog(frm, "preview"), __("Task Summary"));
    frm.add_custom_button(__("Send Test Email"), () => open_summary_dialog(frm, "test"), __("Task Summary"));
    frm.add_custom_button(__("Send Task Summary Now"), () => {
      frappe.confirm(__("Send the Task summary now using the current settings?"), () => frappe.call({method:"qfap_adds.qfap_adds.task_management.scheduler.send_task_summary_now",freeze:true,callback:() => frm.reload_doc()}));
    }, __("Task Summary"));
  },
  summary_schedule_enabled(frm) { frm.trigger("toggle_schedule_fields"); },
  summary_frequency(frm) { frm.trigger("toggle_schedule_fields"); },
  summary_period_mode(frm) { frm.trigger("toggle_schedule_fields"); },
  toggle_schedule_fields(frm) {
    const enabled=!!frm.doc.summary_schedule_enabled;
    frm.toggle_display("summary_weekly_day", enabled && frm.doc.summary_frequency==="Weekly");
    frm.toggle_display("summary_monthly_day", enabled && frm.doc.summary_frequency==="Monthly");
    frm.toggle_display("summary_rolling_days", frm.doc.summary_period_mode==="Custom Rolling Days");
  }
});

function open_summary_dialog(frm, mode) {
  const fields=[
    {fieldname:"employee",label:__("Employee"),fieldtype:"Link",options:"Employee",reqd:1,get_query:()=>({filters:{status:"Active"}})},
    {fieldname:"reference_date",label:__("Reference Date"),fieldtype:"Date",default:frappe.datetime.get_today(),reqd:1}
  ];
  if (mode==="test") fields.push({fieldname:"recipient",label:__("Test Recipient"),fieldtype:"Data",options:"Email",reqd:1});
  const dialog=new frappe.ui.Dialog({title:mode==="preview"?__("Preview Task Summary"):__("Send Test Email"),fields,primary_action_label:mode==="preview"?__("Preview"):__("Send"),primary_action(values){
    const method=mode==="preview"?"qfap_adds.qfap_adds.task_management.scheduler.preview_task_summary":"qfap_adds.qfap_adds.task_management.scheduler.send_test_summary";
    frappe.call({method,args:values,freeze:true,callback:r=>{
      if (mode==="preview") {
        const preview=new frappe.ui.Dialog({title:__("Task Summary Preview"),size:"extra-large",fields:[{fieldname:"html",fieldtype:"HTML"}]});
        preview.fields_dict.html.$wrapper.html(r.message||""); preview.show();
      } else frappe.msgprint(__("The test email has been queued."));
      dialog.hide();
    }});
  }}); dialog.show();
}
