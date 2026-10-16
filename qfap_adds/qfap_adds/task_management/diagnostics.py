from __future__ import annotations

import frappe

REQUIRED_FIELDS = [
    "custom_assign_to", "custom_user_id", "custom_task_assigned_by",
    "custom_self_assigned", "custom_project_workplan",
    "custom_task_timing_context", "custom_expected_days",
    "custom_supervisor_remarks", "custom_comments", "custom_task_locked",
    "custom_parent_rollup_locked", "custom_child_task_count",
    "custom_completed_child_task_count",
]
LEGACY_SERVER_SCRIPTS = [
    "Task Assignment Scope", "Task Project Workplan Parent Query", "Task Reopen",
    "Task Unlock Parent Summary", "Task Complete Parent Summary",
    "Task - Validate Lock Assignment", "Task - Parent Rollup and Access",
    "Task - Parent Rollup After Delete", "Weekly Employee Task Summary",
]

def task_integration_health():
    missing_fields = [name for name in REQUIRED_FIELDS if not frappe.db.exists("Custom Field", {"dt":"Task", "fieldname":name})]
    enabled_server = []
    if frappe.db.exists("DocType", "Server Script"):
        enabled_server = frappe.get_all("Server Script", filters={"name":["in",LEGACY_SERVER_SCRIPTS],"disabled":0}, pluck="name")
    enabled_client = []
    if frappe.db.exists("DocType", "Client Script"):
        enabled_client = frappe.get_all("Client Script", filters={"dt":"Task","enabled":1}, pluck="name")
    return {
        "ok": not missing_fields and not enabled_server and not enabled_client,
        "missing_fields": missing_fields,
        "enabled_legacy_server_scripts": enabled_server,
        "enabled_task_client_scripts": enabled_client,
        "roles": {"Reports Viewer": bool(frappe.db.exists("Role", "Reports Viewer"))},
        "notifications": {name: bool(frappe.db.exists("Notification", name)) for name in ["Task Assigned to Employee", "Supervisor Remark on Employee Task"]},
        "report": bool(frappe.db.exists("Report", "Employees Task Tracker")),
        "settings_doctype": bool(frappe.db.exists("DocType", "Task Management Settings")),
    }
