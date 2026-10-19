from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

ALL_SCOPES = {
    "progress_updates", "activities", "indicators", "risks_issues",
    "changes", "compliance", "beneficiaries", "budget", "closure", "health",
}
CLOSED = {"Closed", "Cancelled", "Inactive", "Rejected", "Implemented", "Completed"}


def _exists(doctype):
    return bool(frappe.db.exists("DocType", doctype))


def _fields(doctype, names):
    meta = frappe.get_meta(doctype)
    return [name for name in names if meta.has_field(name)]


def _rows(doctype, project, names, extra_filters=None, order_by=None):
    if not _exists(doctype):
        return []
    fields = _fields(doctype, names)
    if "name" not in fields:
        fields.insert(0, "name")
    filters = {"project": project}
    filters.update(extra_filters or {})
    return frappe.get_all(
        doctype, filters=filters, fields=fields,
        order_by=order_by, limit_page_length=0,
    )


def _set_if(meta, values, fieldname, value):
    if meta.has_field(fieldname):
        values[fieldname] = value


def _status(row):
    return str(row.get("status") or "").strip()


def _active(row):
    return int(row.get("docstatus") or 0) != 2 and _status(row) not in {"Cancelled", "Inactive", "Rejected"}


def _latest_approved_update(project):
    rows = _rows(
        "Project Progress Update", project,
        ["name", "status", "docstatus", "period_end_date", "update_date", "modified"],
        order_by="period_end_date desc, modified desc",
    )
    for row in rows:
        if int(row.get("docstatus") or 0) == 2:
            continue
        if row.get("status") == "Approved" or int(row.get("docstatus") or 0) == 1:
            return row
    return None


def _reconcile_activity_entries(project):
    """Rebuild approved activity progress from approved updates, latest period wins."""
    if not _exists("Project Progress Update") or not _exists("Project Workplan Activity"):
        return
    updates = _rows(
        "Project Progress Update", project,
        ["name", "status", "docstatus", "period_end_date", "modified"],
        order_by="period_end_date asc, modified asc",
    )
    latest = {}
    for row in updates:
        if int(row.get("docstatus") or 0) == 2:
            continue
        if row.get("status") != "Approved" and int(row.get("docstatus") or 0) != 1:
            continue
        doc = frappe.get_doc("Project Progress Update", row.name)
        for entry in doc.get("activity_progress_entries") or []:
            if entry.get("activity"):
                latest[entry.activity] = flt(entry.get("progress_percentage"))
    activities = frappe.get_all(
        "Project Workplan Activity", filters={"project": project}, pluck="name",
        limit_page_length=0,
    )
    meta = frappe.get_meta("Project Workplan Activity")
    if not meta.has_field("approved_progress"):
        return
    for activity in activities:
        value = latest.get(activity, 0)
        current = flt(frappe.db.get_value("Project Workplan Activity", activity, "approved_progress"))
        if round(current, 6) != round(value, 6):
            frappe.db.set_value(
                "Project Workplan Activity", activity, "approved_progress", value,
                update_modified=False,
            )


def _activity_values(project, meta):
    rows = _rows(
        "Project Workplan Activity", project,
        ["name", "status", "approved_progress", "weight", "health_status"],
    )
    rows = [row for row in rows if _active(row)]
    total = len(rows)
    weighted = sum(flt(row.get("approved_progress")) * flt(row.get("weight")) for row in rows)
    weights = sum(flt(row.get("weight")) for row in rows)
    progress = weighted / weights if weights else (
        sum(flt(row.get("approved_progress")) for row in rows) / total if total else 0
    )
    values = {}
    _set_if(meta, values, "custom_total_activities", total)
    _set_if(meta, values, "custom_completed_activities", sum(1 for row in rows if _status(row) == "Completed" or flt(row.get("approved_progress")) >= 100))
    _set_if(meta, values, "custom_in_progress_activities", sum(1 for row in rows if _status(row) in {"In Progress", "Working"}))
    _set_if(meta, values, "custom_not_started_activities", sum(1 for row in rows if _status(row) in {"Not Started", "Open", "Planned", ""}))
    _set_if(meta, values, "custom_on_hold_activities", sum(1 for row in rows if _status(row) == "On Hold"))
    _set_if(meta, values, "custom_delayed_activities", sum(1 for row in rows if _status(row) in {"Delayed", "Overdue"}))
    _set_if(meta, values, "custom_at_risk_activities", sum(1 for row in rows if str(row.get("health_status") or "") == "At Risk"))
    _set_if(meta, values, "custom_critical_activities", sum(1 for row in rows if str(row.get("health_status") or "") == "Critical"))
    _set_if(meta, values, "custom_activities_progress_percentage", round(progress, 2))
    return values, progress


