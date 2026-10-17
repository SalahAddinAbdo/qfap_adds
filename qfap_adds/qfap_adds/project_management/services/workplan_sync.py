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
    task_name = activity.get("linked_workplan_task") or frappe.db.get_value(TASK_DOCTYPE, {"custom_workplan_activity": activity.name}, "name")
    if not task_name: return
    child_count = frappe.db.count(TASK_DOCTYPE, {"parent_task": task_name})
    actual_time = frappe.db.get_value(TASK_DOCTYPE, task_name, "actual_time") or 0
    if child_count or actual_time:
        frappe.throw(_("Linked Workplan Task {0} contains execution data. Cancel or archive the activity instead of deleting it.").format(frappe.bold(task_name)))
    frappe.delete_doc(TASK_DOCTYPE, task_name, ignore_permissions=True)
