from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DEFAULTS = {
    "create_workplan_tasks_automatically": 1,
    "update_linked_workplan_tasks": 1,
    "show_task_execution_metrics_in_activities": 1,
    "warn_about_open_tasks_during_closure": 1,
    "block_closure_when_open_tasks_exist": 0,
    "default_workplan_task_type": "Workplan",
}

SETTINGS_FIELDS = [
    {"fieldname":"custom_project_cycle_integration_section","label":"Project Cycle Integration","fieldtype":"Section Break","insert_after":"fetch_timesheet_in_sales_invoice"},
    {"fieldname":"create_workplan_tasks_automatically","label":"Create Workplan Tasks Automatically","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_integration_section","description":"Create one operational parent Task for each Project Workplan Activity."},
    {"fieldname":"update_linked_workplan_tasks","label":"Update Linked Workplan Tasks","fieldtype":"Check","default":"1","insert_after":"create_workplan_tasks_automatically"},
    {"fieldname":"default_workplan_task_type","label":"Default Workplan Task Type","fieldtype":"Link","options":"Task Type","default":"Workplan","insert_after":"update_linked_workplan_tasks","description":"Task Type assigned automatically to parent Tasks created from Project Workplan Activities."},
    {"fieldname":"show_task_execution_metrics_in_activities","label":"Show Task Execution Metrics in Activities","fieldtype":"Check","default":"1","insert_after":"default_workplan_task_type"},
    {"fieldname":"custom_project_cycle_integration_column","fieldtype":"Column Break","insert_after":"show_task_execution_metrics_in_activities"},
    {"fieldname":"warn_about_open_tasks_during_closure","label":"Warn About Open Tasks During Closure","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_integration_column","description":"Informational only. Tasks do not determine Project completion."},
    {"fieldname":"block_closure_when_open_tasks_exist","label":"Block Closure When Open Tasks Exist","fieldtype":"Check","default":"0","insert_after":"warn_about_open_tasks_during_closure","description":"Optional exception. Disabled by default because Tasks are independent from Project completion."},
    {"fieldname":"custom_project_cycle_defaults_initialized","fieldtype":"Check","hidden":1,"read_only":1,"default":"0","insert_after":"block_closure_when_open_tasks_exist"},
]



def _ensure_workplan_task_type():
    if not frappe.db.exists("DocType", "Task Type"):
        return
    if frappe.db.exists("Task Type", "Workplan"):
        return

    task_type = frappe.new_doc("Task Type")
    task_type.name = "Workplan"
    if task_type.meta.has_field("type_name"):
        task_type.type_name = "Workplan"
    if task_type.meta.has_field("disabled"):
        task_type.disabled = 0
    task_type.insert(ignore_permissions=True)

def provision_project_management():
    _ensure_workplan_task_type()
    for old in ("project_cycle_integration_section","project_cycle_integration_column"):
        name=f"Projects Settings-{old}"
        if frappe.db.exists("Custom Field",name): frappe.delete_doc("Custom Field",name,ignore_permissions=True,force=True)
    create_custom_fields({"Projects Settings":SETTINGS_FIELDS},update=True)
    settings=frappe.get_single("Projects Settings")
    if not int(settings.get("custom_project_cycle_defaults_initialized") or 0):
        for name,value in DEFAULTS.items(): settings.set(name,value)
        settings.custom_project_cycle_defaults_initialized=1
        settings.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Projects Settings")
