from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt
from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings

def achievement(actual, target, direction="Higher is Better", settings=None):
    settings=settings or get_project_cycle_settings()
    actual=flt(actual); target=flt(target)
    if not target:
        return 100.0 if actual and direction=="Lower is Better" else 0.0
    value=(target/actual*100) if direction=="Lower is Better" and actual else (actual/target*100)
    return max(0.0, value if settings.allow_progress_above_100 else min(value, flt(settings.maximum_displayed_achievement or 100)))

def validate_progress_update(doc):
    settings=get_project_cycle_settings()
    seen_activities=set(); seen_indicators=set()
    for row in doc.get("activity_progress_entries") or []:
        if row.activity in seen_activities: frappe.throw(_("Activity {0} is duplicated.").format(frappe.bold(row.activity)))
        seen_activities.add(row.activity)
        project=frappe.db.get_value("Project Workplan Activity",row.activity,"project")
        if project != doc.project: frappe.throw(_("Activity {0} does not belong to this Project.").format(frappe.bold(row.activity)))
        maximum=flt(settings.maximum_displayed_achievement or 100)
        row.progress_percentage=max(0, flt(row.progress_percentage) if settings.allow_progress_above_100 else min(flt(row.progress_percentage),maximum))
        if settings.require_evidence_for_progress_updates and not (row.get("evidence") or row.get("evidence_reference")): frappe.throw(_("Evidence is required for Activity {0}.").format(frappe.bold(row.activity)))
    for row in doc.get("indicator_result_entries") or []:
        if row.indicator in seen_indicators: frappe.throw(_("Indicator {0} is duplicated.").format(frappe.bold(row.indicator)))
        seen_indicators.add(row.indicator)
        values=frappe.db.get_value("Project Indicator",row.indicator,["project","improvement_direction"],as_dict=True)
        if not values or values.project != doc.project: frappe.throw(_("Indicator {0} does not belong to this Project.").format(frappe.bold(row.indicator)))
        row.achievement_percentage=achievement(row.cumulative_actual,row.cumulative_target,values.improvement_direction,settings)
        if settings.require_verified_indicator_results and row.data_quality_status != "Verified": frappe.throw(_("Indicator {0} must be Verified.").format(frappe.bold(row.indicator)))

def apply_approved_update(doc):
    settings=get_project_cycle_settings()
    if not settings.update_project_progress_automatically or doc.status != "Approved" or doc.get("update_locked"):
        return
    for row in doc.get("activity_progress_entries") or []:
        frappe.db.set_value("Project Workplan Activity",row.activity,{"actual_quantity":row.cumulative_actual_quantity,"approved_progress":row.progress_percentage,"status":row.period_status},update_modified=False)
    doc.db_set("update_locked",1,update_modified=False)
    meta=frappe.get_meta("Project")
    updates={}
    if meta.has_field("custom_latest_approved_progress_update"): updates["custom_latest_approved_progress_update"]=doc.name
    if meta.has_field("custom_latest_progress_update_date"): updates["custom_latest_progress_update_date"]=doc.period_end_date
    if meta.has_field("custom_latest_reporting_period"): updates["custom_latest_reporting_period"]=doc.reporting_period_label
    if updates: frappe.db.set_value("Project",doc.project,updates,update_modified=False)
    from qfap_adds.qfap_adds.project_management.services.project_summary import rebuild_project_summary
    rebuild_project_summary(doc.project)
