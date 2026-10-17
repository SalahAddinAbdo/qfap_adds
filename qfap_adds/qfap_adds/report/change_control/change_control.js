// v1.1 VERIFIED SCHEMA - Frappe 16
frappe.query_reports["Change Control"]={filters:[
{fieldname:"view",label:__("View"),fieldtype:"Select",options:["Executive Change Assurance","Donor Amendment Control","Change Request Register","Impact Analysis","Budget Change Analysis","Schedule and Scope Changes","Donor Approval Tracking","Implementation Follow-up","Affected Items Traceability","Project Comparison","Decision and Processing Performance","Data Quality and Control Gaps","Full"].join("\n"),default:"Executive Change Assurance",on_change:()=>frappe.query_report.refresh()},
{fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Project",txt)},
{fieldname:"project_managers",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_project_managers",txt)},{fieldname:"stages",label:__("Stages"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_stages",txt)},{fieldname:"donors",label:__("Donors"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_donors",txt)},
{fieldname:"change_categories",label:__("Change Categories"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_change_categories",txt)},{fieldname:"change_priorities",label:__("Priorities"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_change_priorities",txt)},{fieldname:"change_scopes",label:__("Scopes"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_change_scopes",txt)},{fieldname:"impact_levels",label:__("Impact Levels"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_impact_levels",txt)},
{fieldname:"statuses",label:__("Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_statuses",txt)},{fieldname:"donor_approval_statuses",label:__("Donor Approval Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_donor_approval_statuses",txt)},{fieldname:"implementation_statuses",label:__("Implementation Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_implementation_statuses",txt)},
{fieldname:"requested_by",label:__("Requested By"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_requested_by",txt)},{fieldname:"implementation_responsibles",label:__("Implementation Responsible"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_implementation_responsibles",txt)},{fieldname:"affected_item_types",label:__("Affected Item Types"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_affected_item_types",txt)},
{fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
{fieldname:"pending_approval_only",label:__("Pending Approval Only"),fieldtype:"Check",default:0},{fieldname:"pending_donor_approval_only",label:__("Pending Donor Approval Only"),fieldtype:"Check",default:0},{fieldname:"approved_not_implemented_only",label:__("Approved Not Implemented Only"),fieldtype:"Check",default:0},{fieldname:"overdue_implementation_only",label:__("Overdue Implementation Only"),fieldtype:"Check",default:0},{fieldname:"high_critical_impact_only",label:__("High / Critical Impact Only"),fieldtype:"Check",default:0},{fieldname:"budget_changes_only",label:__("Budget Changes Only"),fieldtype:"Check",default:0},{fieldname:"quality_exceptions_only",label:__("Quality Exceptions Only"),fieldtype:"Check",default:0},{fieldname:"include_completed",label:__("Include Completed"),fieldtype:"Check",default:1},{fieldname:"include_closed_projects",label:__("Include Closed Projects"),fieldtype:"Check",default:0}],
onload(r){r.page.add_inner_button(__("Reset Filters"),()=>{const d={view:"Executive Change Assurance",include_completed:1};Object.keys(r.get_values()).forEach(k=>r.set_filter_value(k,d[k]!==undefined?d[k]:[]));r.refresh();});},
formatter(v,row,col,d,fmt){let x=fmt(v,row,col,d);if(!d)return x;const colors={Approved:"green",Authorized:"green",Rejected:"red",Cancelled:"gray","Pending Approval":"orange","Under Review":"orange",Draft:"gray",Implemented:"green",Verified:"green","Not Started":"gray","In Progress":"blue","Not Submitted":"gray",Submitted:"blue"};if(["status","donor_approval_status","implementation_status"].includes(col.fieldname))x=pill(v,colors[v]||"gray");if(col.fieldname==="management_attention")x=pill(v,v==="Critical Attention"?"red":v==="Review Required"?"orange":v==="Monitor"?"blue":"green");if(col.fieldname==="quality_flags"&&v)x=`<span style="color:#c0392b;white-space:normal">${frappe.utils.escape_html(v)}</span>`;return x;}}
function pill(v,c){return `<span class="indicator-pill ${c}">${frappe.utils.escape_html(String(v||""))}</span>`;}
function ctx(f,t){const q=(t||"").toLowerCase(),vals=[];(frappe.query_report.data||[]).forEach(r=>String(r[f]||"").split(",").forEach(i=>{const v=i.trim();if(v&&!vals.includes(v)&&(!q||v.toLowerCase().includes(q)))vals.push(v);}));vals.sort((a,b)=>a.localeCompare(b));return vals.map(v=>({value:v,description:desc(f,v)}));}
function desc(f,v){let c=0,ps=[];(frappe.query_report.data||[]).forEach(r=>{if(String(r[f]||"").split(",").map(i=>i.trim()).includes(v)){c++;if(r.project&&!ps.includes(r.project))ps.push(r.project);}});return `${c} record${c===1?"":"s"}${ps.length?" • "+ps.slice(0,3).join(" • "):""}${ps.length>3?" • +"+(ps.length-3)+" more":""}`;}


// QFAP report usability layer: readable KPI cards and sticky first two data columns.
(function qfap_report_usability(){
 const STYLE_ID="qfap-report-usability-v28";
 function ensure_style(){
  if(document.getElementById(STYLE_ID))return;
  const style=document.createElement("style");style.id=STYLE_ID;
  style.textContent=`
   .query-report .report-summary{display:flex!important;gap:10px!important;align-items:stretch!important;flex-wrap:wrap!important;overflow:visible!important;padding-block:6px 10px!important}
   .query-report .report-summary .summary-item,.query-report [class*="kpi-card"],.query-report .qfap-kpi-card{height:auto!important;min-height:72px!important;overflow:visible!important;padding:11px 14px!important;display:flex!important;flex-direction:column!important;justify-content:center!important}
   .query-report .report-summary .summary-item .summary-label,.query-report .report-summary .summary-item .text-muted,.query-report [class*="kpi-card"] .label{height:auto!important;max-height:none!important;overflow:visible!important;white-space:normal!important;line-height:1.35!important;padding-bottom:3px!important}
   .query-report .report-summary .summary-item .summary-value,.query-report [class*="kpi-card"] .value{line-height:1.25!important;overflow:visible!important}
   .query-report .datatable{isolation:isolate;border-radius:10px;overflow:auto}
   .query-report .dt-cell.qfap-sticky-col{position:sticky!important;background:var(--card-bg,#fff)!important;box-shadow:1px 0 0 var(--border-color,#d1d8dd);}
   .query-report .dt-header .dt-cell.qfap-sticky-col{z-index:8!important;background:var(--subtle-fg,#f5f7fa)!important}
   .query-report .dt-row:not(.dt-row-filter) .dt-cell.qfap-sticky-col{z-index:5!important}
   .query-report .dt-row-filter .dt-cell.qfap-sticky-col{z-index:7!important;background:var(--control-bg,#f4f5f6)!important}
   .query-report .dt-cell__content{line-height:1.35!important}
  `;document.head.appendChild(style);
 }
 function freeze_two(){
  ensure_style();
  const root=document.querySelector('.query-report .datatable');if(!root)return;
  const header=[...root.querySelectorAll('.dt-header .dt-cell')].filter(x=>x.offsetWidth>0);
  if(header.length<2)return;
  // If a narrow serial/checkbox column exists, freeze it plus the next two business columns.
  const start=header[0].offsetWidth<70?1:0;
  const indices=[start,start+1];let left=0;
  if(start===1){
   const serial=header[0];serial.classList.add('qfap-sticky-col');serial.style.left='0px';left=serial.getBoundingClientRect().width;
   root.querySelectorAll('.dt-cell--col-0').forEach(c=>{c.classList.add('qfap-sticky-col');c.style.left='0px';});
  }
  indices.forEach(idx=>{
   const cell=header[idx];if(!cell)return;
   const cls=[...cell.classList].find(c=>c.startsWith('dt-cell--col-'));
   if(!cls)return;
   root.querySelectorAll('.'+cls).forEach(c=>{c.classList.add('qfap-sticky-col');c.style.left=left+'px';});
   left+=cell.getBoundingClientRect().width;
  });
 }
 ensure_style();
 let tries=0;const timer=setInterval(()=>{freeze_two();if(++tries>20)clearInterval(timer);},250);
 const observer=new MutationObserver(()=>freeze_two());
 const page=document.querySelector('.query-report');if(page)observer.observe(page,{childList:true,subtree:true});
 window.addEventListener('resize',()=>setTimeout(freeze_two,100),{passive:true});
})();
