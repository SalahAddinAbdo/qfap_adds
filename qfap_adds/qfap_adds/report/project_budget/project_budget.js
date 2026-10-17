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
