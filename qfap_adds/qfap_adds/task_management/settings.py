from __future__ import annotations

import frappe

DEFAULTS = {
    "enabled": 1,
    "administrative_role": "Task Management Administrator",
    "global_reopen_roles": "System Manager\nTask Management Administrator",
    "scope_mode": "Full Reporting Tree",
    "hierarchy_max_depth": 100,
    "same_company_only": 1,
    "allow_unassigned_standard_tasks": 1,
    "allow_self_assignment": 1,
    "outside_scope_policy": "Create Assignment Request",
    "enforce_project_period": 1,
    "allow_before_project_start": 0,
    "allow_after_project_end": 0,
    "allow_cross_project_end": 0,
    "allow_workplan_outside_period": 1,
    "missing_project_dates_policy": "Allow with Warning",
    "parent_must_same_project": 1,
    "allow_workplan_as_parent": 1,
    "exclude_locked_parents": 1,
    "maximum_task_tree_depth": 100,
    "lock_parent_with_children": 1,
    "require_children_completed": 1,
    "progress_calculation": "Weighted by Expected Hours",
    "rollup_expected_hours": 1,
    "rollup_actual_hours": 1,
    "enable_managed_sharing": 1,
    "share_with_assignee": 1,
    "share_with_supervisor_chain": 1,
    "managed_share_write": 1,
    "protect_manual_shares": 1,
    "remove_obsolete_managed_shares": 1,
    "enable_assignment_requests": 1,
    "prevent_self_approval": 1,
    "enable_notifications": 1,
    "weekly_summary_enabled": 1,
    "weekly_summary_recipients": "",
    "migration_batch_size": 200,
    "reconciliation_batch_size": 200,
    "warn_legacy_scripts": 1,
}


def get_settings():
    values = dict(DEFAULTS)
    if not frappe.db.exists("DocType", "Task Management Settings"):
        return frappe._dict(values)
    doc = frappe.get_single("Task Management Settings")
    for fieldname in DEFAULTS:
        value = doc.get(fieldname)
        if value not in (None, ""):
            values[fieldname] = value
    return frappe._dict(values)
