const PPP_STAGE_OPTIONS=["Idea","Concept Development","Internal Review","Proposal Development","Ready for Submission","Submitted to Donor","Under Donor Review","Approved","Pre-Implementation","Under Implementation","Operationally Completed","Under Closure","Closed","Post-Project Monitoring","Deferred","Rejected","Cancelled"];
const PPP_HEALTH_OPTIONS=["Not Assessed","On Track","At Risk","Critical","Completed","On Hold"];
const PPP_PERFORMANCE_OPTIONS=["Not Assessed","Ahead","On Track","Behind","Critical"];
function ppp_static(values,txt){const q=(txt||"").toLowerCase();return values.filter(v=>v.toLowerCase().includes(q)).map(v=>({value:v,description:""}));}
function ppp_rows(){return (frappe.query_report&&frappe.query_report.data)||[];}
function ppp_split(value,sep="|||"){return String(value||"").split(sep).map(v=>v.trim()).filter(Boolean);}
function ppp_project_label(row){return row.project_name||row.project||"";}
function ppp_short(values){const unique=[];values.forEach(v=>{if(v&&!unique.includes(v))unique.push(v);});const shown=unique.slice(0,3).join(" • ");return unique.length>3?`${shown} • +${unique.length-3} more`:shown;}
function ppp_context(field,txt,kind){const q=(txt||"").toLowerCase(),map={};ppp_rows().forEach(row=>ppp_split(row[field]).forEach(value=>{if(!map[value])map[value]={projects:[],primary:0};const project=ppp_project_label(row);if(project&&!map[value].projects.includes(project))map[value].projects.push(project);if((kind==="donor"&&row.primary_donor===value)||(kind==="sector"&&row.primary_sector===value)||(kind==="governorate"&&row.governorate===value))map[value].primary+=1;}));return Object.keys(map).filter(v=>v.toLowerCase().includes(q)).sort((a,b)=>a.localeCompare(b)).map(value=>{const item=map[value],count=item.projects.length;let description=`${count} project${count===1?"":"s"}`;if(item.primary)description+=` • Primary in ${item.primary}`;const projects=ppp_short(item.projects);if(projects)description+=` • ${projects}`;return{value,description};});}
function ppp_managers(txt){const q=(txt||"").toLowerCase(),map={};ppp_rows().forEach(row=>{const value=row.project_manager||"",name=row.project_manager_name||value;if(value){if(!map[value])map[value]={name,projects:[]};const project=ppp_project_label(row);if(project&&!map[value].projects.includes(project))map[value].projects.push(project);}});return Object.keys(map).filter(v=>v.toLowerCase().includes(q)||map[v].name.toLowerCase().includes(q)).sort((a,b)=>map[a].name.localeCompare(map[b].name)).map(value=>{const x=map[value],count=x.projects.length;return{value,description:`${x.name} • ${count} project${count===1?"":"s"} • ${ppp_short(x.projects)}`};});}
function ppp_districts(txt){const q=(txt||"").toLowerCase(),govs=frappe.query_report.get_filter_value("governorate")||[],map={};ppp_rows().forEach(row=>ppp_split(row.location_pairs,";;;").forEach(pair=>{const parts=pair.split("|||"),gov=parts[0]||"",district=parts[1]||"";if(!district||govs.length&&!govs.includes(gov))return;if(!map[district])map[district]={governorates:[],projects:[]};if(gov&&!map[district].governorates.includes(gov))map[district].governorates.push(gov);const project=ppp_project_label(row);if(project&&!map[district].projects.includes(project))map[district].projects.push(project);}));return Object.keys(map).filter(v=>v.toLowerCase().includes(q)).sort((a,b)=>a.localeCompare(b)).map(value=>{const x=map[value],count=x.projects.length;return{value,description:`${x.governorates.join(", ")} • ${count} project${count===1?"":"s"} • ${ppp_short(x.projects)}`};});}
frappe.query_reports["Project Progress"]={
 filters:[
  {fieldname:"view_mode",label:__("View"),fieldtype:"Select",options:["Executive","Headquarters","Project Management","Activities","Indicators","Timeline","Full"].join("\n"),default:"Executive"},
  {fieldname:"project",label:__("Projects"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Project",txt);}},
  {fieldname:"project_manager",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:ppp_managers},
  {fieldname:"project_stage",label:__("Stages"),fieldtype:"MultiSelectList",get_data(txt){return ppp_static(PPP_STAGE_OPTIONS,txt);}},
  {fieldname:"project_health",label:__("Health Statuses"),fieldtype:"MultiSelectList",get_data(txt){return ppp_static(PPP_HEALTH_OPTIONS,txt);}},
  {fieldname:"performance_level",label:__("Performance Levels"),fieldtype:"MultiSelectList",get_data(txt){return ppp_static(PPP_PERFORMANCE_OPTIONS,txt);}},
  {fieldname:"donor",label:__("Donors"),fieldtype:"MultiSelectList",get_data(txt){return ppp_context("all_donors",txt,"donor");}},
  {fieldname:"sector",label:__("Sectors"),fieldtype:"MultiSelectList",get_data(txt){return ppp_context("all_sectors",txt,"sector");}},
  {fieldname:"implementing_partner",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data(txt){return ppp_context("all_partners",txt,"partner");}},
  {fieldname:"governorate",label:__("Governorates"),fieldtype:"MultiSelectList",get_data(txt){return ppp_context("all_governorates",txt,"governorate");},on_change(){frappe.query_report.set_filter_value("district",[]);frappe.query_report.refresh();}},
  {fieldname:"district",label:__("Districts"),fieldtype:"MultiSelectList",get_data:ppp_districts},
  {fieldname:"company",label:__("Companies"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Company",txt);}},
  {fieldname:"donor_display_mode",label:__("Donors in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
  {fieldname:"sector_display_mode",label:__("Sectors in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
  {fieldname:"partner_display_mode",label:__("Partners in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"All",on_change(){frappe.query_report.refresh();}},
  {fieldname:"location_display_mode",label:__("Locations in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"All",on_change(){frappe.query_report.refresh();}},
  {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
  {fieldname:"chart_by",label:__("Chart By"),fieldtype:"Select",options:["Performance Level","Health","Stage","Manager","Sector","Governorate"].join("\n"),default:"Performance Level"},
  {fieldname:"active_only",label:__("Active Only"),fieldtype:"Check",default:1},{fieldname:"attention_only",label:__("Need Attention Only"),fieldtype:"Check",default:0},{fieldname:"delayed_only",label:__("Delayed Activities Only"),fieldtype:"Check",default:0},{fieldname:"update_required_only",label:__("Update Required Only"),fieldtype:"Check",default:0},{fieldname:"include_closed",label:__("Include Closed"),fieldtype:"Check",default:0}
 ],
 formatter(value,row,column,data,default_formatter){value=default_formatter(value,row,column,data);if(!data)return value;if(column.fieldname==="performance_level"){const c={"Ahead":"blue","On Track":"green","Behind":"orange","Critical":"red"}[data.performance_level]||"gray";return `<span class="indicator-pill ${c}">${value}</span>`;}if(column.fieldname==="project_health"){const c={"On Track":"green","At Risk":"orange","Critical":"red","On Hold":"gray","Completed":"blue"}[data.project_health]||"gray";return `<span class="indicator-pill ${c}">${value}</span>`;}if(["activity_progress","indicator_achievement","overall_progress","time_elapsed","schedule_variance"].includes(column.fieldname)){const n=parseFloat(data[column.fieldname]||0),c=column.fieldname==="schedule_variance"?(n>=-10?"#2e7d32":n>=-25?"#f9a825":"#c62828"):(n>=90?"#2e7d32":n>=70?"#f9a825":"#c62828");return `<span style="color:${c};font-weight:600">${value}</span>`;}if(["activity_delayed","indicators_below_target","indicators_not_updated"].includes(column.fieldname)&&parseInt(data[column.fieldname]||0)>0)return `<span class="indicator-pill red">${value}</span>`;if(column.fieldname==="attention"&&data.attention)return `<span style="color:#b42318;font-weight:600">${value}</span>`;return value;},
 onload(report){["Executive","Headquarters","Project Management","Activities","Indicators","Timeline","Full"].forEach(view=>report.page.add_inner_button(__(view),()=>{report.set_filter_value("view_mode",view);report.refresh();},__("Views")));report.page.add_inner_button(__("Reset Filters"),()=>{["project","project_manager","project_stage","project_health","performance_level","donor","sector","implementing_partner","governorate","district","company"].forEach(f=>report.set_filter_value(f,[]));["from_date","to_date"].forEach(f=>report.set_filter_value(f,""));report.set_filter_value("view_mode","Executive");report.set_filter_value("donor_display_mode","Primary");report.set_filter_value("sector_display_mode","Primary");report.set_filter_value("partner_display_mode","All");report.set_filter_value("location_display_mode","All");report.set_filter_value("chart_by","Performance Level");report.set_filter_value("active_only",1);report.set_filter_value("attention_only",0);report.set_filter_value("delayed_only",0);report.set_filter_value("update_required_only",0);report.set_filter_value("include_closed",0);report.refresh();});const style=document.createElement("style");style.textContent=`.query-report .report-summary{gap:12px}.query-report .report-summary .summary-item{min-width:145px;padding:12px 16px;border:1px solid var(--border-color);border-radius:10px;background:var(--card-bg)}.query-report .chart-container{border:1px solid var(--border-color);border-radius:12px;padding:12px;margin-top:8px;background:var(--card-bg)}.query-report .datatable{border-radius:10px;overflow:hidden;border:1px solid var(--border-color)}.dt-cell__content{white-space:normal!important;line-height:1.35}.awesomplete>ul>li small,.multiselect-list .dropdown-menu small{display:block;white-space:normal;color:var(--text-muted);line-height:1.35;margin-top:2px}`;document.head.appendChild(style);}
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
