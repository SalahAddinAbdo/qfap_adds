// v3.3 VIRTUAL PARENT FOR STANDALONE TASKS - Frappe 16
// v3.2 ORGANIZED GROUP HIERARCHY AND STANDALONE TASKS SECTION - Frappe 16
// v3.1 CORRECTED COMPLETE HIERARCHY AND ADAPTIVE STICKY COLUMNS - Frappe 16
// v3.0 HIERARCHICAL PARENT TASKS AND ADAPTIVE STICKY COLUMNS - Frappe 16
// v2.9 CORRECT POST-FILTER INCREMENTAL LOADING - Frappe 16
// v2.8 FULL SUMMARY VIEWS AND INCREMENTAL DETAIL - Frappe 16
// v2.7 LOAD MORE AND TASK YEAR - Frappe 16
// v2.6 PROFESSIONAL ADAPTIVE INTERFACE - Frappe 16
// v2.5 MY TASKS AND SERVER PAGINATION - Frappe 16
// v2.4 CONDITIONAL TASK LINKS - Frappe 16
// v2.3 VISUAL GROUP SEPARATORS - Frappe 16
// v2.2 ORGANIZED OPERATIONAL VIEWS - Frappe 16
// v2.1 VERIFIED VIEWS AND PROJECT NAMES - Frappe 16
frappe.query_reports["Employees Task Tracker"]={filters:[
{fieldname:"view",label:__("View"),fieldtype:"Select",options:["Operational Overview","Employee Workload","Department Workload","Project Workload","Overdue Tasks","Due Soon","Pending Review","Project Workplans","Data Quality Exceptions","Full"].join("\n"),default:"Operational Overview",on_change:()=>{frappe.query_report.set_filter_value("page_number",1);const v=frappe.query_report.get_filter_value("view");frappe.query_report.set_filter_value("overdue_only",0);frappe.query_report.set_filter_value("due_soon_only",0);frappe.query_report.set_filter_value("quality_exceptions_only",0);if(v==="Project Workplans")frappe.query_report.set_filter_value("workplan_filter","Project Workplans Only");else if(frappe.query_report.get_filter_value("workplan_filter")==="Project Workplans Only")frappe.query_report.set_filter_value("workplan_filter","");frappe.query_report.refresh();}},
{fieldname:"task_year",label:__("Task Year"),fieldtype:"Select",options:get_task_year_options(),default:String(new Date().getFullYear()),description:__("Filters tasks by expected due date. Clear the value to display all years."),on_change:()=>{frappe.query_report.set_filter_value("page_number",1);frappe.query_report.refresh();}},{fieldname:"my_tasks_only",label:__("Show My Assigned Tasks Only"),fieldtype:"Check",default:1,description:__("When enabled, the report shows only tasks assigned to your linked Employee record."),on_change:()=>{frappe.query_report.set_filter_value("page_number",1);frappe.query_report.refresh();}},{fieldname:"records_per_page",label:__("Records Added Each Time"),fieldtype:"Select",options:"50\n100\n200\n500",default:"50",description:__("Choose how many additional records are displayed each time you click Load More."),on_change:()=>{frappe.query_report.set_filter_value("page_number",1);frappe.query_report.refresh();}},{fieldname:"page_number",label:__("Current Page"),fieldtype:"Int",default:1,hidden:1},
{fieldname:"companies",label:__("Companies"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Company",txt)},{fieldname:"departments",label:__("Departments"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Department",txt)},{fieldname:"branches",label:__("Branches"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_branches",txt)},{fieldname:"employees",label:__("Employees"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Employee",txt)},{fieldname:"projects",label:__("Projects"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Project",txt)},{fieldname:"task_types",label:__("Task Types"),fieldtype:"MultiSelectList",get_data:(txt)=>frappe.db.get_link_options("Task Type",txt)},{fieldname:"statuses",label:__("Statuses"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_statuses",txt)},{fieldname:"priorities",label:__("Priorities"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_priorities",txt)},{fieldname:"due_buckets",label:__("Due Buckets"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_due_buckets",txt)},{fieldname:"assignment_types",label:__("Assignment Types"),fieldtype:"MultiSelectList",get_data:(txt)=>ctx("_context_assignment_types",txt)},
{fieldname:"organize_by",label:__("Organize By"),fieldtype:"Select",options:"Management Priority\nEmployee\nDepartment\nBranch\nTask Type\nStatus\nPriority\nProject\nParent Task",default:"Management Priority",on_change:()=>frappe.query_report.refresh()},{fieldname:"secondary_sort",label:__("Then Sort By"),fieldtype:"Select",options:"Due Date\nEmployee\nDepartment\nTask Type\nPriority\nProgress\nSubject",default:"Due Date",on_change:()=>frappe.query_report.refresh()},{fieldname:"show_group_column",label:__("Show Organization Column"),fieldtype:"Check",default:1},{fieldname:"group_separator_style",label:__("Group Separator"),fieldtype:"Select",options:"Strong Line\nSoft Line\nLabel Only",default:"Strong Line",on_change:()=>frappe.query_report.refresh()},{fieldname:"task_level",label:__("Task Level"),fieldtype:"Select",options:"\nMain Task\nSub Task"},{fieldname:"workplan_filter",label:__("Workplan Filter"),fieldtype:"Select",options:"\nProject Workplans Only\nRegular Tasks Only"},{fieldname:"from_date",label:__("Start From"),fieldtype:"Date"},{fieldname:"to_date",label:__("Due To"),fieldtype:"Date"},{fieldname:"subject",label:__("Subject Contains"),fieldtype:"Data"},{fieldname:"include_group_tasks",label:__("Include Group Tasks"),fieldtype:"Check",default:0},{fieldname:"milestones_only",label:__("Milestones Only"),fieldtype:"Check",default:0},{fieldname:"overdue_only",label:__("Overdue Only"),fieldtype:"Check",default:0},{fieldname:"due_soon_only",label:__("Due Soon Only"),fieldtype:"Check",default:0},{fieldname:"quality_exceptions_only",label:__("Data Exceptions Only"),fieldtype:"Check",default:0}],
onload(r){
const quick=(label,vals)=>r.page.add_inner_button(__(label),()=>{Object.keys(vals).forEach(k=>r.set_filter_value(k,vals[k]));r.set_filter_value("page_number",1);r.refresh();});
r._ett_load_more_btn=r.page.add_inner_button(__("Load More"),()=>{const p=Math.max(1,Number(r.get_filter_value("page_number")||1)+1);r.set_filter_value("page_number",p);r.refresh();});
quick("Overdue",{view:"Overdue Tasks",workplan_filter:"Regular Tasks Only",overdue_only:0,due_soon_only:0,quality_exceptions_only:0,statuses:[]});
quick("Due Soon",{view:"Due Soon",workplan_filter:"Regular Tasks Only",overdue_only:0,due_soon_only:0,quality_exceptions_only:0,statuses:[]});
quick("Pending Review",{view:"Pending Review",workplan_filter:"Regular Tasks Only",statuses:[],overdue_only:0,due_soon_only:0});
quick("Workplans",{view:"Project Workplans",workplan_filter:"Project Workplans Only",statuses:[],overdue_only:0,due_soon_only:0});
r.page.add_inner_button(__("Reset Filters"),()=>{const d={view:"Operational Overview",task_year:String(new Date().getFullYear()),my_tasks_only:1,records_per_page:"50",page_number:1,organize_by:"Management Priority",secondary_sort:"Due Date",show_group_column:1,group_separator_style:"Strong Line",include_group_tasks:0,milestones_only:0,overdue_only:0,due_soon_only:0,quality_exceptions_only:0};Object.keys(r.get_values()).forEach(k=>r.set_filter_value(k,d[k]!==undefined?d[k]:[]));r.refresh();});
bind_incremental_reset(r);
adapt_task_tracker_ui(r);
},
after_refresh(r){adapt_task_tracker_ui(r);},
formatter(v,row,col,d,fmt){let x=fmt(v,row,col,d);if(!d)return x;if(col.fieldname==="task"&&v&&Number(d.can_open_task||0)===1)x=conditional_task_link(v);if(col.fieldname==="parent_task"&&v&&Number(d.can_open_parent_task||0)===1)x=conditional_task_link(v);const colors={Open:"blue",Working:"orange","Pending Review":"purple",Overdue:"red",Completed:"green",Cancelled:"gray",Urgent:"red",High:"orange",Medium:"blue",Low:"gray","Due Today":"red","Due in 3 Days":"orange","Due in 7 Days":"yellow",Later:"blue","No Due Date":"gray"};if(["display_status","priority","due_bucket","assignment_type","task_level"].includes(col.fieldname))x=pill(v,colors[v]||"gray");if(col.fieldname==="progress"){const n=Number(v||0),safe=Math.max(0,Math.min(n,100)),c=n>=100?"#16a34a":n<25?"#ef4444":n<75?"#f59e0b":"#2490ef";x=`<div style="position:relative;height:18px;min-width:78px;overflow:hidden;border-radius:9px;background:#e9ecef"><div style="width:${safe}%;height:100%;background:${c}"></div><span style="position:absolute;inset:0;text-align:center;line-height:18px;font-size:11px;font-weight:600">${n.toFixed(0)}%</span></div>`;}if(col.fieldname==="subject"&&d.project_workplan)x=`<span style="color:#1d4ed8;font-weight:700">${x}</span>`;if(col.fieldname==="subject"&&d.display_status==="Overdue")x=`<span style="color:#c92a2a;font-weight:650">${x}</span>`;if(col.fieldname==="subject"&&d.hierarchy_number){const depth=Math.max(0,Number(d.hierarchy_depth||0));const number=frappe.utils.escape_html(String(d.hierarchy_number||""));const virtualGroup=Number(d.hierarchy_virtual_group||0)===1;const isGroup=Number(d.is_group||0)===1||virtualGroup;const hasChildren=Number(d.hierarchy_has_children||0)===1;const marker=hasChildren?"▾":"•";const weight=isGroup?"700":"400";const color=isGroup?"#0f172a":"#334155";x=`<div style="display:flex;align-items:flex-start;gap:4px;padding-inline-start:${depth*8}px;color:${color};font-weight:${weight};white-space:normal;line-height:1.35"><span style="display:inline-block;min-width:31px;color:#64748b;font-weight:${isGroup?700:500};white-space:nowrap">${number}</span><span style="display:inline-block;width:9px;color:${isGroup?"#2563eb":"#94a3b8"};font-weight:700">${marker}</span><span style="white-space:normal">${x}</span></div>`;}if(col.fieldname==="delay_days"&&Number(v||0)>0)x=pill(v,"red");if(col.fieldname==="quality_flags"&&v)x=`<span style="color:#c0392b;white-space:normal">${frappe.utils.escape_html(v)}</span>`;if(col.fieldname==="organization_group_display"&&d.group_start)x=`<span style="display:inline-block;padding:3px 9px;border-radius:12px;background:#e8f3ff;color:#1d4ed8;font-weight:700;white-space:normal">${frappe.utils.escape_html(String(v||""))}</span>`;if(d.group_start){const style=frappe.query_report.get_filter_value("group_separator_style")||"Strong Line";const hierarchyRoot=(Number(d.is_group||0)===1||Number(d.hierarchy_virtual_group||0)===1)&&Boolean(d.hierarchy_number)&&Number(d.hierarchy_depth||0)===0;const border=style==="Strong Line"?"2px solid #64748b":style==="Soft Line"?"1px solid #cbd5e1":"0";const bg=hierarchyRoot?"rgba(226,232,240,0.50)":style==="Label Only"?"transparent":"rgba(241,245,249,0.55)";const topSpace=hierarchyRoot?7:(style==="Label Only"?0:5);x=`<div style="border-top:${border};background:${bg};padding-top:${topSpace}px;padding-bottom:${hierarchyRoot?5:0}px;min-height:22px">${x}</div>`;}return x;}}
function conditional_task_link(task_name){const task=String(task_name||"");const label=frappe.utils.escape_html(task);const route="/app/task/"+encodeURIComponent(task);return `<a href="${route}" data-doctype="Task" data-name="${frappe.utils.escape_html(task)}">${label}</a>`;}
function pill(v,c){return `<span class="indicator-pill ${c}">${frappe.utils.escape_html(String(v||""))}</span>`;}
function ctx(f,t){const q=(t||"").toLowerCase(),vals=[];(frappe.query_report.data||[]).forEach(r=>String(r[f]||"").split(",").forEach(i=>{const v=i.trim();if(v&&!vals.includes(v)&&(!q||v.toLowerCase().includes(q)))vals.push(v);}));vals.sort((a,b)=>a.localeCompare(b));return vals.map(v=>({value:v,description:desc(f,v)}));}
function desc(f,v){let c=0,ps=[];(frappe.query_report.data||[]).forEach(r=>{if(String(r[f]||"").split(",").map(i=>i.trim()).includes(v)){c++;if(r.project&&!ps.includes(r.project))ps.push(r.project);}});return `${c} record${c===1?"":"s"}${ps.length?" • "+ps.slice(0,3).join(" • "):""}`;}

