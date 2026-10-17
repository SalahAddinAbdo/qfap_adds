from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


PROJECT_SETTINGS_FIELDS = [
    {
        "fieldname": "project_cycle_integration_section",
        "label": "Project Cycle Integration",
        "fieldtype": "Section Break",
        "insert_after": "allow_to_extend_project_end_date",
    },
    {
        "fieldname": "create_workplan_tasks_automatically",
        "label": "Create Workplan Tasks Automatically",
        "fieldtype": "Check",
        "default": "1",
        "insert_after": "project_cycle_integration_section",
        "description": "Create one operational parent Task for each Project Workplan Activity.",
    },
    {
        "fieldname": "update_linked_workplan_tasks",
        "label": "Update Linked Workplan Tasks",
        "fieldtype": "Check",
        "default": "1",
        "insert_after": "create_workplan_tasks_automatically",
    },
    {
        "fieldname": "show_task_execution_metrics_in_activities",
        "label": "Show Task Execution Metrics in Activities",
        "fieldtype": "Check",
        "default": "1",
        "insert_after": "update_linked_workplan_tasks",
    },
    {
        "fieldname": "project_cycle_integration_column",
        "fieldtype": "Column Break",
        "insert_after": "show_task_execution_metrics_in_activities",
    },
    {
        "fieldname": "warn_about_open_tasks_during_closure",
        "label": "Warn About Open Tasks During Closure",
        "fieldtype": "Check",
        "default": "1",
        "insert_after": "project_cycle_integration_column",
        "description": "Informational only. Tasks do not determine Project completion.",
    },
    {
        "fieldname": "block_closure_when_open_tasks_exist",
        "label": "Block Closure When Open Tasks Exist",
        "fieldtype": "Check",
        "default": "0",
        "insert_after": "warn_about_open_tasks_during_closure",
        "description": "Optional exception. Disabled by default because Tasks are independent from Project completion.",
    },
]


def provision_project_management():
    custom_fields = {
        "Projects Settings": PROJECT_SETTINGS_FIELDS,
        "Task": [
            {
                "fieldname": "custom_workplan_activity",
                "label": "Workplan Activity",
                "fieldtype": "Link",
                "options": "Project Workplan Activity",
                "read_only": 1,
                "no_copy": 1,
                "unique": 1,
                "insert_after": "custom_project_workplan",
                "depends_on": "eval:doc.custom_project_workplan",
            }
        ],
        "Project Workplan Activity": [
            {
                "fieldname": "linked_workplan_task",
                "label": "Linked Workplan Task",
                "fieldtype": "Link",
                "options": "Task",
                "read_only": 1,
                "no_copy": 1,
                "unique": 1,
                "insert_after": "activity_name",
            }
        ],
    }
    create_custom_fields(custom_fields, update=True)
    frappe.clear_cache(doctype="Projects Settings")
    frappe.clear_cache(doctype="Task")
    frappe.clear_cache(doctype="Project Workplan Activity")
