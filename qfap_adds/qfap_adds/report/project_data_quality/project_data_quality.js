// v2.1 SAFE METADATA DISCOVERY - Frappe 16
// v2.0 SYSTEM 360
frappe.query_reports["Project Data Quality"]={filters:[
{fieldname:"view",label:__("View"),fieldtype:"Select",options:["Executive Data Quality","Stage Readiness","Project Setup Completeness","Results Framework Quality","Monitoring Data Quality","Financial Data Quality","Beneficiary Data Quality","Risk and Issue Quality","Compliance Quality","Change Control Quality","Closure Quality","System Linkage Inventory","Procurement and Stock","Financial and Assets","All Linked Documents","Cross-Module Exceptions","Full Audit Export"].join("\n"),default:"Executive Data Quality",on_change:()=>frappe.query_report.refresh()},
{fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Project",txt)},{fieldname:"project_managers",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_project_managers",txt)},{fieldname:"stages",label:__("Stages"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_stages",txt)},{fieldname:"health_statuses",label:__("Health Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_health_statuses",txt)},{fieldname:"donors",label:__("Donors"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_donors",txt)},{fieldname:"sectors",label:__("Sectors"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_sectors",txt)},{fieldname:"partners",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_partners",txt)},{fieldname:"governorates",label:__("Governorates"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_governorates",txt),on_change:()=>{frappe.query_report.set_filter_value("districts",[]);frappe.query_report.refresh();}},{fieldname:"districts",label:__("Districts"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_districts",txt)},{fieldname:"readiness_statuses",label:__("Readiness Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_readiness_statuses",txt)},{fieldname:"quality_ratings",label:__("Quality Ratings"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_quality_ratings",txt)},{fieldname:"domains",label:__("Exception Domains"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_domains",txt)},
{fieldname:"linked_doctypes",label:__("Linked Document Types"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_linked_doctypes",txt)},{fieldname:"linked_statuses",label:__("Linked Document Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_linked_statuses",txt)},{fieldname:"linked_modules",label:__("Linked Modules"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_linked_modules",txt)},
{fieldname:"minimum_score",label:__("Minimum Quality Score"),fieldtype:"Percent"},{fieldname:"critical_only",label:__("Critical Quality Only"),fieldtype:"Check",default:0},{fieldname:"exceptions_only",label:__("Exceptions Only"),fieldtype:"Check",default:0},{fieldname:"stage_not_ready_only",label:__("Stage Not Ready Only"),fieldtype:"Check",default:0},{fieldname:"include_closed_projects",label:__("Include Closed Projects"),fieldtype:"Check",default:0}],
onload(r){r.page.add_inner_button(__("Reset Filters"),()=>{const d={view:"Executive Data Quality"};Object.keys(r.get_values()).forEach(k=>r.set_filter_value(k,d[k]!==undefined?d[k]:[]));r.refresh();});},
formatter(v,row,col,d,fmt){let x=fmt(v,row,col,d);if(!d)return x;const c={Good:"green","Needs Improvement":"orange",Critical:"red",Ready:"green","Ready with Exceptions":"orange","Not Ready":"red","On Track":"green","At Risk":"orange","Not Assessed":"gray","On Hold":"orange"};if(["quality_rating","cycle_readiness","project_health","severity","document_status"].includes(col.fieldname))x=pill(v,c[v]||"gray");if(["data_quality_score","setup_score","results_score","monitoring_score","financial_score","beneficiary_score","risk_issue_score","compliance_score","change_score","closure_score"].includes(col.fieldname)){const n=Number(v||0);x=pill(`${n.toFixed(2)}%`,n>=80?"green":n>=50?"orange":"red");}if(col.fieldname==="quality_flags"&&v)x=`<span style="color:#c0392b;white-space:normal">${frappe.utils.escape_html(v)}</span>`;return x;}}
function pill(v,c){return `<span class="indicator-pill ${c}">${frappe.utils.escape_html(String(v||""))}</span>`;}
function ctx(f,t){const q=(t||"").toLowerCase(),vals=[];(frappe.query_report.data||[]).forEach(r=>String(r[f]||"").split(",").forEach(i=>{const v=i.trim();if(v&&!vals.includes(v)&&(!q||v.toLowerCase().includes(q)))vals.push(v);}));vals.sort((a,b)=>a.localeCompare(b));return vals.map(v=>({value:v,description:desc(f,v)}));}
function desc(f,v){let c=0,ps=[];(frappe.query_report.data||[]).forEach(r=>{if(String(r[f]||"").split(",").map(i=>i.trim()).includes(v)){c++;if(r.project&&!ps.includes(r.project))ps.push(r.project);}});return `${c} record${c===1?"":"s"}${ps.length?" • "+ps.slice(0,3).join(" • "):""}${ps.length>3?" • +"+(ps.length-3)+" more":""}`;}

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
 const config=frappe.query_reports["Project Data Quality"];
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