function adapt_task_tracker_ui(r){
const myOnly=Number(r.get_filter_value("my_tasks_only")||0)===1;
const page=Math.max(1,Number(r.get_filter_value("page_number")||1));
const data=r.data||frappe.query_report.data||[];
const first=data.length?data[0]:{};
const hasMore=Number(first._pagination_has_next||0)===1;
const view=r.get_filter_value("view")||"Operational Overview";
const summaryView=["Employee Workload","Department Workload","Project Workload"].includes(view);
toggle_report_filter(r,"employees",!myOnly);
toggle_report_filter(r,"records_per_page",!summaryView&&hasMore);
toggle_report_filter(r,"page_number",false);
if(r._ett_load_more_btn)r._ett_load_more_btn.toggle(!summaryView&&hasMore);
}
function toggle_report_filter(r,fieldname,show){
const f=r.get_filter(fieldname);
if(f&&f.$wrapper)f.$wrapper.toggle(Boolean(show));
}
function get_task_year_options(){
const current=new Date().getFullYear();
const years=[""];
for(let y=current+1;y>=current-10;y--)years.push(String(y));
return years.join("\n");
}

function bind_incremental_reset(r){
const excluded=["page_number","records_per_page","organize_by","secondary_sort","show_group_column","group_separator_style"];
(r.filters||[]).forEach(f=>{
if(!f||!f.df||excluded.includes(f.df.fieldname)||!f.$input)return;
f.$input.off("change.ett_reset").on("change.ett_reset",()=>{
if(Number(r.get_filter_value("page_number")||1)!==1)r.set_filter_value("page_number",1);
});
});
}
