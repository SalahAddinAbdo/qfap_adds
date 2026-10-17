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



// QFAP application report refinement layer
(function(){
    const report=frappe.query_report;
    const add_css=()=>{
        if(document.getElementById("qfap-project-report-style")) return;
        const style=document.createElement("style"); style.id="qfap-project-report-style";
        style.textContent=`
          .page-form{border-radius:10px;background:#f8fafc;padding:12px!important;margin-bottom:12px}
          .page-form .frappe-control{margin-bottom:6px}
          .report-summary{gap:8px;flex-wrap:wrap}
          .report-summary .summary-item{border-radius:10px;border:1px solid #e5e7eb;background:#fff;min-width:150px;padding:10px 14px}
          .datatable{border-radius:10px;overflow:hidden;border:1px solid #e5e7eb}
          .dt-header .dt-cell{background:#f1f5f9;font-weight:600}
          .dt-row:hover .dt-cell{background:#f8fafc}
          .qfap-critical{color:#b91c1c;font-weight:700}.qfap-warning{color:#b45309;font-weight:600}.qfap-good{color:#047857;font-weight:600}
        `; document.head.appendChild(style);
    };
    const format_status=(value)=>{
        const v=String(value||"");
        if(/critical|overdue|rejected|high/i.test(v)) return `<span class="qfap-critical">${frappe.utils.escape_html(v)}</span>`;
        if(/risk|due soon|pending|moderate|review/i.test(v)) return `<span class="qfap-warning">${frappe.utils.escape_html(v)}</span>`;
        if(/approved|completed|on track|verified|closed/i.test(v)) return `<span class="qfap-good">${frappe.utils.escape_html(v)}</span>`;
        return frappe.utils.escape_html(v);
    };
    add_css();
    if(report && report.columns){
        (report.columns||[]).forEach(col=>{
            const key=String(col.fieldname||"");
            if(/status|health|level|readiness|quality/.test(key) && !col.__qfap_formatter){
                const original=col.formatter; col.formatter=(value,row,column,data,default_formatter)=>format_status(value); col.__qfap_formatter=1;
            }
        });
    }
})();
