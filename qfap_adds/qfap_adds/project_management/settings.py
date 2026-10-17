from __future__ import annotations

import frappe
from frappe.utils import cint


DEFAULTS = {
    "create_workplan_tasks_automatically": 1,
    "update_linked_workplan_tasks": 1,
    "show_task_execution_metrics_in_activities": 1,
    "warn_about_open_tasks_during_closure": 1,
    "block_closure_when_open_tasks_exist": 0,
}


def get_project_cycle_settings():
    values = frappe._dict(DEFAULTS.copy())
    if not frappe.db.exists("DocType", "Projects Settings"):
        return values

    meta = frappe.get_meta("Projects Settings")
    available = {field.fieldname for field in meta.fields}
    requested = [fieldname for fieldname in DEFAULTS if fieldname in available]
    if not requested:
        return values

    stored = frappe.db.get_value("Projects Settings", "Projects Settings", requested, as_dict=True) or {}
    for fieldname in requested:
        values[fieldname] = cint(stored.get(fieldname))
    return values