def _indicator_values(project, meta):
    indicators = _rows("Project Indicator", project, ["name", "status"])
    indicators = [row for row in indicators if _active(row)]
    latest = {}
    updates = _rows(
        "Project Progress Update", project,
        ["name", "status", "docstatus", "period_end_date", "modified"],
        order_by="period_end_date asc, modified asc",
    )
    for row in updates:
        if int(row.get("docstatus") or 0) == 2:
            continue
        if row.get("status") != "Approved" and int(row.get("docstatus") or 0) != 1:
            continue
        doc = frappe.get_doc("Project Progress Update", row.name)
        for entry in doc.get("indicator_result_entries") or []:
            if entry.get("indicator"):
                latest[entry.indicator] = flt(entry.get("achievement_percentage"))
    scores = [latest[row.name] for row in indicators if row.name in latest]
    assessed = len(scores)
    total = len(indicators)
    achievement = sum(scores) / assessed if assessed else 0
    values = {}
    _set_if(meta, values, "custom_total_indicators", total)
    _set_if(meta, values, "custom_assessed_indicators", assessed)
    _set_if(meta, values, "custom_not_assessed_indicators", max(0, total - assessed))
    _set_if(meta, values, "custom_targets_exceeded", sum(1 for value in scores if value > 100))
    _set_if(meta, values, "custom_targets_achieved", sum(1 for value in scores if value >= 100))
    _set_if(meta, values, "custom_indicators_on_track", sum(1 for value in scores if 75 <= value < 100))
    _set_if(meta, values, "custom_indicators_at_risk", sum(1 for value in scores if 50 <= value < 75))
    _set_if(meta, values, "custom_critical_indicators", sum(1 for value in scores if value < 50))
    _set_if(meta, values, "custom_indicators_achievement_percentage", round(achievement, 2))
    return values, achievement


def _beneficiary_values(project, meta):
    rows = _rows(
        "Project Beneficiary Plan", project,
        ["name", "status", "docstatus", "actuals_finalized", "actuals_finalized_on",
         "planned_individuals_total", "actual_individuals_total",
         "planned_households_total", "actual_households_total",
         "planned_pwd_total", "actual_pwd_total", "modified"],
        order_by="actuals_finalized desc, actuals_finalized_on desc, modified desc",
    )
    rows = [row for row in rows if _active(row)]
    authoritative = next((row for row in rows if int(row.get("actuals_finalized") or 0)), rows[0] if rows else None)
    values = {}
    if not authoritative:
        defaults = {
            "custom_beneficiary_plan": "", "custom_beneficiary_plan_status": "",
            "custom_beneficiary_actuals_finalized": 0, "custom_planned_individuals": 0,
            "custom_actual_individuals": 0, "custom_planned_households": 0,
            "custom_actual_households": 0, "custom_planned_pwd": 0,
            "custom_actual_pwd": 0, "custom_individual_achievement": 0,
            "custom_household_achievement": 0, "custom_last_beneficiary_update": None,
        }
        for fieldname, value in defaults.items():
            _set_if(meta, values, fieldname, value)
        return values
    planned_i = flt(authoritative.get("planned_individuals_total"))
    actual_i = flt(authoritative.get("actual_individuals_total"))
    planned_h = flt(authoritative.get("planned_households_total"))
    actual_h = flt(authoritative.get("actual_households_total"))
    pairs = {
        "custom_beneficiary_plan": authoritative.name,
        "custom_beneficiary_plan_status": authoritative.get("status") or "",
        "custom_beneficiary_actuals_finalized": int(authoritative.get("actuals_finalized") or 0),
        "custom_planned_individuals": planned_i,
        "custom_actual_individuals": actual_i,
        "custom_planned_households": planned_h,
        "custom_actual_households": actual_h,
        "custom_planned_pwd": flt(authoritative.get("planned_pwd_total")),
        "custom_actual_pwd": flt(authoritative.get("actual_pwd_total")),
        "custom_individual_achievement": actual_i / planned_i * 100 if planned_i else 0,
        "custom_household_achievement": actual_h / planned_h * 100 if planned_h else 0,
        "custom_last_beneficiary_update": authoritative.get("modified"),
    }
    for fieldname, value in pairs.items():
        _set_if(meta, values, fieldname, value)
    return values


def _budget_values(project, meta):
    rows = _rows(
        "Budget Line", project,
        ["name", "parent_budget_line", "status", "line_cost", "is_group"],
    )
    roots = [row for row in rows if not row.get("parent_budget_line")]
    approved_roots = [row for row in roots if _status(row) == "Approved"]
    root = approved_roots[0] if approved_roots else (roots[0] if roots else None)
    values = {}
    # Budget Line remains the source of truth. No Project funding or sector
    # allocation field is overwritten because those fields have distinct meanings.
    return values


def _health(project, activity_progress, indicator_achievement):
    risks = _rows("Project Risk", project, ["status", "risk_level"])
    critical_risks = sum(1 for row in risks if _active(row) and row.get("risk_level") == "Critical")
    deliverables = _rows("Project Compliance Deliverable", project, ["status", "monitoring_status"])
    overdue = sum(1 for row in deliverables if _active(row) and row.get("monitoring_status") in {"Overdue", "Critical"})
    changes = _rows("Project Change Request", project, ["status"])
    pending_changes = sum(1 for row in changes if _status(row) not in CLOSED)
    if critical_risks or overdue:
        return "Critical"
    if pending_changes or activity_progress < 70 or (indicator_achievement and indicator_achievement < 70):
        return "At Risk"
    return "On Track"


