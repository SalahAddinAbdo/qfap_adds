function ppb_toggle_asset_filter(report){
 const enabled=Number(report.get_filter_value("include_asset_expenses")||0)===1;
 const filter=report.get_filter("asset_accounts");
 if(filter&&filter.$wrapper)filter.$wrapper.toggle(enabled);
}
const PBP_STAGES=["Idea","Concept Development","Internal Review","Proposal Development","Ready for Submission","Submitted to Donor","Under Donor Review","Approved","Pre-Implementation","Under Implementation","Operationally Completed","Under Closure","Closed","Post-Project Monitoring","Deferred","Rejected","Cancelled"];
function pbp_static(values,txt){const q=(txt||"").toLowerCase();return values.filter(v=>v.toLowerCase().includes(q)).map(v=>({value:v,description:""}));}
function pbp_rows(){return(frappe.query_report&&frappe.query_report.data)||[];}
function pbp_split(v){return String(v||"").split("|||").filter(Boolean);}
function pbp_context(field,txt){const q=(txt||"").toLowerCase(),m={};pbp_rows().forEach(r=>pbp_split(r[field]).forEach(v=>{if(!m[v])m[v]=[];const p=r.project_name||r.project||"";if(p&&!m[v].includes(p))m[v].push(p);}));return Object.keys(m).filter(v=>v.toLowerCase().includes(q)).sort().map(v=>({value:v,description:`${m[v].length} project${m[v].length===1?"":"s"} • ${m[v].slice(0,3).join(" • ")}${m[v].length>3?` • +${m[v].length-3} more`:""}`}));}
function pbp_manager(txt){const q=(txt||"").toLowerCase(),m={};pbp_rows().forEach(r=>{const v=r.project_manager||"",n=r.project_manager_name||v;if(v){if(!m[v])m[v]={n,p:[]};const p=r.project_name||r.project||"";if(p&&!m[v].p.includes(p))m[v].p.push(p);}});return Object.keys(m).filter(v=>v.toLowerCase().includes(q)||m[v].n.toLowerCase().includes(q)).map(v=>({value:v,description:`${m[v].n} • ${m[v].p.length} project${m[v].p.length===1?"":"s"}`}));}
frappe.query_reports["Project Budget"]={filters:[
{fieldname:"view_mode",label:__("View"),fieldtype:"Select",options:["Executive Budget","Donor Budget","Budget Tree","Sector Allocation","Partner Allocation","Change Analysis","Full"].join("\n"),default:"Executive Budget"},
{fieldname:"project",label:__("Projects"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Project",txt);}},
{fieldname:"project_manager",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:pbp_manager},
{fieldname:"project_stage",label:__("Stages"),fieldtype:"MultiSelectList",get_data(txt){return pbp_static(PBP_STAGES,txt);}},
{fieldname:"donor",label:__("Donors"),fieldtype:"MultiSelectList",get_data(txt){return pbp_context("all_donors",txt);}},
{fieldname:"sector",label:__("Sectors"),fieldtype:"MultiSelectList",get_data(txt){return pbp_context("all_sectors",txt);}},
{fieldname:"implementing_partner",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data(txt){return pbp_context("all_partners",txt);}},
{fieldname:"company",label:__("Companies"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Company",txt);}},
{fieldname:"currency",label:__("Currencies"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Currency",txt);}},
{fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
{fieldname:"under_utilized_threshold",label:__("Under-Utilized Below %"),fieldtype:"Float",default:70},
{fieldname:"include_asset_expenses",label:__("Include Selected Asset Accounts"),fieldtype:"Check",default:0,on_change(){const report=frappe.query_report;const enabled=Number(report.get_filter_value("include_asset_expenses")||0)===1;ppb_toggle_asset_filter(report);if(!enabled){report.set_filter_value("asset_accounts",[]);report.refresh();}}},
{fieldname:"asset_accounts",label:__("Asset Account Groups / Accounts"),fieldtype:"MultiSelectList",get_data(txt){const companies=frappe.query_report.get_filter_value("company")||[];const f={root_type:"Asset",disabled:0};if(companies.length===1)f.company=companies[0];return frappe.db.get_link_options("Account",txt,f);},on_change(){if(Number(frappe.query_report.get_filter_value("include_asset_expenses")||0)===1)frappe.query_report.refresh();},description:__("Select one or more Asset parent groups or ledger accounts. A parent group includes its enabled non-group Asset descendants.")},
{fieldname:"donor_display_mode",label:__("Donors in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
{fieldname:"sector_display_mode",label:__("Sectors in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
{fieldname:"partner_display_mode",label:__("Partners in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"All",on_change(){frappe.query_report.refresh();}},
{fieldname:"chart_by",label:__("Chart By"),fieldtype:"Select",options:["Allocation Status","Funding Coverage","Project","Donor","Sector"].join("\n"),default:"Allocation Status"},
{fieldname:"attention_only",label:__("Need Attention Only"),fieldtype:"Check",default:0},
{fieldname:"over_budget_only",label:__("Over Budget Only"),fieldtype:"Check",default:0}
],formatter(value,row,column,data,df){value=df(value,row,column,data);if(!data)return value;if(column.fieldname==="financial_status"){const m={"Over Budget":"red","Unbudgeted Expense":"red","Under Utilized":"orange","Fully Utilized":"blue","Within Budget":"green"};return `<span class="indicator-pill ${m[data.financial_status]||"gray"}">${value}</span>`;}if(["utilization_percentage","line_utilization"].includes(column.fieldname)){const n=parseFloat(data[column.fieldname]||0),t=parseFloat(frappe.query_report.get_filter_value("under_utilized_threshold")||70),c=n>100?"#c62828":n<t?"#f9a825":"#2e7d32";return `<span style="color:${c};font-weight:600">${value}</span>`;}if(["available_balance","line_balance"].includes(column.fieldname)&&parseFloat(data[column.fieldname]||0)<0)return `<span style="color:#c62828;font-weight:600">${value}</span>`;if(column.fieldname==="budget_attention"&&data.budget_attention)return `<span style="color:#b42318;font-weight:600">${value}</span>`;if(["sector_allocation_status","partner_allocation_status"].includes(column.fieldname)){const c=String(data[column.fieldname]||"").includes("Over")?"red":String(data[column.fieldname]||"").includes("Fully")?"green":"orange";return `<span class="indicator-pill ${c}">${value}</span>`;}if(["funding_coverage","sector_allocation_percentage","partner_allocation_percentage"].includes(column.fieldname)){const n=parseFloat(data[column.fieldname]||0),c=n>100?"#c62828":n>=90?"#2e7d32":n>=70?"#f9a825":"#c62828";return `<span style="color:${c};font-weight:600">${value}</span>`;}return value;},onload(report){ppb_toggle_asset_filter(report);["Executive Budget","Donor Budget","Budget Tree","Sector Allocation","Partner Allocation","Change Analysis","Full"].forEach(v=>report.page.add_inner_button(__(v),()=>{report.set_filter_value("view_mode",v);report.refresh();},__("Views")));report.page.add_inner_button(__("Reset Filters"),()=>{["project","project_manager","project_stage","donor","sector","implementing_partner","company","currency"].forEach(f=>report.set_filter_value(f,[]));report.set_filter_value("view_mode","Executive Budget");report.set_filter_value("donor_display_mode","Primary");report.set_filter_value("sector_display_mode","Primary");report.set_filter_value("partner_display_mode","All");report.set_filter_value("chart_by","Allocation Status");report.set_filter_value("attention_only",0);report.set_filter_value("over_budget_only",0);report.set_filter_value("under_utilized_threshold",70);report.set_filter_value("include_asset_expenses",0);report.set_filter_value("asset_accounts",[]);report.set_filter_value("from_date","");report.set_filter_value("to_date","");ppb_toggle_asset_filter(report);report.refresh();});const st=document.createElement("style");st.textContent=`.query-report .report-summary{gap:12px}.query-report .report-summary .summary-item{min-width:145px;padding:12px 16px;border:1px solid var(--border-color);border-radius:10px;background:var(--card-bg)}.query-report .chart-container{border:1px solid var(--border-color);border-radius:12px;padding:12px;margin-top:8px;background:var(--card-bg)}.query-report .datatable{border-radius:10px;overflow:hidden;border:1px solid var(--border-color)}.dt-cell__content{white-space:normal!important;line-height:1.35}`;document.head.appendChild(st);}};


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
