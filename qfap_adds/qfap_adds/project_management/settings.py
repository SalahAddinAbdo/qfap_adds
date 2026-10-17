from __future__ import annotations

import frappe
from frappe.utils import cint

DEFAULTS = {
    "create_workplan_tasks_automatically": 1,
    "update_linked_workplan_tasks": 1,
    "show_task_execution_metrics_in_activities": 1,
    "warn_about_open_tasks_during_closure": 1,
    "block_closure_when_open_tasks_exist": 0,
    "default_workplan_task_type": "Workplan",
}


def get_project_cycle_settings():
    values = frappe._dict(DEFAULTS.copy())
    if not frappe.db.exists("DocType", "Projects Settings"):
        return values
    meta = frappe.get_meta("Projects Settings")
    fields = [name for name in DEFAULTS if meta.has_field(name)]
    if not fields:
        return values
    stored = frappe.db.get_value("Projects Settings", "Projects Settings", fields, as_dict=True) or {}
    check_fields = {
        "create_workplan_tasks_automatically",
        "update_linked_workplan_tasks",
        "show_task_execution_metrics_in_activities",
        "warn_about_open_tasks_during_closure",
        "block_closure_when_open_tasks_exist",
    }
    for name in fields:
        if name in check_fields:
            values[name] = cint(stored.get(name))
        else:
            values[name] = stored.get(name) or DEFAULTS.get(name)
    return values
