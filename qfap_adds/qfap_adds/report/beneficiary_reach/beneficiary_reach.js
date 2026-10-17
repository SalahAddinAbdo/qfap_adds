function beneficiary_context_options(fieldname, txt) {
 const report = frappe.query_report;
 const rows = (report && report.data) || [];
 const selectedGovernors = (report && report.get_filter_value("governorates")) || [];
 const selectedProjects = (report && report.get_filter_value("projects")) || [];
 const values = new Set();
 rows.forEach(row => {
  if (selectedProjects.length && row.project && !selectedProjects.includes(row.project)) return;
  if (fieldname === "district" && selectedGovernors.length && row.governorate && !selectedGovernors.includes(row.governorate)) return;
  let raw = row[fieldname];
  if (fieldname === "donors" && !raw) raw = row.donor;
  if (fieldname === "sector" && !raw) raw = row.sectors;
  if (fieldname === "implementing_partner" && !raw) raw = row.implementing_partners;
  if (!raw) return;
  String(raw).split(",").map(v => v.trim()).filter(Boolean).forEach(v => values.add(v));
 });
 const q = String(txt || "").toLowerCase();
 return Array.from(values).filter(v => v.toLowerCase().includes(q)).sort().map(v => ({value:v, description:v}));
}

frappe.query_reports["Beneficiary Reach"] = {
 filters: [
  {fieldname:"view",label:__("View"),fieldtype:"Select",options:["Executive Reach","Demographic","Geographic","Sector","Partner","Period Performance","Full"],default:"Executive Reach"},
  {fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",options:"Project",get_data:txt=>frappe.db.get_link_options("Project",txt)},
  {fieldname:"governorates",label:__("Governorates"),fieldtype:"MultiSelectList",get_data:txt=>beneficiary_context_options("governorate",txt)},
  {fieldname:"districts",label:__("Districts"),fieldtype:"MultiSelectList",get_data:txt=>beneficiary_context_options("district",txt)},
  {fieldname:"sectors",label:__("Sectors"),fieldtype:"MultiSelectList",get_data:txt=>beneficiary_context_options("sector",txt)},
  {fieldname:"implementing_partners",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data:txt=>beneficiary_context_options("implementing_partner",txt)},
  {fieldname:"donors",label:__("Donors"),fieldtype:"MultiSelectList",get_data:txt=>beneficiary_context_options("donors",txt)},
  {fieldname:"plan_statuses",label:__("Plan Statuses"),fieldtype:"MultiSelectList",get_data:txt=>["Draft","Approved","Under Implementation","Actuals Finalized","Cancelled"].filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
  {fieldname:"tracking_modes",label:__("Tracking Modes"),fieldtype:"MultiSelectList",get_data:txt=>["Aggregate Only","Named Lists Only","Mixed"].filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
  {fieldname:"reach_types",label:__("Reach Types"),fieldtype:"MultiSelectList",get_data:txt=>["Direct","Indirect"].filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
  {fieldname:"primary_units",label:__("Primary Units"),fieldtype:"MultiSelectList",get_data:txt=>["Individuals","Households","Service Contacts","Institutions","Facilities","Communities","Groups","Other"].filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
  {fieldname:"data_quality",label:__("Data Quality"),fieldtype:"MultiSelectList",get_data:txt=>["Not Yet Available","Measured","Verified Administrative Record","Estimated","Projected"].filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
  {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},
  {fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
  {fieldname:"below_target_only",label:__("Below Target Only"),fieldtype:"Check",default:0},
  {fieldname:"missing_updates_only",label:__("Missing Updates Only"),fieldtype:"Check",default:0},
  {fieldname:"quality_issues_only",label:__("Quality Issues Only"),fieldtype:"Check",default:0},
  {fieldname:"include_drafts",label:__("Include Draft Plans"),fieldtype:"Check",default:0},
  {fieldname:"include_cancelled",label:__("Include Cancelled Plans"),fieldtype:"Check",default:0}
 ],
 formatter(value,row,column,data,default_formatter){
  let v=default_formatter(value,row,column,data);
  if(!data) return v;
  const statusFields=["reach_status","data_quality_status","beneficiary_attention"];
  if(statusFields.includes(column.fieldname)){
   const s=String(value||"");
   const color=(["Issue","Review Required","Below Target","Not Reported","Not Planned"].includes(s)?"red":s==="Exceeded Target"?"orange":["Target Achieved","Valid","No Immediate Issue"].includes(s)?"green":"blue");
   return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(s)}</span>`;
  }
  if(["individual_achievement","household_achievement","pwd_achievement"].includes(column.fieldname)){
   const n=flt(value); const c=n<70?"red":n<90?"orange":n<=110?"green":"blue";
   return `<span style="color:var(--${c}-600);font-weight:600">${v}</span>`;
  }
  return v;
 },
 onload(report){
  ["projects","governorates","sectors","implementing_partners","donors"].forEach(name=>{
   const f=report.get_filter(name); if(f && f.df) f.df.onchange=()=>{
    if(name==="governorates") report.set_filter_value("districts",[]);
    report.refresh();
   };
  });
  report.page.add_inner_button(__("Reset Filters"),()=>{
   (report.filters||[]).forEach(f=>f.set_value(f.df.fieldname==="view"?"Executive Reach":(f.df.fieldtype==="Check"?0:null)));
   report.refresh();
  });
  const style=document.createElement("style");
  style.textContent='.query-report .dt-cell__content{white-space:normal!important;line-height:1.35}.query-report .dt-row{min-height:34px}';
  document.head.appendChild(style);
 }
};

// QFAP KPI card refinement. Column freezing is native through sticky: true.
;(function qfap_kpi_card_refinement(){
 const STYLE_ID="qfap-kpi-card-refinement-v282";
 if(document.getElementById(STYLE_ID)) return;
 const style=document.createElement("style");
 style.id=STYLE_ID;
 style.textContent=`
  .query-report .report-summary{display:flex!important;gap:10px!important;align-items:stretch!important;flex-wrap:wrap!important;overflow:visible!important;padding:6px 0 12px!important}
  .query-report .report-summary .summary-item,.query-report [class*="kpi-card"],.query-report .qfap-kpi-card{height:auto!important;min-height:72px!important;overflow:visible!important;padding:11px 14px!important;display:flex!important;flex-direction:column!important;justify-content:center!important}
  .query-report .report-summary .summary-item .summary-label,.query-report .report-summary .summary-item .text-muted,.query-report [class*="kpi-card"] .label{height:auto!important;max-height:none!important;overflow:visible!important;white-space:normal!important;line-height:1.35!important;padding:0 0 4px!important}
  .query-report .report-summary .summary-item .summary-value,.query-report [class*="kpi-card"] .value{line-height:1.25!important;overflow:visible!important}
 `;
 document.head.appendChild(style);
})();


// QFAP Link title display v2.8.4.
;(function qfap_link_title_display(){
 const config=frappe.query_reports["Beneficiary Reach"];
 if(!config||config.__qfap_link_titles_wrapped) return;
 const original=config.formatter;
 config.formatter=function(value,row,column,data,default_formatter){
  let rendered=original?original.call(this,value,row,column,data,default_formatter):default_formatter(value,row,column,data);
  if(data&&column&&column.fieldtype==="Link"&&column.fieldname){
   const title=data[column.fieldname+"__title"];
   if(title&&String(title)!==String(value||"")){
    rendered+=`<span class="qfap-link-title"><span class="qfap-link-title-separator" aria-hidden="true">&nbsp;-&nbsp;</span>${frappe.utils.escape_html(String(title))}</span>`;
   }
  }
  return rendered;
 };
 config.__qfap_link_titles_wrapped=true;
})();

;(function qfap_link_title_style(){
 const id="qfap-link-title-style-v284";if(document.getElementById(id))return;
 const s=document.createElement("style");s.id=id;s.textContent=`.query-report .qfap-link-title{display:inline;color:var(--text-muted,#6b7280);font-size:11px;line-height:1.25;white-space:normal}.query-report .qfap-link-title-separator{color:var(--text-muted,#6b7280)}`;document.head.appendChild(s);
})();
