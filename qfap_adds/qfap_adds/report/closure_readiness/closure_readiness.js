// v1.1 VERIFIED PROJECT INTEGRATION - Frappe 16
frappe.query_reports["Closure Readiness"]={filters:[
{fieldname:"view",label:__("View"),fieldtype:"Select",options:["Executive Closure Readiness","Donor Closeout Assurance","Closure Register","Domain Readiness","Outstanding Actions","Critical Closure Blockers","Programme Completion","Financial Closeout","Compliance and Records","Partner Closeout","Assets and Handover","Sustainability and Transition","Lessons Learned and Evaluation","Closure Approval Workflow","Data Quality and Control Gaps","Full"].join("\n"),default:"Executive Closure Readiness",on_change:()=>frappe.query_report.refresh()},
{fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Project",txt)},{fieldname:"project_managers",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_project_managers",txt)},{fieldname:"stages",label:__("Stages"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_stages",txt)},{fieldname:"donors",label:__("Donors"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_donors",txt)},{fieldname:"partners",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_partners",txt)},
{fieldname:"closure_statuses",label:__("Closure Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_closure_statuses",txt)},{fieldname:"overall_readiness",label:__("Overall Readiness"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_overall_readiness",txt)},{fieldname:"closure_domains",label:__("Closure Domains"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_closure_domains",txt)},{fieldname:"checklist_statuses",label:__("Checklist Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_checklist_statuses",txt)},{fieldname:"action_statuses",label:__("Action Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_action_statuses",txt)},{fieldname:"action_owners",label:__("Action Owners"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_action_owners",txt)},{fieldname:"departments",label:__("Departments"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_departments",txt)},{fieldname:"priorities",label:__("Priorities"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_priorities",txt)},
{fieldname:"from_date",label:__("Planned End From"),fieldtype:"Date"},{fieldname:"to_date",label:__("Planned End To"),fieldtype:"Date"},{fieldname:"ready_only",label:__("Ready for Closure Only"),fieldtype:"Check",default:0},{fieldname:"not_ready_only",label:__("Not Ready Only"),fieldtype:"Check",default:0},{fieldname:"outstanding_actions_only",label:__("Outstanding Actions Only"),fieldtype:"Check",default:0},{fieldname:"overdue_actions_only",label:__("Overdue Actions Only"),fieldtype:"Check",default:0},{fieldname:"critical_blockers_only",label:__("Critical Blockers Only"),fieldtype:"Check",default:0},{fieldname:"pending_deliverables_only",label:__("Pending Deliverables Only"),fieldtype:"Check",default:0},{fieldname:"financial_attention_only",label:__("Financial Attention Only"),fieldtype:"Check",default:0},{fieldname:"quality_exceptions_only",label:__("Quality Exceptions Only"),fieldtype:"Check",default:0},{fieldname:"include_closed_projects",label:__("Include Closed Projects"),fieldtype:"Check",default:0}],
onload(r){r.page.add_inner_button(__("Reset Filters"),()=>{const d={view:"Executive Closure Readiness"};Object.keys(r.get_values()).forEach(k=>r.set_filter_value(k,d[k]!==undefined?d[k]:[]));r.refresh();});},
formatter(v,row,col,d,fmt){let x=fmt(v,row,col,d);if(!d)return x;const colors={"Ready for Closure":"green","Ready with Outstanding Actions":"orange","Not Ready":"red","Not Assessed":"gray",Approved:"green",Closed:"green",Draft:"gray",Complete:"green",Completed:"green",Pending:"orange",Open:"orange",Overdue:"red",Critical:"red"};if(["closure_status","overall_closure_status","item_status","action_status","monitoring_status","implementation_status","project_health"].includes(col.fieldname))x=pill(v,colors[v]||"gray");if(col.fieldname==="management_attention")x=pill(v,v==="Critical Attention"?"red":v==="Review Required"?"orange":v==="Monitor"?"blue":"green");if(["checklist_completion","activities_progress","indicators_achievement","overall_progress","individual_achievement","household_achievement"].includes(col.fieldname)){const n=Number(v||0);x=pill(`${n.toFixed(2)}%`,n>=100?"green":n>=80?"orange":"red");}if(col.fieldname==="quality_flags"&&v)x=`<span style="color:#c0392b;white-space:normal">${frappe.utils.escape_html(v)}</span>`;return x;}}
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
 const config=frappe.query_reports["Closure Readiness"];
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