def expected_project_values(project, scopes=None, rebuild_activity_entries=True):
    if not project or not frappe.db.exists("Project", project):
        return {}
    selected = set(scopes or ALL_SCOPES)
    meta = frappe.get_meta("Project")
    values = {}
    if "progress_updates" in selected and rebuild_activity_entries:
        _reconcile_activity_entries(project)
    activity_values, activity_progress = _activity_values(project, meta)
    indicator_values, indicator_achievement = _indicator_values(project, meta)
    if selected.intersection({"activities", "progress_updates"}):
        values.update(activity_values)
    if selected.intersection({"indicators", "progress_updates"}):
        values.update(indicator_values)
    latest = _latest_approved_update(project)
    if "progress_updates" in selected:
        _set_if(meta, values, "custom_latest_approved_progress_update", latest.name if latest else "")
        latest_date = (latest.get("period_end_date") or latest.get("update_date")) if latest else None
        _set_if(meta, values, "custom_latest_progress_update_date", latest_date)
    if "beneficiaries" in selected:
        values.update(_beneficiary_values(project, meta))
    if "budget" in selected:
        values.update(_budget_values(project, meta))
    submitted_closure = None
    if _exists("Project Closure"):
        submitted = _rows("Project Closure", project, ["name", "docstatus", "project_closed", "modified"], order_by="modified desc")
        submitted_closure = next((
            row for row in submitted
            if int(row.get("docstatus") or 0) == 1
        ), None)
    if "closure" in selected and submitted_closure:
        if meta.has_field("percent_complete"):
            values["percent_complete"] = 100
        if meta.has_field("status"):
            values["status"] = "Completed"
    elif selected.intersection({"activities", "progress_updates", "closure"}):
        if meta.has_field("percent_complete"):
            values["percent_complete"] = round(activity_progress, 2)
        current_status = frappe.db.get_value("Project", project, "status") if meta.has_field("status") else None
        if current_status == "Completed" and not submitted_closure:
            values["status"] = "Open"
    if "health" in selected or selected.intersection({"activities", "indicators", "risks_issues", "changes", "compliance"}):
        health = _health(project, activity_progress, indicator_achievement)
        _set_if(meta, values, "custom_calculated_project_health", health)
        _set_if(meta, values, "custom_project_health", health)
    return values


def reconcile_project(project, scopes=None, save=True):
    """Idempotently rebuild stored Project summaries from source records."""
    if getattr(frappe.flags, "qorg_project_reconciliation", False):
        return {"project": project, "changed": {}, "expected": {}}
    if not project or not frappe.db.exists("Project", project):
        return {"project": project, "changed": {}, "expected": {}}
    frappe.flags.qorg_project_reconciliation = True
    try:
        expected = expected_project_values(project, scopes=scopes, rebuild_activity_entries=bool(save))
        current = frappe.db.get_value("Project", project, list(expected), as_dict=True) if expected else {}
        changed = {}
        for fieldname, value in expected.items():
            old = current.get(fieldname) if current else None
            if _different(old, value):
                changed[fieldname] = {"old": old, "new": value}
        if save and changed:
            frappe.db.set_value(
                "Project", project,
                {fieldname: row["new"] for fieldname, row in changed.items()},
                update_modified=False,
            )
        return {"project": project, "changed": changed, "expected": expected}
    finally:
        frappe.flags.qorg_project_reconciliation = False


def _different(old, new):
    if isinstance(new, (int, float)):
        return round(flt(old), 6) != round(flt(new), 6)
    return (old or "") != (new or "")


def reconcile_document_projects(doc, method=None):
    """Reconcile current and previous Project links for a cycle document."""
    projects = set()
    current = doc.get("project")
    if current:
        projects.add(current)
    old = None
    if hasattr(doc, "get_doc_before_save"):
        before = doc.get_doc_before_save()
        old = before.get("project") if before else None
    if old:
        projects.add(old)
    for project in projects:
        reconcile_project(project)


def reconcile_deleted_document(doc, method=None):
    project = doc.get("project")
    if project:
        reconcile_project(project)


@frappe.whitelist()
def audit_project(project):
    frappe.get_doc("Project", project).check_permission("read")
    return reconcile_project(project, save=False)


@frappe.whitelist()
def repair_project(project):
    frappe.get_doc("Project", project).check_permission("write")
    return reconcile_project(project, save=True)


@frappe.whitelist()
def audit_all_projects(repair=0):
    if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only System Managers can audit all projects."))
    result = {"checked": 0, "changed_projects": 0, "differences": {}}
    for project in frappe.get_all("Project", pluck="name", limit_page_length=0):
        row = reconcile_project(project, save=bool(int(repair or 0)))
        result["checked"] += 1
        if row["changed"]:
            result["changed_projects"] += 1
            result["differences"][project] = row["changed"]
    return result
