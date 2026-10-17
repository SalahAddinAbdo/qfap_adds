from __future__ import annotations
import frappe
from frappe.utils import flt

def rebuild_project_summary(project):
    if not project or not frappe.db.exists("Project", project):
        return
    project_meta=frappe.get_meta("Project")
    updates={}
    activities=frappe.get_all("Project Workplan Activity",filters={"project":project,"status":["not in",["Cancelled","Inactive"]]},fields=["approved_progress","weight"])
    if activities:
        weighted=sum(flt(x.approved_progress)*flt(x.weight or 0) for x in activities)
        weights=sum(flt(x.weight or 0) for x in activities)
        activity_progress=weighted/weights if weights else sum(flt(x.approved_progress) for x in activities)/len(activities)
    else: activity_progress=0
    for field in ("custom_activities_progress_percentage","percent_complete"):
        if project_meta.has_field(field): updates[field]=round(activity_progress,2)
    indicators=frappe.get_all("Project Indicator",filters={"project":project,"status":["!=","Inactive"]},pluck="name") if frappe.db.exists("DocType","Project Indicator") else []
    if indicators and frappe.db.exists("DocType","Indicator Result Entry"):
        vals=frappe.get_all("Indicator Result Entry",filters={"indicator":["in",indicators]},pluck="achievement_percentage")
        achievement=sum(flt(v) for v in vals)/len(vals) if vals else 0
        if project_meta.has_field("custom_indicators_achievement_percentage"): updates["custom_indicators_achievement_percentage"]=round(achievement,2)
    critical_risks=frappe.db.count("Project Risk",{"project":project,"risk_level":"Critical","status":["not in",["Closed","Inactive"]]}) if frappe.db.exists("DocType","Project Risk") else 0
    overdue_deliverables=frappe.db.count("Project Compliance Deliverable",{"project":project,"monitoring_status":["in",["Overdue","Critical"]]}) if frappe.db.exists("DocType","Project Compliance Deliverable") else 0
    health="Critical" if critical_risks or overdue_deliverables else ("At Risk" if activity_progress < 70 else "On Track")
    if project_meta.has_field("custom_calculated_project_health"): updates["custom_calculated_project_health"]=health
    if updates: frappe.db.set_value("Project",project,updates,update_modified=False)
