from __future__ import annotations

import frappe
from frappe.share import add, remove
from frappe.utils import now

from qfap_adds.qfap_adds.task_management.assignment_scope import supervisors
from qfap_adds.qfap_adds.task_management.settings import get_settings


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
