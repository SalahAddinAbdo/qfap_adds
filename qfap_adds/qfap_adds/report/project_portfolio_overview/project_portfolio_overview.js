const PPO_STAGE_OPTIONS=["Idea","Concept Development","Internal Review","Proposal Development","Ready for Submission","Submitted to Donor","Under Donor Review","Approved","Pre-Implementation","Under Implementation","Operationally Completed","Under Closure","Closed","Post-Project Monitoring","Deferred","Rejected","Cancelled"];
const PPO_HEALTH_OPTIONS=["Not Assessed","On Track","At Risk","Critical","Completed","On Hold"];
const PPO_FUNDING_OPTIONS=["Not Yet Identified","Potential Funding","Under Development","Submitted","Under Donor Review","Approved","Partially Approved","Rejected","Withdrawn","Self-Funded","Not Applicable"];
const PPO_MODALITY_OPTIONS=["Not Yet Determined","Direct Implementation","Through Implementing Partner","Consortium","Mixed Implementation"];

function ppo_static_options(values,txt){
    const q=(txt||"").toLowerCase();
    return values.filter(v=>v.toLowerCase().includes(q)).map(v=>({value:v,description:""}));
}
function ppo_rows(){return (frappe.query_report&&frappe.query_report.data)||[];}
function ppo_split(value,separator="|||"){return String(value||"").split(separator).map(v=>v.trim()).filter(Boolean);}
function ppo_project_label(row){return row.project_name||row.project||"";}
function ppo_short_projects(projects){
    const unique=[];
    projects.forEach(value=>{if(value&&!unique.includes(value))unique.push(value);});
    if(!unique.length)return "";
    const shown=unique.slice(0,3).join(" • ");
    return unique.length>3?`${shown} • +${unique.length-3} more`:shown;
}
function ppo_context_options(fieldname,txt,kind){
    const q=(txt||"").toLowerCase(),map={};
    ppo_rows().forEach(row=>{
        ppo_split(row[fieldname]).forEach(value=>{
            if(!map[value])map[value]={projects:[],primary:0};
            const label=ppo_project_label(row);
            if(label&&!map[value].projects.includes(label))map[value].projects.push(label);
            if((kind==="donor"&&row.primary_donor===value)||(kind==="sector"&&row.primary_sector===value)||(kind==="governorate"&&row.governorate===value))map[value].primary+=1;
        });
    });
    return Object.keys(map).filter(value=>value.toLowerCase().includes(q)).sort((a,b)=>a.localeCompare(b)).map(value=>{
        const info=map[value],count=info.projects.length;
        let description=`${count} project${count===1?"":"s"}`;
        if(info.primary)description+=` • Primary in ${info.primary}`;
        const projects=ppo_short_projects(info.projects);
        if(projects)description+=` • ${projects}`;
        return {value,description};
    });
}
function ppo_manager_options(txt){
    const q=(txt||"").toLowerCase(),map={};
    ppo_rows().forEach(row=>{
        const value=row.project_manager||"",name=row.project_manager_name||value;
        if(value){
            if(!map[value])map[value]={name,projects:[]};
            const project=ppo_project_label(row);
            if(project&&!map[value].projects.includes(project))map[value].projects.push(project);
        }
    });
    return Object.keys(map).filter(value=>value.toLowerCase().includes(q)||map[value].name.toLowerCase().includes(q)).sort((a,b)=>map[a].name.localeCompare(map[b].name)).map(value=>{
        const item=map[value],count=item.projects.length,projects=ppo_short_projects(item.projects);
        return {value,description:`${item.name} • ${count} project${count===1?"":"s"}${projects?` • ${projects}`:""}`};
    });
}
function ppo_district_options(txt){
    const q=(txt||"").toLowerCase(),governorates=frappe.query_report.get_filter_value("governorate")||[],map={};
    ppo_rows().forEach(row=>{
        ppo_split(row.location_pairs,";;;").forEach(pair=>{
            const parts=pair.split("|||"),governorate=parts[0]||"",district=parts[1]||"";
            if(!district||governorates.length&&!governorates.includes(governorate))return;
            if(!map[district])map[district]={governorates:[],projects:[]};
            if(governorate&&!map[district].governorates.includes(governorate))map[district].governorates.push(governorate);
            const project=ppo_project_label(row);
            if(project&&!map[district].projects.includes(project))map[district].projects.push(project);
        });
    });
    return Object.keys(map).filter(value=>value.toLowerCase().includes(q)).sort((a,b)=>a.localeCompare(b)).map(value=>{
        const item=map[value],count=item.projects.length,projects=ppo_short_projects(item.projects);
        return {value,description:`${item.governorates.join(", ")} • ${count} project${count===1?"":"s"}${projects?` • ${projects}`:""}`};
    });
}

