frappe.query_reports["Compliance Assurance"]={filters:[
{fieldname:"view",label:__("View"),fieldtype:"Select",options:["Executive Assurance","Donor Compliance","Deliverables Register","Upcoming and Due Soon","Overdue and Escalated","Evidence Completeness","Review and Approval Workflow","Responsible Workload","Period Performance","Data Quality and Control Gaps","Full"].join("\n"),default:"Executive Assurance",on_change:()=>frappe.query_report.refresh()},
{fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Project",txt)},
{fieldname:"project_managers",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_project_managers",txt)},
{fieldname:"stages",label:__("Stages"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_stages",txt)},
{fieldname:"donors",label:__("Donors"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_donors",txt)},
{fieldname:"partners",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_partners",txt)},
{fieldname:"deliverable_types",label:__("Deliverable Types"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_deliverable_types",txt)},
{fieldname:"responsible_employees",label:__("Responsible Employees"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_responsible_employees",txt)},
{fieldname:"review_responsibles",label:__("Review Responsibles"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_review_responsibles",txt)},
{fieldname:"statuses",label:__("Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_statuses",txt)},
{fieldname:"monitoring_statuses",label:__("Monitoring Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_monitoring_statuses",txt)},
{fieldname:"attachment_statuses",label:__("Attachment Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_attachment_statuses",txt)},
{fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
{fieldname:"due_soon_only",label:__("Due Soon Only"),fieldtype:"Check",default:0},{fieldname:"overdue_only",label:__("Overdue Only"),fieldtype:"Check",default:0},{fieldname:"missing_evidence_only",label:__("Missing Evidence Only"),fieldtype:"Check",default:0},{fieldname:"rejected_revision_only",label:__("Rejected / Revision Only"),fieldtype:"Check",default:0},{fieldname:"quality_exceptions_only",label:__("Quality Exceptions Only"),fieldtype:"Check",default:0},{fieldname:"include_completed",label:__("Include Completed"),fieldtype:"Check",default:1},{fieldname:"include_closed_projects",label:__("Include Closed Projects"),fieldtype:"Check",default:0}],
onload(r){r.page.add_inner_button(__("Reset Filters"),()=>{const d={view:"Executive Assurance",include_completed:1};Object.keys(r.get_values()).forEach(k=>r.set_filter_value(k,d[k]!==undefined?d[k]:[]));r.refresh();});},
formatter(v,row,col,d,fmt){let x=fmt(v,row,col,d);if(!d)return x;const sc={Approved:"green",Waived:"blue",Rejected:"red",Cancelled:"gray","Revision Required":"orange","Awaiting Response":"blue","Ready for Submission":"purple","Under Internal Review":"orange","In Preparation":"gray",Draft:"gray"};const mc={Critical:"red",Overdue:"red","Due Soon":"orange","Internal Review Due":"orange","Awaiting Response":"blue","Revision Required":"orange",Approved:"green",Waived:"blue",Rejected:"red","Not Due":"green","Not Assessed":"gray"};if(col.fieldname==="status")x=pill(v,sc[v]||"gray");if(col.fieldname==="monitoring_status")x=pill(v,mc[v]||"gray");if(col.fieldname==="management_attention")x=pill(v,v==="Critical Attention"?"red":v==="Review Required"?"orange":v==="Monitor"?"blue":"green");if(["compliance_rate","on_time_rate","evidence_completeness"].includes(col.fieldname)){const n=Number(v||0);x=pill(format_percent_value(n),n>=90?"green":n>=70?"orange":"red");}if(col.fieldname==="quality_flags"&&v)x=`<span style="color:#c0392b;white-space:normal">${frappe.utils.escape_html(v)}</span>`;return x;}}
function format_percent_value(value){const n=Number(value||0);return `${n.toFixed(2)}%`;}
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
