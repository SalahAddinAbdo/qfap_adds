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
