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
