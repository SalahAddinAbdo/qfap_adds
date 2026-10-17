function bva_toggle_asset_filter(report){const enabled=Number(report.get_filter_value("include_asset_expenses")||0)===1;const filter=report.get_filter("asset_accounts");if(filter&&filter.$wrapper)filter.$wrapper.toggle(enabled);}
frappe.query_reports["Budget Versus Actual"]={tree:true,name_field:"budget_line",parent_field:"parent",initial_depth:2,filters:[
{fieldname:"company",label:__("Company"),fieldtype:"Link",options:"Company",default:frappe.defaults.get_default("company"),reqd:1},
{fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
{fieldname:"project",label:__("Project"),fieldtype:"Link",options:"Project",get_query(){const c=frappe.query_report.get_filter_value("company");return{filters:c?{company:c}:{}};}},
{fieldname:"accounts",label:__("Accounts"),fieldtype:"MultiSelectList",get_data(txt){const c=frappe.query_report.get_filter_value("company"),f={disabled:0};if(c)f.company=c;return frappe.db.get_link_options("Account",txt,f);}},
{fieldname:"include_asset_expenses",label:__("Include Selected Asset Accounts"),fieldtype:"Check",default:0,on_change(){bva_toggle_asset_filter(frappe.query_report);frappe.query_report.refresh();}},
{fieldname:"asset_accounts",label:__("Asset Account Groups / Accounts"),fieldtype:"MultiSelectList",get_data(txt){const c=frappe.query_report.get_filter_value("company"),f={root_type:"Asset",disabled:0};if(c)f.company=c;return frappe.db.get_link_options("Account",txt,f);}},
{fieldname:"under_utilized_threshold",label:__("Under-Utilized Below %"),fieldtype:"Float",default:70},{fieldname:"over_budget_only",label:__("Over Budget Only"),fieldtype:"Check",default:0},{fieldname:"under_utilized_only",label:__("Under-Utilized Only"),fieldtype:"Check",default:0},{fieldname:"show_account_details",label:__("Show Account Details"),fieldtype:"Check",default:1}],
formatter(value,row,column,data,df){value=df(value,row,column,data);if(!data)return value;if(data.is_account_row&&column.fieldname==="budget_line")return"";if(column.fieldname==="variance"){const n=Number(data.variance||0);return`<span style="color:${n<0?'#c62828':'#2e7d32'};font-weight:600">${value}</span>`;}if(column.fieldname==="performance_status"){const m={"Over Budget":"red","Unbudgeted Expense":"red","Under Utilized":"orange","Fully Utilized":"blue","Within Budget":"green"};return`<span class="indicator-pill ${m[data.performance_status]||'gray'}">${value}</span>`;}return value;},
onload(report){bva_toggle_asset_filter(report);report.page.add_inner_button(__("Reset Filters"),()=>{["project","from_date","to_date"].forEach(x=>report.set_filter_value(x,""));report.set_filter_value("accounts",[]);report.set_filter_value("asset_accounts",[]);report.set_filter_value("include_asset_expenses",0);report.set_filter_value("under_utilized_threshold",70);report.set_filter_value("show_account_details",1);report.refresh();});}}


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
