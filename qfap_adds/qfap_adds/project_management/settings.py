from __future__ import annotations
import frappe
from frappe.utils import cint, flt

DEFAULTS = {
    "create_workplan_tasks_automatically": 1,
    "update_linked_workplan_tasks": 1,
    "show_task_execution_metrics_in_activities": 1,
    "warn_about_open_tasks_during_closure": 1,
    "block_closure_when_open_tasks_exist": 0,
    "default_workplan_task_type": "Workplan",
    "enable_daily_project_monitoring": 1,
    "update_project_progress_automatically": 1,
    "maximum_displayed_achievement": 100,
    "allow_progress_above_100": 0,
    "require_evidence_for_progress_updates": 0,
    "require_verified_indicator_results": 0,
    "lock_approved_progress_updates": 1,
    "allow_progress_update_correction": 1,
    "enable_automatic_project_health": 1,
    "on_track_threshold": 80,
    "at_risk_threshold": 60,
    "low_risk_maximum_score": 4,
    "moderate_risk_maximum_score": 9,
    "high_risk_maximum_score": 16,
    "auto_create_issue_when_risk_occurs": 1,
    "auto_close_risk_when_issue_closes": 0,
    "critical_risk_escalation_enabled": 1,
    "risk_review_due_soon_days": 7,
    "issue_resolution_due_soon_days": 7,
    "deliverable_due_soon_days": 7,
    "require_mandatory_attachments_before_submission": 1,
    "require_mandatory_attachments_before_approval": 1,
    "allow_deliverable_resubmission": 1,
    "auto_escalate_overdue_deliverables": 1,
    "enable_automatic_change_application": 1,
    "require_donor_approval_for_budget_changes": 1,
    "budget_change_approval_threshold": 10,
    "schedule_change_approval_threshold": 30,
    "require_final_technical_report": 1,
    "require_final_financial_report": 1,
    "require_archive_reference": 1,
    "require_final_progress_update": 1,
    "require_beneficiary_finalization": 1,
    "generate_default_closure_checklist": 1,
}
CHECK_FIELDS={key for key,value in DEFAULTS.items() if isinstance(value,int) and value in (0,1)}

def get_project_cycle_settings():
    values=frappe._dict(DEFAULTS.copy())
    if not frappe.db.exists("DocType","Projects Settings"): return values
    meta=frappe.get_meta("Projects Settings")
    scalar=[name for name in DEFAULTS if meta.has_field(name)]
    stored=frappe.db.get_value("Projects Settings","Projects Settings",scalar,as_dict=True) or {}
    for name in scalar:
        value=stored.get(name)
        values[name]=cint(value) if name in CHECK_FIELDS else (value if value not in (None,"") else DEFAULTS[name])
    doc=frappe.get_cached_doc("Projects Settings")
    for field in ("project_health_weights","project_readiness_gates","project_change_allowed_fields","project_workflow_role_mappings","project_notification_rules"):
        values[field]=[frappe._dict(row.as_dict()) for row in (doc.get(field) or [])] if meta.has_field(field) else []
    return values

def enabled_rows(field):
    return [row for row in get_project_cycle_settings().get(field,[]) if cint(row.get("enabled"))]
