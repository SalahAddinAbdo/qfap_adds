frappe.ui.form.on("Print Settings", {
  setup(frm) { const f=frm.fields_dict.qorg_rules?.grid?.get_field("document_type"); if(f) f.get_query=()=>({filters:{istable:0,issingle:0,is_virtual:0}}); },
  qorg_apply_formats(frm) { frappe.call({method:"qfap_adds.qfap_adds.project_management.print_settings_integration.apply_print_formats",freeze:true,freeze_message:__("Applying managed print formats..."),callback:()=>frm.reload_doc()}); }
});
