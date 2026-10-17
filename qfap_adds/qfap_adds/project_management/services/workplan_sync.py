from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from qfap_adds.qfap_adds.project_management.settings import get_project_cycle_settings


ACTIVITY_DOCTYPE = "Project Workplan Activity"
TASK_DOCTYPE = "Task"


def validate_activity(activity):
    if activity.planned_start_date and activity.planned_end_date:
        if activity.planned_end_date < activity.planned_start_date:
            frappe.throw(_("Planned End Date cannot be before Planned Start Date."))

    if activity.predecessor_activity == activity.name:
        frappe.throw(_("An activity cannot be its own predecessor."))

    if activity.predecessor_activity:
        predecessor_project = frappe.db.get_value(
            ACTIVITY_DOCTYPE, activity.predecessor_activity, "project"
        )
        if predecessor_project and predecessor_project != activity.project:
            frappe.throw(_("The predecessor activity must belong to the same Project."))


def sync_activity_task(activity_name: str) -> str | None:
    settings = get_project_cycle_settings()
    if not cint(settings.create_workplan_tasks_automatically):
        return None

    activity = frappe.get_doc(ACTIVITY_DOCTYPE, activity_name)
    task_name = _find_linked_task(activity)
    if task_name and not cint(settings.update_linked_workplan_tasks):
        _set_activity_task_link(activity, task_name)
        return task_name

    task = frappe.get_doc(TASK_DOCTYPE, task_name) if task_name else frappe.new_doc(TASK_DOCTYPE)
    if task.is_new():
        task.custom_project_workplan = 1
        task.is_group = 1
        task.custom_workplan_activity = activity.name

    _apply_planning_values(activity, task)
    task.flags.qfap_workplan_sync = True
    task.save(ignore_permissions=True)
    _set_activity_task_link(activity, task.name)
    return task.name


def _find_linked_task(activity) -> str | None:
    linked = activity.get("linked_workplan_task")
    if linked and frappe.db.exists(TASK_DOCTYPE, linked):
        return linked

    if frappe.get_meta(TASK_DOCTYPE).has_field("custom_workplan_activity"):
        linked = frappe.db.get_value(
            TASK_DOCTYPE,
            {"custom_workplan_activity": activity.name},
            "name",
        )
    return linked or None


def _apply_planning_values(activity, task):
    task.project = activity.project
    task.subject = activity.activity_name or activity.name
    task.description = activity.activity_description or ""
    task.exp_start_date = activity.planned_start_date
    task.exp_end_date = activity.planned_end_date

    if task.meta.has_field("custom_project_workplan"):
        task.custom_project_workplan = 1
    if task.meta.has_field("custom_workplan_activity"):
        task.custom_workplan_activity = activity.name
    if task.meta.has_field("is_group"):
        task.is_group = 1

    # Workplan Tasks are operational containers. Their status and progress do
    # not update Project progress or completion.
    if task.is_new() and task.meta.has_field("status"):
        task.status = "Open"


def _set_activity_task_link(activity, task_name: str):
    if not activity.meta.has_field("linked_workplan_task"):
        return
    if activity.linked_workplan_task == task_name:
        return
    frappe.db.set_value(
        ACTIVITY_DOCTYPE,
        activity.name,
        "linked_workplan_task",
        task_name,
        update_modified=False,
    )


def validate_activity_deletion(activity):
    task_name = _find_linked_task(activity)
    if not task_name:
        return

    child_count = frappe.db.count(TASK_DOCTYPE, {"parent_task": task_name})
    has_time = frappe.db.get_value(TASK_DOCTYPE, task_name, "actual_time") or 0
    if child_count or has_time:
        frappe.throw(
            _(
                "This activity is linked to Workplan Task {0}, which contains execution data. "
                "Cancel or archive the activity instead of deleting it."
            ).format(frappe.bold(task_name))
        )

    frappe.delete_doc(TASK_DOCTYPE, task_name, ignore_permissions=True)