frappe.query_reports["Project Portfolio Overview"]={
 filters:[
  {fieldname:"view_mode",label:__("View"),fieldtype:"Select",options:["Executive","Donor","Operations","Full"].join("\n"),default:"Executive"},
  {fieldname:"project",label:__("Projects"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Project",txt);}},
  {fieldname:"project_manager",label:__("Project Managers"),fieldtype:"MultiSelectList",get_data:ppo_manager_options},
  {fieldname:"project_stage",label:__("Stages"),fieldtype:"MultiSelectList",get_data(txt){return ppo_static_options(PPO_STAGE_OPTIONS,txt);}},
  {fieldname:"project_health",label:__("Health Statuses"),fieldtype:"MultiSelectList",get_data(txt){return ppo_static_options(PPO_HEALTH_OPTIONS,txt);}},
  {fieldname:"donor",label:__("Donors"),fieldtype:"MultiSelectList",get_data(txt){return ppo_context_options("all_donors",txt,"donor");}},
  {fieldname:"sector",label:__("Sectors"),fieldtype:"MultiSelectList",get_data(txt){return ppo_context_options("all_sectors",txt,"sector");}},
  {fieldname:"implementing_partner",label:__("Implementing Partners"),fieldtype:"MultiSelectList",get_data(txt){return ppo_context_options("all_partners",txt,"partner");}},
  {fieldname:"governorate",label:__("Governorates"),fieldtype:"MultiSelectList",get_data(txt){return ppo_context_options("all_governorates",txt,"governorate");},on_change(){frappe.query_report.set_filter_value("district",[]);frappe.query_report.refresh();}},
  {fieldname:"district",label:__("Districts"),fieldtype:"MultiSelectList",get_data:ppo_district_options},
  {fieldname:"funding_status",label:__("Funding Statuses"),fieldtype:"MultiSelectList",get_data(txt){return ppo_static_options(PPO_FUNDING_OPTIONS,txt);}},
  {fieldname:"implementation_modality",label:__("Implementation Modalities"),fieldtype:"MultiSelectList",get_data(txt){return ppo_static_options(PPO_MODALITY_OPTIONS,txt);}},
  {fieldname:"company",label:__("Companies"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Company",txt);}},
  {fieldname:"project_currency",label:__("Currencies"),fieldtype:"MultiSelectList",get_data(txt){return frappe.db.get_link_options("Currency",txt);}},
  {fieldname:"donor_display_mode",label:__("Donors in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
  {fieldname:"sector_display_mode",label:__("Sectors in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
  {fieldname:"partner_display_mode",label:__("Partners in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"All",on_change(){frappe.query_report.refresh();}},
  {fieldname:"location_display_mode",label:__("Locations in Column"),fieldtype:"Select",options:["Primary","All"].join("\n"),default:"Primary",on_change(){frappe.query_report.refresh();}},
  {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},{fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
  {fieldname:"chart_by",label:__("Chart By"),fieldtype:"Select",options:["Stage","Health","Sector","Governorate","Donor"].join("\n"),default:"Stage"},
  {fieldname:"active_only",label:__("Active Only"),fieldtype:"Check",default:1},{fieldname:"attention_only",label:__("Need Attention Only"),fieldtype:"Check",default:0},{fieldname:"include_closed",label:__("Include Closed"),fieldtype:"Check",default:0}
 ],
 formatter(value,row,column,data,default_formatter){value=default_formatter(value,row,column,data);if(!data)return value;if(column.fieldname==="project_health"){const c={"On Track":"green","At Risk":"orange","Critical":"red","On Hold":"gray","Completed":"blue"}[data.project_health]||"gray";return `<span class="indicator-pill ${c}">${value}</span>`;}if(column.fieldname==="project_stage"){const c={"Under Implementation":"blue","Operationally Completed":"green","Under Closure":"orange","Closed":"gray","Cancelled":"red","Rejected":"red"}[data.project_stage]||"gray";return `<span class="indicator-pill ${c}">${value}</span>`;}if(column.fieldname==="attention"&&data.attention)return `<span style="color:#b42318;font-weight:600">${value}</span>`;if(["activities_progress","indicator_achievement","time_elapsed"].includes(column.fieldname)){const n=parseFloat(data[column.fieldname]||0),c=n>=90?"#2e7d32":n>=70?"#f9a825":"#c62828";return `<span style="color:${c};font-weight:600">${value}</span>`;}if(["critical_risks","critical_issues","delayed_activities","overdue_deliverables"].includes(column.fieldname)&&parseInt(data[column.fieldname]||0)>0)return `<span class="indicator-pill red">${value}</span>`;return value;},
 onload(report){report.page.add_inner_button(__("Executive"),()=>{report.set_filter_value("view_mode","Executive");report.refresh();},__("Views"));report.page.add_inner_button(__("Donor"),()=>{report.set_filter_value("view_mode","Donor");report.refresh();},__("Views"));report.page.add_inner_button(__("Operations"),()=>{report.set_filter_value("view_mode","Operations");report.refresh();},__("Views"));report.page.add_inner_button(__("Full"),()=>{report.set_filter_value("view_mode","Full");report.refresh();},__("Views"));report.page.add_inner_button(__("Reset Filters"),()=>{["project","project_manager","project_stage","project_health","donor","sector","implementing_partner","governorate","district","funding_status","implementation_modality","company","project_currency"].forEach(f=>report.set_filter_value(f,[]));["from_date","to_date"].forEach(f=>report.set_filter_value(f,""));report.set_filter_value("view_mode","Executive");report.set_filter_value("donor_display_mode","Primary");report.set_filter_value("sector_display_mode","Primary");report.set_filter_value("partner_display_mode","All");report.set_filter_value("location_display_mode","Primary");report.set_filter_value("chart_by","Stage");report.set_filter_value("active_only",1);report.set_filter_value("attention_only",0);report.set_filter_value("include_closed",0);report.refresh();});const style=document.createElement("style");style.textContent=`.query-report .report-summary{gap:12px}.query-report .report-summary .summary-item{min-width:145px;padding:12px 16px;border:1px solid var(--border-color);border-radius:10px;background:var(--card-bg)}.query-report .chart-container{border:1px solid var(--border-color);border-radius:12px;padding:12px;margin-top:8px;background:var(--card-bg)}.query-report .datatable{border-radius:10px;overflow:hidden;border:1px solid var(--border-color)}.dt-cell__content{white-space:normal!important;line-height:1.35}.awesomplete>ul>li small,.multiselect-list .dropdown-menu small{display:block;white-space:normal;color:var(--text-muted);line-height:1.35;margin-top:2px}`;document.head.appendChild(style);}
};

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
 const config=frappe.query_reports["Project Portfolio Overview"];
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
