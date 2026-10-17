from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings

ACTIVITY_DOCTYPE = "Project Workplan Activity"
TASK_DOCTYPE = "Task"



def _get_workplan_task_type(settings):
    task_type = str(settings.get("default_workplan_task_type") or "Workplan").strip()
    if not task_type:
        frappe.throw(_("Default Workplan Task Type is not configured in Projects Settings."))
    if not frappe.db.exists("Task Type", task_type):
        frappe.throw(
            _("Task Type {0} does not exist. Configure Default Workplan Task Type in Projects Settings.").format(
                frappe.bold(task_type)
            )
        )
    return task_type

def sync_activity_task(activity):
    settings = get_project_cycle_settings()
    if not cint(settings.create_workplan_tasks_automatically):
        return None
    task_name = activity.get("linked_workplan_task")
    if not task_name:
        task_name = frappe.db.get_value(TASK_DOCTYPE, {"custom_workplan_activity": activity.name}, "name")
    if task_name and not cint(settings.update_linked_workplan_tasks):
        return task_name
    task = frappe.get_doc(TASK_DOCTYPE, task_name) if task_name else frappe.new_doc(TASK_DOCTYPE)
    task.project = activity.project
    task.subject = activity.activity_name or activity.name
    task.description = activity.activity_description or ""
    task.exp_start_date = activity.planned_start_date
    task.exp_end_date = activity.planned_end_date
    task.custom_project_workplan = 1
    task.custom_workplan_activity = activity.name
    task.is_group = 1
    if task.is_new():
        task.status = "Open"
        task.type = _get_workplan_task_type(settings)
    task.flags.qfap_workplan_sync = True
    task.save(ignore_permissions=True)
    if activity.linked_workplan_task != task.name:
        frappe.db.set_value(ACTIVITY_DOCTYPE, activity.name, "linked_workplan_task", task.name, update_modified=False)
    return task.name


def validate_activity_deletion(activity):
    """Delete an unused linked Workplan Task with its Activity.

    Direct deletion of a linked Task remains blocked by Frappe. Deleting the
    owning Activity is the controlled path: execution data is checked first,
    both links are cleared inside the same database transaction, and then the
    empty Task is deleted. Any failure rolls the transaction back.
    """
    task_name = activity.get("linked_workplan_task") or frappe.db.get_value(
        TASK_DOCTYPE,
        {"custom_workplan_activity": activity.name},
        "name",
    )
    if not task_name or not frappe.db.exists(TASK_DOCTYPE, task_name):
        return

    child_count = frappe.db.count(TASK_DOCTYPE, {"parent_task": task_name})
    task_values = frappe.db.get_value(
        TASK_DOCTYPE,
        task_name,
        ["actual_time", "total_expense_claim"],
        as_dict=True,
    ) or {}

    if child_count:
        frappe.throw(
            _("Linked Workplan Task {0} has child Tasks. Remove or reassign them before deleting the Activity.").format(
                frappe.bold(task_name)
            )
        )
    if float(task_values.get("actual_time") or 0) > 0:
        frappe.throw(
            _("Linked Workplan Task {0} has actual working hours and cannot be deleted with the Activity.").format(
                frappe.bold(task_name)
            )
        )
    if float(task_values.get("total_expense_claim") or 0) > 0:
        frappe.throw(
            _("Linked Workplan Task {0} has Expense Claim activity and cannot be deleted with the Activity.").format(
                frappe.bold(task_name)
            )
        )

    # Break the two-way relationship before deleting the Task. This avoids the
    # LinkExistsError while keeping direct Task deletion protected.
    if activity.meta.has_field("linked_workplan_task"):
        activity.linked_workplan_task = None
        frappe.db.set_value(
            ACTIVITY_DOCTYPE,
            activity.name,
            "linked_workplan_task",
            None,
            update_modified=False,
        )

    task_meta = frappe.get_meta(TASK_DOCTYPE)
    if task_meta.has_field("custom_workplan_activity"):
        frappe.db.set_value(
            TASK_DOCTYPE,
            task_name,
            "custom_workplan_activity",
            None,
            update_modified=False,
        )

    frappe.delete_doc(TASK_DOCTYPE, task_name, ignore_permissions=True)

