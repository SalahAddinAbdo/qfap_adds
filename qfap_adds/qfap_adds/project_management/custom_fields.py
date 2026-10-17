from __future__ import annotations

PROJECT_MANAGEMENT_CUSTOM_FIELDS = {
    "Projects Settings": [
        {"fieldname":"custom_project_cycle_integration_section","label":"Project Cycle Integration","fieldtype":"Section Break","insert_after":"fetch_timesheet_in_sales_invoice"},
        {"fieldname":"create_workplan_tasks_automatically","label":"Create Workplan Tasks Automatically","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_integration_section","description":"Create one operational parent Task for each Project Workplan Activity."},
        {"fieldname":"update_linked_workplan_tasks","label":"Update Linked Workplan Tasks","fieldtype":"Check","default":"1","insert_after":"create_workplan_tasks_automatically"},
        {"fieldname":"show_task_execution_metrics_in_activities","label":"Show Task Execution Metrics in Activities","fieldtype":"Check","default":"1","insert_after":"update_linked_workplan_tasks"},
        {"fieldname":"custom_project_cycle_integration_column","fieldtype":"Column Break","insert_after":"show_task_execution_metrics_in_activities"},
        {"fieldname":"warn_about_open_tasks_during_closure","label":"Warn About Open Tasks During Closure","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_integration_column","description":"Informational only. Tasks do not determine Project completion."},
        {"fieldname":"block_closure_when_open_tasks_exist","label":"Block Closure When Open Tasks Exist","fieldtype":"Check","default":"0","insert_after":"warn_about_open_tasks_during_closure","description":"Optional exception. Disabled by default because Tasks are independent from Project completion."},
        {"fieldname":"custom_project_cycle_defaults_initialized","fieldtype":"Check","default":"0","hidden":1,"read_only":1,"insert_after":"block_closure_when_open_tasks_exist"},
    ],
    "Task": [
        {"fieldname":"custom_workplan_activity","label":"Workplan Activity","fieldtype":"Link","options":"Project Workplan Activity","insert_after":"custom_project_workplan","depends_on":"eval:doc.custom_project_workplan","read_only":1,"no_copy":1,"unique":1},
    ],
}

PROJECT_MANAGEMENT_DEFAULTS = {
    "create_workplan_tasks_automatically": 1,
    "update_linked_workplan_tasks": 1,
    "show_task_execution_metrics_in_activities": 1,
    "warn_about_open_tasks_during_closure": 1,
    "block_closure_when_open_tasks_exist": 0,
}
