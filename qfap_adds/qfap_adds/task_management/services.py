from __future__ import annotations

import hashlib

import frappe
from frappe.share import add, remove
from frappe.utils import date_diff, flt, getdate, now

from qfap_adds.qfap_adds.task_management.scope import supervisors
from qfap_adds.qfap_adds.task_management.settings import get_settings

OPEN_REQUEST_STATES = ["Draft", "Pending Approval", "Approved", "Application Failed"]


def request_key(doc):
    raw = "|".join(str(value or "") for value in (
        doc.request_type, doc.company, doc.task_type, doc.requested_assignee,
        doc.project, doc.subject, doc.exp_start_date, doc.exp_end_date,
        doc.parent_task,
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_request_duplicate(doc):
    doc.duplicate_key = request_key(doc)
    other = frappe.db.get_value(
        "Task Assignment Request",
        {
            "duplicate_key": doc.duplicate_key,
            "workflow_state": ["in", OPEN_REQUEST_STATES],
            "name": ["!=", doc.name or ""],
        },
        "name",
    )
    if other:
        frappe.throw("A matching open Task Assignment Request already exists: " + other)


def validate_task_tree(task_name, parent_name):
    if not parent_name:
        return
    if task_name and task_name == parent_name:
        frappe.throw("A task cannot be its own parent.")
    settings = get_settings()
    seen = set()
    cursor = parent_name
    for _ in range(int(settings.maximum_task_tree_depth or 100)):
        if not cursor:
            return
        if cursor in seen:
            frappe.throw("A circular Task hierarchy already exists.")
        if task_name and cursor == task_name:
            frappe.throw("The selected main task would create a circular hierarchy.")
        seen.add(cursor)
        cursor = frappe.db.get_value("Task", cursor, "parent_task") or ""
    frappe.throw("Maximum Task hierarchy depth exceeded.")


def validate_period(project, start_date, end_date, is_workplan=False, throw=True):
    settings = get_settings()
    result = {"allowed": True, "classification": "No Project", "message": ""}
    if start_date and end_date and getdate(end_date) < getdate(start_date):
        result.update(allowed=False, classification="Invalid Dates", message="Expected End Date cannot be before Expected Start Date.")
    elif not project or not int(settings.enforce_project_period or 0):
        return result
    else:
        values = frappe.db.get_value("Project", project, ["expected_start_date", "expected_end_date"], as_dict=True)
        if not values:
            result.update(allowed=False, classification="Invalid Project", message="Project does not exist.")
        elif is_workplan and int(settings.allow_workplan_outside_period or 0):
            return result
        else:
            ps = getdate(values.expected_start_date) if values.expected_start_date else None
            pe = getdate(values.expected_end_date) if values.expected_end_date else None
            ts = getdate(start_date) if start_date else None
            te = getdate(end_date) if end_date else None
            if (not ps or not pe) and settings.missing_project_dates_policy == "Block":
                result.update(allowed=False, classification="Missing Project Dates", message="Project start and end dates are required.")
            elif ps and ts and ts < ps and not int(settings.allow_before_project_start or 0):
                result.update(allowed=False, classification="Before Project Start", message="Task starts before the Project period.")
            elif pe and ts and ts > pe and not int(settings.allow_after_project_end or 0):
                result.update(allowed=False, classification="After Project End", message="Task starts after the Project period.")
            elif pe and te and te > pe and not int(settings.allow_cross_project_end or 0):
                result.update(allowed=False, classification="Crosses Project End", message="Task ends after the Project period.")
            else:
                result["classification"] = "Within Project Period"
    if throw and not result["allowed"]:
        frappe.throw(result["message"])
    return result


def _different(current, value):
    if isinstance(value, float):
        return abs(flt(current) - value) > 0.0001
    return str(current or "") != str(value or "")


def rebuild(parent):
    """Rebuild a parent Task from direct children and return the applied values."""
    if not parent or not frappe.db.exists("Task", parent):
        return {}
    settings = get_settings()
    children = frappe.get_all(
        "Task",
        filters={"parent_task": parent, "status": ["not in", ["Cancelled", "Template"]]},
        fields=["status", "progress", "expected_time", "actual_time", "exp_end_date"],
        limit_page_length=10000,
    )
    count = len(children)
    completed = sum(1 for child in children if child.status == "Completed")
    if not count:
        values = {
            "custom_child_task_count": 0,
            "custom_completed_child_task_count": 0,
            "custom_parent_rollup_locked": 0,
        }
    else:
        expected = sum(flt(child.expected_time) for child in children)
        actual = sum(flt(child.actual_time) for child in children)
        weighted = sum(flt(child.progress) * flt(child.expected_time) for child in children)
        progress = weighted / expected if expected else sum(flt(child.progress) for child in children) / count
        end_dates = [getdate(child.exp_end_date) for child in children if child.exp_end_date]
        latest_end = max(end_dates) if end_dates else None
        parent_start = frappe.db.get_value("Task", parent, "exp_start_date")
        values = {
            "custom_child_task_count": count,
            "custom_completed_child_task_count": completed,
            "custom_parent_rollup_locked": 1 if int(settings.lock_parent_with_children or 0) else 0,
            "progress": 100 if completed == count else flt(progress, 2),
            # Parent hours are always authoritative rollups when children exist.
            "expected_time": flt(expected, 2),
            "actual_time": flt(actual, 2),
        }
        if latest_end:
            values["exp_end_date"] = latest_end
            if parent_start:
                values["custom_expected_days"] = flt(date_diff(latest_end, getdate(parent_start)) + 1, 2)
    current = frappe.db.get_value("Task", parent, list(values), as_dict=True) or {}
    changed = {field: value for field, value in values.items() if _different(current.get(field), value)}
    if changed:
        frappe.db.set_value("Task", parent, changed, update_modified=False)
    return values


def rebuild_chain(parent):
    settings = get_settings()
    seen = set()
    for _ in range(int(settings.maximum_task_tree_depth or 100)):
        if not parent or parent in seen:
            return
        seen.add(parent)
        rebuild(parent)
        parent = frappe.db.get_value("Task", parent, "parent_task") or ""


def _user(employee):
    return frappe.db.get_value("Employee", employee, "user_id") or ""


def _desired(task):
    settings = get_settings()
    wanted = {}
    if not task.get("custom_assign_to"):
        return wanted
    if int(settings.share_with_assignee or 0):
        user = _user(task.custom_assign_to)
        if user:
            wanted[user] = (task.custom_assign_to, "Assignee")
    if int(settings.share_with_supervisor_chain or 0):
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
            frappe.db.set_value("QFAP Managed Task Share", tracked[user].name, "last_reconciled_on", now(), update_modified=False)
            continue
        manual_share = frappe.db.get_value("DocShare", {"share_doctype": "Task", "share_name": task.name, "user": user}, "name")
        if manual_share and int(settings.protect_manual_shares or 0):
            continue
        if not manual_share:
            add("Task", task.name, user, read=1, write=int(settings.managed_share_write or 0), share=0, notify=0)
        share_name = frappe.db.get_value("DocShare", {"share_doctype": "Task", "share_name": task.name, "user": user}, "name")
        frappe.get_doc({
            "doctype": "QFAP Managed Task Share", "task": task.name, "user": user,
            "employee": employee, "reason": reason, "docshare": share_name,
            "active": 1, "last_reconciled_on": now(),
        }).insert(ignore_permissions=True)
    if not int(settings.remove_obsolete_managed_shares or 0):
        return
    for row in trackers:
        if row.user in wanted:
            continue
        if row.docshare and frappe.db.exists("DocShare", row.docshare):
            current = frappe.db.get_value("DocShare", row.docshare, ["share_doctype", "share_name", "user"], as_dict=True)
            if current and current.share_doctype == "Task" and current.share_name == task.name and current.user == row.user:
                remove("Task", task.name, row.user)
        frappe.db.set_value("QFAP Managed Task Share", row.name, "active", 0, update_modified=False)
