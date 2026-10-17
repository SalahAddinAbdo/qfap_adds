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
