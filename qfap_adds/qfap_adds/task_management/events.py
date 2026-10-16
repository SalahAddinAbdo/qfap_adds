from __future__ import annotations

import frappe
from frappe.utils import nowdate

from qfap_adds.qfap_adds.task_management.assignment_scope import (
    can_manage_employee,
    employee_for_user,
)
from qfap_adds.qfap_adds.task_management.duplicate_guard import validate_task_tree
from qfap_adds.qfap_adds.task_management.project_period import validate_period
from qfap_adds.qfap_adds.task_management.rollup import rebuild_chain
from qfap_adds.qfap_adds.task_management.settings import get_settings
from qfap_adds.qfap_adds.task_management.sharing import sync

PROTECTED_FIELDS = (
    "status", "project", "subject", "type", "priority", "custom_assign_to",
    "custom_task_assigned_by", "custom_self_assigned", "parent_task",
    "exp_start_date", "exp_end_date", "expected_time", "progress",
    "custom_project_workplan", "custom_task_timing_context",
)


def _validate_completed_lock(doc):
    if doc.is_new():
        return
    old = doc.get_doc_before_save()
    if not old or not int(old.get("custom_task_locked") or 0):
        return
    if getattr(doc.flags, "qfap_reopen", False):
        return
    changed = [field for field in PROTECTED_FIELDS if str(old.get(field) or "") != str(doc.get(field) or "")]
    if changed:
        frappe.throw("This task is completed and locked. Use Reopen Task before changing operational fields.")


def _validate_parent(doc, settings):
    validate_task_tree(None if doc.is_new() else doc.name, doc.parent_task)
    if not doc.parent_task:
        return
    parent = frappe.db.get_value(
        "Task", doc.parent_task,
        ["project", "is_group", "status", "custom_task_locked"], as_dict=True,
    )
    if not parent:
        frappe.throw("The selected main task does not exist.")
    if settings.get("parent_must_same_project", 1) and (parent.project or "") != (doc.project or ""):
        frappe.throw("The main task and child task must belong to the same Project.")
    if not int(parent.is_group or 0):
        frappe.throw("The selected main task must be a group task.")
    if parent.status in ("Completed", "Cancelled", "Template"):
        frappe.throw("A completed, cancelled, or template task cannot be selected as a main task.")
    if int(settings.exclude_locked_parents or 0) and int(parent.custom_task_locked or 0):
        frappe.throw("A locked task cannot be selected as a main task.")


def _prepare_assignment(doc, settings):
    if int(doc.get("custom_project_workplan") or 0):
        doc.is_group = 1
        doc.custom_assign_to = None
        doc.custom_user_id = None
        doc.custom_task_assigned_by = None
        doc.custom_self_assigned = 0
        doc.department = None
        return

    assignee = doc.get("custom_assign_to")
    if not assignee:
        if int(settings.allow_unassigned_standard_tasks or 0):
            doc.custom_user_id = None
            doc.custom_task_assigned_by = None
            doc.custom_self_assigned = 0
            return
        frappe.throw("Assign To is required for employee tasks.")
    employee = frappe.db.get_value(
        "Employee", assignee,
        ["status", "user_id", "department", "company"], as_dict=True,
    )
    if not employee or employee.status != "Active":
        frappe.throw("The assigned Employee must be active.")
    if not employee.user_id or not frappe.db.get_value("User", employee.user_id, "enabled"):
        frappe.throw("The assigned Employee must be linked to an enabled User account.")

    current_employee = employee_for_user()
    is_self = bool(current_employee and current_employee == assignee)
    if is_self and not int(settings.allow_self_assignment or 0):
        frappe.throw("Self-assignment is disabled in Task Management Settings.")
    if not can_manage_employee(assignee) and not getattr(doc.flags, "from_assignment_request", False):
        frappe.throw("You cannot assign a task outside your administrative scope. Create a Task Assignment Request instead.")

    doc.custom_user_id = employee.user_id
    doc.department = employee.department
    doc.custom_self_assigned = 1 if is_self else 0
    if is_self:
        doc.custom_task_assigned_by = current_employee
    elif not doc.get("custom_task_assigned_by"):
        doc.custom_task_assigned_by = current_employee
    if not doc.custom_task_assigned_by:
        frappe.throw("Assigned By could not be determined from the current User.")


def _prepare_completion(doc):
    if doc.status == "Completed":
        doc.progress = 100
        doc.custom_task_locked = 1
        doc.completed_by = doc.completed_by or frappe.session.user
        doc.completed_on = doc.completed_on or nowdate()
        doc.closing_date = doc.closing_date or nowdate()


def before_validate(doc, method=None):
    settings = get_settings()
    if not int(settings.enabled or 0):
        return
    _validate_completed_lock(doc)
    _validate_parent(doc, settings)
    validate_period(
        doc.project, doc.exp_start_date, doc.exp_end_date,
        bool(doc.get("custom_project_workplan")), True,
    )
    _prepare_assignment(doc, settings)
    _prepare_completion(doc)


def on_update(doc, method=None):
    settings = get_settings()
    if not int(settings.enabled or 0):
        return
    old = doc.get_doc_before_save()
    old_parent = old.parent_task if old else None
    sync(doc)
    if old_parent and old_parent != doc.parent_task:
        rebuild_chain(old_parent)
    rebuild_chain(doc.parent_task)


def after_delete(doc, method=None):
    rebuild_chain(doc.parent_task)
