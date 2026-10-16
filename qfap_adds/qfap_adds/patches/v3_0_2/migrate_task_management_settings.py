from __future__ import annotations

import frappe
from frappe.utils import validate_email_address


def execute():
    if not frappe.db.exists("DocType", "Task Management Settings"):
        return
    settings = frappe.get_single("Task Management Settings")
    changed = False

    defaults = {
        "enabled": 1,
        "scope_mode": "Full Reporting Tree",
        "hierarchy_max_depth": 100,
        "same_company_only": 1,
        "allow_unassigned_standard_tasks": 1,
        "allow_self_assignment": 1,
        "outside_scope_policy": "Create Assignment Request",
        "administrative_role": "Task Management Administrator",
        "summary_schedule_enabled": 1,
        "summary_frequency": "Weekly",
        "summary_send_time": "08:00:00",
        "summary_weekly_day": "Sunday",
        "summary_monthly_day": 1,
        "summary_send_to_employees": 1,
    }
    meta = frappe.get_meta("Task Management Settings")
    for fieldname, value in defaults.items():
        if meta.has_field(fieldname) and settings.get(fieldname) in (None, "", 0) and value not in (0, ""):
            settings.set(fieldname, value); changed = True

    existing_roles = {row.role for row in settings.get("global_reopen_role_rows") or [] if row.role}
    for role in str(settings.get("global_reopen_roles") or "").replace(",", "\n").splitlines():
        role = role.strip()
        if role and frappe.db.exists("Role", role) and role not in existing_roles:
            settings.append("global_reopen_role_rows", {"role": role, "enabled": 1}); existing_roles.add(role); changed = True

    existing_emails = set()
    for row in settings.get("summary_recipients") or []:
        email = row.external_email or (frappe.db.get_value("User", row.user, "email") if row.user else "")
        if email: existing_emails.add(email.lower())
    for email in str(settings.get("weekly_summary_recipients") or "").replace(",", "\n").splitlines():
        email = email.strip()
        if email and validate_email_address(email, throw=False) and email.lower() not in existing_emails:
            settings.append("summary_recipients", {"recipient_type": "External Email", "external_email": email, "enabled": 1}); existing_emails.add(email.lower()); changed = True

    if changed:
        settings.save(ignore_permissions=True)
