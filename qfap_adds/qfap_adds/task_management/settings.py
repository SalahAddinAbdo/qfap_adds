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
    "auto_calculate_expected_hours": 1,
    "working_hours_per_day": 8,
    "enable_managed_sharing": 1,
    "share_with_assignee": 1,
    "share_with_supervisor_chain": 1,
    "managed_share_write": 1,
    "protect_manual_shares": 1,
    "remove_obsolete_managed_shares": 1,
    "enable_assignment_requests": 1,
    "prevent_self_approval": 1,
    "enable_notifications": 1,
    "summary_schedule_enabled": 1,
    "summary_frequency": "Weekly",
    "summary_send_time": "08:00:00",
    "summary_weekly_day": "Sunday",
    "summary_monthly_day": 1,
    "summary_email_subject": "Task Summary | {employee_name} | {report_date}",
    "summary_send_to_employees": 1,
    "summary_period_mode": "Automatic by Frequency",
    "summary_rolling_days": 7,
    "summary_include_carried_forward": 1,
    "summary_include_undated": 0,
    "summary_include_operational": 1,
    "summary_include_main_tasks": 1,
    "summary_include_workplan": 0,
    "summary_include_completed": 1,
    "summary_include_overdue": 1,
    "summary_include_due_soon": 1,
    "summary_due_soon_days": 7,
    "summary_only_attention": 0,
    "summary_progress_warning": 25,
    "summary_stale_days": 7,
    "summary_exclude_zero_hours": 0,
    "summary_detail_level": "Full Task Details",
    "summary_max_tasks": 25,
    "summary_show_project": 1,
    "summary_show_status": 1,
    "summary_show_priority": 1,
    "summary_show_progress": 1,
    "summary_show_due_date": 1,
    "summary_show_expected_hours": 1,
    "summary_show_actual_hours": 1,
    "summary_show_task_type": 1,
    "summary_show_assigned_by": 0,

    "summary_last_period_key": "",
    "migration_batch_size": 200,
    "reconciliation_batch_size": 200,
    "warn_legacy_scripts": 1,
}


def get_settings():
    values = dict(DEFAULTS)
    if not frappe.db.exists("DocType", "Task Management Settings"):
        return frappe._dict(values)
    doc = frappe.get_single("Task Management Settings")
    values.update({field: doc.get(field) for field in DEFAULTS if doc.get(field) not in (None, "")})
    values["global_reopen_role_rows"] = doc.get("global_reopen_role_rows") or []
    values["summary_recipients"] = doc.get("summary_recipients") or []
    values["summary_filter_rows"] = doc.get("summary_filter_rows") or []
    values["summary_email_template"] = doc.get("summary_email_template")
    values["summary_last_period_key"] = doc.get("summary_last_period_key") or ""
    return frappe._dict(values)


def role_lines(value):
    if not value:
        return []
    values = value if isinstance(value, (list, tuple, set)) else str(value).replace(",", "\n").splitlines()
    result, seen = [], set()
    for item in values:
        role = str(item or "").strip()
        if role and role not in seen:
            seen.add(role); result.append(role)
    return result


def get_global_reopen_roles(settings=None):
    settings = settings or get_settings()
    roles = []
    for row in settings.get("global_reopen_role_rows") or []:
        if int(row.get("enabled") or 0) and row.get("role") and row.role not in roles:
            roles.append(row.role)
    return roles or role_lines(settings.get("global_reopen_roles"))


def get_additional_recipient_emails(settings=None):
    settings = settings or get_settings()
    emails, seen = [], set()
    for row in settings.get("summary_recipients") or []:
        if not int(row.get("enabled") or 0):
            continue
        email = ""
        if row.get("recipient_type") == "System User" and row.get("user"):
            email = frappe.db.get_value("User", row.user, "email") or ""
        elif row.get("recipient_type") == "External Email":
            email = row.get("external_email") or ""
        key = email.strip().lower()
        if key and key not in seen:
            seen.add(key); emails.append(email.strip())
    if emails:
        return emails
    for email in str(settings.get("weekly_summary_recipients") or "").replace(",", "\n").splitlines():
        key = email.strip().lower()
        if key and key not in seen:
            seen.add(key); emails.append(email.strip())
    return emails
