from __future__ import annotations

import hashlib

import frappe
from frappe.share import add, remove
from frappe.utils import flt, getdate, now

from qfap_adds.qfap_adds.task_management.scope import supervisors
from qfap_adds.qfap_adds.task_management.settings import get_settings

# Duplicate and hierarchy validation
import hashlib, frappe

OPEN_STATES=["Draft","Pending Approval","Approved","Application Failed"]
def request_key(doc):
    raw="|".join([doc.request_type or "", doc.company or "", doc.task_type or "", doc.requested_assignee or "", doc.project or "", doc.subject or "",str(doc.exp_start_date or ""),str(doc.exp_end_date or ""),doc.parent_task or ""])
    return hashlib.sha256(raw.encode()).hexdigest()
def validate_request_duplicate(doc):
    doc.duplicate_key=request_key(doc)
    filters={"duplicate_key":doc.duplicate_key,"workflow_state":["in",OPEN_STATES],"name":["!=",doc.name or ""]}
    other=frappe.db.get_value("Task Assignment Request",filters,"name")
    if other:frappe.throw("A matching open Task Assignment Request already exists: "+other)
def validate_task_tree(task_name,parent_name):
    if not parent_name:return
    if task_name and task_name==parent_name:frappe.throw("A task cannot be its own parent.")
    seen=set(); cursor=parent_name
    while cursor:
        if cursor in seen:frappe.throw("A circular Task hierarchy already exists.")
        seen.add(cursor)
        if task_name and cursor==task_name:frappe.throw("The selected main task would create a circular hierarchy.")
        cursor=frappe.db.get_value("Task",cursor,"parent_task") or ""


# Project period policy
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


# Parent task rollup
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


# Managed task sharing
def _user(employee):
    return frappe.db.get_value("Employee", employee, "user_id") or ""


def _desired(task):
    wanted = {}
    if not task.get("custom_assign_to"):
        return wanted
    user = _user(task.custom_assign_to)
    if user:
        wanted[user] = (task.custom_assign_to, "Assignee")
    for employee in supervisors(task.custom_assign_to):
        user = _user(employee)
        if user and user not in wanted:
            wanted[user] = (employee, "Supervisor Chain")
    return wanted


def sync(task):
    settings = get_settings()
    if not int(settings.enable_managed_sharing or 0) or task.is_new():
        return
    wanted = _desired(task)
    trackers = frappe.get_all(
        "QFAP Managed Task Share", filters={"task": task.name, "active": 1},
        fields=["name", "user", "docshare"], limit_page_length=10000,
    )
    tracked = {row.user: row for row in trackers}

    for user, (employee, reason) in wanted.items():
        if user in tracked:
            frappe.db.set_value(
                "QFAP Managed Task Share", tracked[user].name,
                {"last_reconciled_on": now()}, update_modified=False,
            )
            continue
        # Existing untracked DocShare is manual. Preserve it and do not adopt it.
        manual_share = frappe.db.get_value(
            "DocShare", {"share_doctype": "Task", "share_name": task.name, "user": user}, "name"
        )
        if manual_share:
            continue
        add(
            "Task", task.name, user, read=1,
            write=int(settings.managed_share_write or 0), share=0, notify=0,
        )
        share_name = frappe.db.get_value(
            "DocShare", {"share_doctype": "Task", "share_name": task.name, "user": user}, "name"
        )
        frappe.get_doc({
            "doctype": "QFAP Managed Task Share", "task": task.name,
            "user": user, "employee": employee, "reason": reason,
            "docshare": share_name, "active": 1, "last_reconciled_on": now(),
        }).insert(ignore_permissions=True)

    for row in trackers:
        if row.user in wanted:
            continue
        # Remove only DocShares whose exact name is owned by this tracker.
        if row.docshare and frappe.db.exists("DocShare", row.docshare):
            current = frappe.db.get_value(
                "DocShare", row.docshare, ["share_doctype", "share_name", "user"], as_dict=True
            )
            if current and current.share_doctype == "Task" and current.share_name == task.name and current.user == row.user:
                remove("Task", task.name, row.user)
        frappe.db.set_value("QFAP Managed Task Share", row.name, "active", 0, update_modified=False)
