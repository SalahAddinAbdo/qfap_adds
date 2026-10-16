from __future__ import annotations
import frappe
from frappe.utils import getdate
from qfap_adds.qfap_adds.task_management.settings import get_settings

def validate_period(project,start_date,end_date,is_workplan=False,throw=True):
    result={"allowed":True,"classification":"No Project","message":""}
    if not project:return result
    values=frappe.db.get_value("Project",project,["expected_start_date","expected_end_date","status"],as_dict=True)
    if not values:
        result.update(allowed=False,classification="Invalid Project",message="Project does not exist.")
    else:
        ps=getdate(values.expected_start_date) if values.expected_start_date else None; pe=getdate(values.expected_end_date) if values.expected_end_date else None
        ts=getdate(start_date) if start_date else None; te=getdate(end_date) if end_date else None; settings=get_settings()
        if is_workplan and settings.allow_workplan_outside_period:return result
        if ps and ts and ts<ps and not settings.allow_before_project_start:result.update(allowed=False,classification="Before Project Start",message="Task starts before the project period.")
        elif pe and ts and ts>pe and not settings.allow_after_project_end:result.update(allowed=False,classification="After Project End",message="Task starts after the project period.")
        elif pe and te and te>pe and not settings.allow_cross_project_end:result.update(allowed=False,classification="Crosses Project End",message="Task ends after the project period.")
        else:result["classification"]="Within Project Period"
    if throw and not result["allowed"]:frappe.throw(result["message"])
    return result
