frappe.ui.form.on("Project Indicator", {
 setup(frm){frm.__project_team_employees=[]; set_queries(frm);},
 async onload(frm){await load_team(frm); set_queries(frm);},
 async refresh(frm){await load_team(frm); set_queries(frm); frm.set_df_property("indicator_code","read_only",!cint(frm.doc.use_custom_code));},
 async project(frm){["project_result","sector","data_collection_responsible_employee","responsible_department"].forEach(f=>frm.set_value(f,"")); await load_team(frm); set_queries(frm);},
 project_result(frm){set_queries(frm);}, use_custom_code(frm){frm.set_df_property("indicator_code","read_only",!cint(frm.doc.use_custom_code));}
});
async function load_team(frm){frm.__project_team_employees=[]; if(!frm.doc.project)return; const r=await frappe.call({method:"qfap_adds.qfap_adds.project_management.api.get_project_team_employees",args:{project:frm.doc.project}}); frm.__project_team_employees=r.message||[];}
function set_queries(frm){frm.set_query("project_result",()=>({filters:{project:frm.doc.project||"",status:["!=","Inactive"]}})); const e=frm.__project_team_employees||[]; frm.set_query("data_collection_responsible_employee",()=>({filters:[["Employee","status","=","Active"],["Employee","name",e.length?"in":"=",e.length?e:"__none__"]]}));}
