from __future__ import annotations
import frappe
from frappe.utils import flt

def rebuild(parent):
    if not parent:return {}
    children=frappe.get_all("Task",filters={"parent_task":parent,"status":["not in",["Cancelled","Template"]]},fields=["status","progress","expected_time","actual_time","exp_start_date","exp_end_date"],limit_page_length=10000)
    count=len(children); completed=sum(1 for x in children if x.status=="Completed"); expected=sum(flt(x.expected_time) for x in children); actual=sum(flt(x.actual_time) for x in children)
    weighted=sum(flt(x.progress)*flt(x.expected_time) for x in children); progress=(weighted/expected if expected else (sum(flt(x.progress) for x in children)/count if count else 0))
    values={"custom_child_task_count":count,"custom_completed_child_task_count":completed,"progress":progress,"custom_parent_rollup_locked":1 if count else 0}
    if frappe.get_meta("Task").has_field("expected_time"):values["expected_time"]=expected
    if frappe.get_meta("Task").has_field("actual_time"):values["actual_time"]=actual
    frappe.db.set_value("Task",parent,values,update_modified=False); return values

def rebuild_chain(parent):
    seen=set()
    while parent and parent not in seen:
        seen.add(parent); rebuild(parent); parent=frappe.db.get_value("Task",parent,"parent_task") or ""
