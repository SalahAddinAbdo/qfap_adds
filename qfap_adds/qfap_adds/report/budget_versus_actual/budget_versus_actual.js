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
 const config=frappe.query_reports["Budget Versus Actual"];
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
