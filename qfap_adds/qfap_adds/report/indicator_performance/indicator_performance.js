const IPTT_STATUS_OPTIONS=["Not Assessed","Target Achieved","Exceeded Target","On Track","At Risk","Critical"];
const IPTT_QUALITY_OPTIONS=["Pending Verification","Verified","Verified with Limitations","Rejected","Not Assessed"];
function iptt_static(values,txt){const q=(txt||"").toLowerCase();return values.filter(v=>v.toLowerCase().includes(q)).map(v=>({value:v,description:""}));}
function iptt_rows(){return (frappe.query_report&&frappe.query_report.data)||[];}
function iptt_options(field,txt,label_field){const q=(txt||"").toLowerCase(),map={};iptt_rows().forEach(row=>{const value=row[field]||"",label=label_field?(row[label_field]||value):value;if(value&&!map[value])map[value]={label,count:0,projects:[]};if(value){map[value].count+=1;const project=row.project_name||row.project||"";if(project&&!map[value].projects.includes(project))map[value].projects.push(project);}});return Object.keys(map).filter(v=>v.toLowerCase().includes(q)||map[v].label.toLowerCase().includes(q)).sort((a,b)=>map[a].label.localeCompare(map[b].label)).map(value=>{const x=map[value],projects=x.projects.slice(0,3).join(" • "),more=x.projects.length>3?` • +${x.projects.length-3} more`:"";return{value,description:`${x.label} • ${x.count} record${x.count===1?"":"s"}${projects?` • ${projects}${more}`:""}`};});}
frappe.query_reports["Indicator Performance"]={
 filters:[
  {fieldname:"view_mode",label:__("View"),fieldtype:"Select",options:["Standard IPTT","Donor IPTT","M&E","Period Performance","Cumulative Performance","Full"].join("\n"),default:"Standard IPTT"},
  {fieldname:"layout_mode",label:__("Layout"),fieldtype:"Select",options:["Period Rows","Period Matrix","Cumulative Matrix"].join("\n"),default:"Period Rows"},
  {fieldname:"period_grouping",label:__("Time Grouping"),fieldtype:"Select",options:["Plan Period","Month","Quarter","Calendar Year","Project Year"].join("\n"),default:"Plan Period"},
  {fieldname:"matrix_measure",label:__("Matrix Measure"),fieldtype:"Select",options:["Target and Actual","Target Only","Actual Only","Achievement %"].join("\n"),default:"Target and Actual"},
  {fieldname:"project",label:__("Projects"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Project",txt);}},
  {fieldname:"indicator",label:__("Indicators"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Project Indicator",txt);}},
  {fieldname:"indicator_type",label:__("Indicator Levels"),fieldtype:"MultiSelectList",get_data(txt){return iptt_static(["Impact","Outcome","Output","Process"],txt);}},
  {fieldname:"project_manager",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data(txt){return iptt_options("project_manager",txt,"project_manager_name");}},
  {fieldname:"performance_status",label:__("Performance Statuses"),fieldtype:"MultiSelectList",get_data(txt){return iptt_static(IPTT_STATUS_OPTIONS,txt);}},
  {fieldname:"data_quality",label:__("Data Quality"),fieldtype:"MultiSelectList",get_data(txt){return iptt_static(IPTT_QUALITY_OPTIONS,txt);}},
  {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
  {fieldname:"chart_by",label:__("Chart By"),fieldtype:"Select",options:["Performance Status","Project","Result","Indicator Level","Data Quality","Aggregation Method"].join("\n"),default:"Performance Status"},
  {fieldname:"below_target_only",label:__("Below Target Only"),fieldtype:"Check",default:0},{fieldname:"not_updated_only",label:__("Not Updated Only"),fieldtype:"Check",default:0}
 ],
 formatter(value,row,column,data,default_formatter){value=default_formatter(value,row,column,data);if(!data)return value;if(column.fieldname==="performance_status"){const c={"Target Achieved":"blue","Exceeded Target":"blue","On Track":"green","At Risk":"orange","Critical":"red"}[data.performance_status]||"gray";return `<span class="indicator-pill ${c}">${value}</span>`;}if(column.fieldname==="achievement_percentage"||column.fieldname.endsWith("_achievement")){const n=parseFloat(data[column.fieldname]||0),c=n>=100?"#1565c0":n>=90?"#2e7d32":n>=70?"#f9a825":"#c62828";return `<span style="color:${c};font-weight:600">${value}</span>`;}if(column.fieldname==="variance"&&parseFloat(data.variance||0)<0)return `<span style="color:#c62828;font-weight:600">${value}</span>`;if(column.fieldname==="data_quality"&&["Verified with Limitations","Rejected"].includes(data.data_quality))return `<span class="indicator-pill red">${value}</span>`;return value;},
 onload(report){["Standard IPTT","Donor IPTT","M&E","Period Performance","Cumulative Performance","Full"].forEach(view=>report.page.add_inner_button(__(view),()=>{report.set_filter_value("view_mode",view);report.refresh();},__("Views")));report.page.add_inner_button(__("Reset Filters"),()=>{["project","indicator","indicator_type","project_manager","performance_status","data_quality"].forEach(f=>report.set_filter_value(f,[]));["from_date","to_date"].forEach(f=>report.set_filter_value(f,""));report.set_filter_value("view_mode","Standard IPTT");report.set_filter_value("layout_mode","Period Rows");report.set_filter_value("period_grouping","Plan Period");report.set_filter_value("matrix_measure","Target and Actual");report.set_filter_value("chart_by","Performance Status");report.set_filter_value("below_target_only",0);report.set_filter_value("not_updated_only",0);report.refresh();});const style=document.createElement("style");style.textContent=`.query-report .report-summary{gap:12px}.query-report .report-summary .summary-item{min-width:145px;padding:12px 16px;border:1px solid var(--border-color);border-radius:10px;background:var(--card-bg)}.query-report .chart-container{border:1px solid var(--border-color);border-radius:12px;padding:12px;margin-top:8px;background:var(--card-bg)}.query-report .datatable{border-radius:10px;overflow:hidden;border:1px solid var(--border-color)}.dt-cell__content{white-space:normal!important;line-height:1.35}.awesomplete>ul>li small,.multiselect-list .dropdown-menu small{display:block;white-space:normal;color:var(--text-muted);line-height:1.35;margin-top:2px}`;document.head.appendChild(style);}
};



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
