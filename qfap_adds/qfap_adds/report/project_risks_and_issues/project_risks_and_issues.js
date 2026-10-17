function ria_values(fields,txt){const q=String(txt||"").toLowerCase(),m={};((frappe.query_report&&frappe.query_report.data)||[]).forEach(r=>{fields.forEach(f=>String(r[f]||"").split(",").map(x=>x.trim()).filter(Boolean).forEach(x=>{if(!m[x])m[x]=[];const p=r.project_name||r.project;if(p&&!m[x].includes(p))m[x].push(p);}));});return Object.keys(m).filter(x=>x.toLowerCase().includes(q)).sort().map(x=>({value:x,description:`${m[x].length} project(s) • ${m[x].slice(0,3).join(" • ")}`}));}
const RIA_LEVELS=["Not Assessed","Low","Moderate","High","Critical"],RIA_MON=["Not Assessed","Not Due","Due Soon","Overdue","Critical","Resolved","On Hold"];
frappe.query_reports["Project Risks and Issues"]={filters:[
{fieldname:"view",label:__("View"),fieldtype:"Select",options:["Executive Assurance","Donor Assurance","Risk Register","Issue Register","Inherent vs Residual Exposure","Critical and Escalated","Overdue Actions and Reviews","Risk-to-Issue Traceability","Owner and Department Workload","Data Quality and Control Gaps","Full"],default:"Executive Assurance"},
{fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",options:"Project",get_data:txt=>frappe.db.get_link_options("Project",txt)},
{fieldname:"donors",label:__("Donors"),fieldtype:"MultiSelectList",get_data:txt=>ria_values(["donors"],txt)},
{fieldname:"owners",label:__("Owners / Responsible"),fieldtype:"MultiSelectList",get_data:txt=>ria_values(["owner","owners"],txt)},
{fieldname:"departments",label:__("Departments"),fieldtype:"MultiSelectList",get_data:txt=>ria_values(["department","departments"],txt)},
{fieldname:"categories",label:__("Categories"),fieldtype:"MultiSelectList",get_data:txt=>ria_values(["category","categories"],txt)},
{fieldname:"inherent_levels",label:__("Inherent Levels"),fieldtype:"MultiSelectList",get_data:txt=>RIA_LEVELS.filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
{fieldname:"residual_levels",label:__("Residual Levels"),fieldtype:"MultiSelectList",get_data:txt=>RIA_LEVELS.filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
{fieldname:"risk_statuses",label:__("Risk Statuses"),fieldtype:"MultiSelectList",get_data:txt=>ria_values(["status","risk_status_values"],txt)},
{fieldname:"issue_severities",label:__("Issue Severities"),fieldtype:"MultiSelectList",get_data:txt=>RIA_LEVELS.slice(1).filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
{fieldname:"issue_statuses",label:__("Issue Statuses"),fieldtype:"MultiSelectList",get_data:txt=>["Open","Replied","On Hold","Resolved","Closed"].filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
{fieldname:"monitoring_statuses",label:__("Monitoring Statuses"),fieldtype:"MultiSelectList",get_data:txt=>RIA_MON.filter(x=>x.toLowerCase().includes((txt||"").toLowerCase())).map(x=>({value:x,description:x}))},
{fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
{fieldname:"critical_only",label:__("Critical Only"),fieldtype:"Check",default:0},{fieldname:"overdue_only",label:__("Overdue Only"),fieldtype:"Check",default:0},{fieldname:"occurred_only",label:__("Occurred Risks Only"),fieldtype:"Check",default:0},{fieldname:"unmitigated_only",label:__("Unmitigated High/Critical"),fieldtype:"Check",default:0},{fieldname:"quality_only",label:__("Quality Exceptions Only"),fieldtype:"Check",default:0},{fieldname:"include_closed",label:__("Include Closed"),fieldtype:"Check",default:0}],
formatter(value,row,column,data,default_formatter){let v=default_formatter(value,row,column,data);if(!data)return v;const s=String(value||"");if(["inherent_level","residual_level","issue_severity","current_level","monitoring_status","attention","exposure_trend"].includes(column.fieldname)){const c=["Critical","Critical Attention","Worsened"].includes(s)?"red":["High","Overdue","Review Required","Unchanged"].includes(s)?"orange":["Low","Resolved","No Immediate Issue","Improved"].includes(s)?"green":"blue";return `<span class="indicator-pill ${c}">${frappe.utils.escape_html(s)}</span>`;}if(column.fieldname==="quality_flags"&&s)return `<span style="color:#b42318;font-weight:600">${v}</span>`;return v;},
onload(report){report.page.add_inner_button(__("Reset Filters"),()=>{(report.filters||[]).forEach(f=>f.set_value(f.df.fieldname==="view"?"Executive Assurance":(f.df.fieldtype==="Check"?0:null)));report.refresh();});const st=document.createElement("style");st.textContent='.query-report .dt-cell__content{white-space:normal!important;line-height:1.35}.query-report .datatable{border:1px solid var(--border-color);border-radius:10px;overflow:hidden}';document.head.appendChild(st);}}

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
 const config=frappe.query_reports["Project Risks and Issues"];
 if(!config||config.__qfap_link_titles_wrapped) return;
 const original=config.formatter;
 config.formatter=function(value,row,column,data,default_formatter){
  let rendered=original?original.call(this,value,row,column,data,default_formatter):default_formatter(value,row,column,data);
  if(data&&column&&column.fieldtype==="Link"&&column.fieldname){
   const title=data[column.fieldname+"__title"];
   if(title&&String(title)!==String(value||"")){
    rendered+=`<span class="qfap-link-title">${frappe.utils.escape_html(String(title))}</span>`;
   }
  }
  return rendered;
 };
 config.__qfap_link_titles_wrapped=true;
})();

;(function qfap_link_title_style(){
 const id="qfap-link-title-style-v284";if(document.getElementById(id))return;
 const s=document.createElement("style");s.id=id;s.textContent=`.query-report .qfap-link-title{display:block;margin-top:2px;color:var(--text-muted,#6b7280);font-size:11px;line-height:1.25;white-space:normal}`;document.head.appendChild(s);
})();
