from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DEFAULTS = {
    "create_workplan_tasks_automatically": 1,
    "update_linked_workplan_tasks": 1,
    "show_task_execution_metrics_in_activities": 1,
    "warn_about_open_tasks_during_closure": 1,
    "block_closure_when_open_tasks_exist": 0,
    "default_workplan_task_type": "Workplan",
    "enable_daily_project_monitoring": 1,
}

SETTINGS_FIELDS = [
    {"fieldname":"custom_project_cycle_progress_section","label":"Project Progress Policy","fieldtype":"Section Break","insert_after":"custom_project_cycle_defaults_initialized"},
    {"fieldname":"update_project_progress_automatically","label":"Update Project Progress Automatically","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_progress_section"},
    {"fieldname":"custom_project_cycle_progress_col","fieldtype":"Column Break","insert_after":"update_project_progress_automatically"},
    {"fieldname":"maximum_displayed_achievement","label":"Maximum Displayed Achievement","fieldtype":"Percent","default":"100","insert_after":"custom_project_cycle_progress_col"},
    {"fieldname":"allow_progress_above_100","label":"Allow Progress Above 100%","fieldtype":"Check","default":"0","insert_after":"maximum_displayed_achievement"},
    {"fieldname":"require_evidence_for_progress_updates","label":"Require Evidence for Progress Updates","fieldtype":"Check","default":"0","insert_after":"allow_progress_above_100"},
    {"fieldname":"custom_project_cycle_progress_col_2","fieldtype":"Column Break","insert_after":"require_evidence_for_progress_updates"},
    {"fieldname":"require_verified_indicator_results","label":"Require Verified Indicator Results","fieldtype":"Check","default":"0","insert_after":"custom_project_cycle_progress_col_2"},
    {"fieldname":"lock_approved_progress_updates","label":"Lock Approved Progress Updates","fieldtype":"Check","default":"1","insert_after":"require_verified_indicator_results"},
    {"fieldname":"allow_progress_update_correction","label":"Allow Progress Update Correction","fieldtype":"Check","default":"1","insert_after":"lock_approved_progress_updates"},
    {"fieldname":"custom_project_cycle_health_section","label":"Project Health Policy","fieldtype":"Section Break","insert_after":"allow_progress_update_correction"},
    {"fieldname":"enable_automatic_project_health","label":"Enable Automatic Project Health","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_health_section"},
    {"fieldname":"custom_project_cycle_health_col","fieldtype":"Column Break","insert_after":"enable_automatic_project_health"},
    {"fieldname":"on_track_threshold","label":"On Track Threshold","fieldtype":"Percent","default":"80","insert_after":"custom_project_cycle_health_col"},
    {"fieldname":"at_risk_threshold","label":"At Risk Threshold","fieldtype":"Percent","default":"60","insert_after":"on_track_threshold"},
    {"fieldname":"custom_project_health_weights_section","label":"Project Health Weights","fieldtype":"Section Break","insert_after":"at_risk_threshold"},
    {"fieldname":"project_health_weights","label":"Project Health Weights","fieldtype":"Table","options":"Project Health Weight","insert_after":"custom_project_health_weights_section"},
    {"fieldname":"custom_project_cycle_risk_section","label":"Risk and Issue Policy","fieldtype":"Section Break","insert_after":"project_health_weights"},
    {"fieldname":"low_risk_maximum_score","label":"Low Risk Maximum Score","fieldtype":"Int","default":"4","insert_after":"custom_project_cycle_risk_section"},
    {"fieldname":"moderate_risk_maximum_score","label":"Moderate Risk Maximum Score","fieldtype":"Int","default":"9","insert_after":"low_risk_maximum_score"},
    {"fieldname":"high_risk_maximum_score","label":"High Risk Maximum Score","fieldtype":"Int","default":"16","insert_after":"moderate_risk_maximum_score"},
    {"fieldname":"custom_project_cycle_risk_col","fieldtype":"Column Break","insert_after":"high_risk_maximum_score"},
    {"fieldname":"auto_create_issue_when_risk_occurs","label":"Auto Create Issue When Risk Occurs","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_risk_col"},
    {"fieldname":"auto_close_risk_when_issue_closes","label":"Auto Close Risk When Issue Closes","fieldtype":"Check","default":"0","insert_after":"auto_create_issue_when_risk_occurs"},
    {"fieldname":"critical_risk_escalation_enabled","label":"Critical Risk Escalation Enabled","fieldtype":"Check","default":"1","insert_after":"auto_close_risk_when_issue_closes"},
    {"fieldname":"custom_project_cycle_risk_col_2","fieldtype":"Column Break","insert_after":"critical_risk_escalation_enabled"},
    {"fieldname":"risk_review_due_soon_days","label":"Risk Review Due Soon Days","fieldtype":"Int","default":"7","insert_after":"custom_project_cycle_risk_col_2"},
    {"fieldname":"issue_resolution_due_soon_days","label":"Issue Resolution Due Soon Days","fieldtype":"Int","default":"7","insert_after":"risk_review_due_soon_days"},
    {"fieldname":"custom_project_cycle_compliance_section","label":"Compliance Policy","fieldtype":"Section Break","insert_after":"issue_resolution_due_soon_days"},
    {"fieldname":"deliverable_due_soon_days","label":"Deliverable Due Soon Days","fieldtype":"Int","default":"7","insert_after":"custom_project_cycle_compliance_section"},
    {"fieldname":"custom_project_cycle_compliance_col","fieldtype":"Column Break","insert_after":"deliverable_due_soon_days"},
    {"fieldname":"require_mandatory_attachments_before_submission","label":"Require Mandatory Attachments Before Submission","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_compliance_col"},
    {"fieldname":"require_mandatory_attachments_before_approval","label":"Require Mandatory Attachments Before Approval","fieldtype":"Check","default":"1","insert_after":"require_mandatory_attachments_before_submission"},
    {"fieldname":"allow_deliverable_resubmission","label":"Allow Deliverable Resubmission","fieldtype":"Check","default":"1","insert_after":"require_mandatory_attachments_before_approval"},
    {"fieldname":"auto_escalate_overdue_deliverables","label":"Auto Escalate Overdue Deliverables","fieldtype":"Check","default":"1","insert_after":"allow_deliverable_resubmission"},
    {"fieldname":"custom_project_cycle_change_section","label":"Change Control Policy","fieldtype":"Section Break","insert_after":"auto_escalate_overdue_deliverables"},
    {"fieldname":"enable_automatic_change_application","label":"Enable Automatic Change Application","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_change_section"},
    {"fieldname":"custom_project_cycle_change_col","fieldtype":"Column Break","insert_after":"enable_automatic_change_application"},
    {"fieldname":"require_donor_approval_for_budget_changes","label":"Require Donor Approval for Budget Changes","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_change_col"},
    {"fieldname":"budget_change_approval_threshold","label":"Budget Change Approval Threshold (%)","fieldtype":"Percent","default":"10","insert_after":"require_donor_approval_for_budget_changes"},
    {"fieldname":"schedule_change_approval_threshold","label":"Schedule Change Approval Threshold (Days)","fieldtype":"Int","default":"30","insert_after":"budget_change_approval_threshold"},
    {"fieldname":"custom_project_change_fields_section","label":"Allowed Change Fields","fieldtype":"Section Break","insert_after":"schedule_change_approval_threshold"},
    {"fieldname":"project_change_allowed_fields","label":"Allowed Change Fields","fieldtype":"Table","options":"Project Change Allowed Field","insert_after":"custom_project_change_fields_section"},
    {"fieldname":"custom_project_cycle_closure_section","label":"Closure and Readiness Policy","fieldtype":"Section Break","insert_after":"project_change_allowed_fields"},
    {"fieldname":"require_final_technical_report","label":"Require Final Technical Report","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_closure_section"},
    {"fieldname":"require_final_financial_report","label":"Require Final Financial Report","fieldtype":"Check","default":"1","insert_after":"require_final_technical_report"},
    {"fieldname":"require_archive_reference","label":"Require Archive Reference","fieldtype":"Check","default":"1","insert_after":"require_final_financial_report"},
    {"fieldname":"custom_project_cycle_closure_col","fieldtype":"Column Break","insert_after":"require_archive_reference"},
    {"fieldname":"require_final_progress_update","label":"Require Final Progress Update","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_closure_col"},
    {"fieldname":"require_beneficiary_finalization","label":"Require Beneficiary Finalization","fieldtype":"Check","default":"1","insert_after":"require_final_progress_update"},
    {"fieldname":"generate_default_closure_checklist","label":"Generate Default Closure Checklist","fieldtype":"Check","default":"1","insert_after":"require_beneficiary_finalization"},
    {"fieldname":"custom_project_readiness_gates_section","label":"Project Readiness Gates","fieldtype":"Section Break","insert_after":"generate_default_closure_checklist"},
    {"fieldname":"project_readiness_gates","label":"Project Readiness Gates","fieldtype":"Table","options":"Project Readiness Gate","insert_after":"custom_project_readiness_gates_section"},
    {"fieldname":"custom_project_cycle_workflow_section","label":"Workflow and Notification Policy","fieldtype":"Section Break","insert_after":"project_readiness_gates"},
    {"fieldname":"custom_project_workflow_mapping_section","label":"Workflow Role Mappings","fieldtype":"Section Break","insert_after":"custom_project_cycle_workflow_section"},
    {"fieldname":"project_workflow_role_mappings","label":"Workflow Role Mappings","fieldtype":"Table","options":"Workflow Role Mapping","insert_after":"custom_project_workflow_mapping_section"},
    {"fieldname":"custom_project_notification_rules_section","label":"Project Notification Rules","fieldtype":"Section Break","insert_after":"project_workflow_role_mappings"},
    {"fieldname":"project_notification_rules","label":"Project Notification Rules","fieldtype":"Table","options":"Project Notification Rule","insert_after":"custom_project_notification_rules_section"},

    {"fieldname":"custom_project_cycle_integration_section","label":"Project Cycle Integration","fieldtype":"Section Break","insert_after":"fetch_timesheet_in_sales_invoice"},
    {"fieldname":"create_workplan_tasks_automatically","label":"Create Workplan Tasks Automatically","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_integration_section","description":"Create one operational parent Task for each Project Workplan Activity."},
    {"fieldname":"update_linked_workplan_tasks","label":"Update Linked Workplan Tasks","fieldtype":"Check","default":"1","insert_after":"create_workplan_tasks_automatically"},
    {"fieldname":"default_workplan_task_type","label":"Default Workplan Task Type","fieldtype":"Link","options":"Task Type","default":"Workplan","insert_after":"update_linked_workplan_tasks","description":"Task Type assigned automatically to parent Tasks created from Project Workplan Activities."},
    {"fieldname":"show_task_execution_metrics_in_activities","label":"Show Task Execution Metrics in Activities","fieldtype":"Check","default":"1","insert_after":"default_workplan_task_type"},
    {"fieldname":"custom_project_cycle_integration_column","fieldtype":"Column Break","insert_after":"show_task_execution_metrics_in_activities"},
    {"fieldname":"warn_about_open_tasks_during_closure","label":"Warn About Open Tasks During Closure","fieldtype":"Check","default":"1","insert_after":"custom_project_cycle_integration_column","description":"Informational only. Tasks do not determine Project completion."},
    {"fieldname":"block_closure_when_open_tasks_exist","label":"Block Closure When Open Tasks Exist","fieldtype":"Check","default":"0","insert_after":"warn_about_open_tasks_during_closure","description":"Optional exception. Disabled by default because Tasks are independent from Project completion."},
    {"fieldname":"enable_daily_project_monitoring","label":"Enable Daily Project Monitoring","fieldtype":"Check","default":"1","insert_after":"block_closure_when_open_tasks_exist"},
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


def _ensure_project_issue_custom_fields():
    path = Path(__file__).with_name("project_issue_custom_fields.json")
    definitions = json.loads(path.read_text(encoding="utf-8"))
    create_custom_fields(definitions, update=True)


def _ensure_configurable_policy_defaults():
    settings = frappe.get_single("Projects Settings")
    defaults = {
        "project_health_weights": [
            ("Activity Progress",30),("Indicator Performance",25),("Schedule Variance",15),("Financial Performance",10),("Risk Exposure",10),("Compliance",10)
        ],
        "project_readiness_gates": [
            ("risks","No open High/Critical Risks",1),("changes","No pending Change Requests",1),("compliance","No overdue Deliverables",1),("beneficiaries","Beneficiary actuals finalized",1),("tasks","No open operational Tasks",0)
        ],
        "project_change_allowed_fields": [
            ("Project","expected_start_date"),("Project","expected_end_date"),("Project Result","result_statement"),("Project Result","weight"),("Project Indicator","life_of_project_target"),("Indicator Target Plan","target_value"),("Project Workplan Activity","planned_start_date"),("Project Workplan Activity","planned_end_date"),("Project Workplan Activity","planned_quantity"),("Project Compliance Deliverable","due_date")
        ],
        "project_workflow_role_mappings": [
            ("Project Progress Update","System Manager","System Manager","System Manager"),("Project Change Request","System Manager","System Manager","System Manager"),("Project Compliance Deliverable","System Manager","System Manager","System Manager"),("Project Beneficiary Plan","System Manager","System Manager","System Manager"),("Project Closure","System Manager","System Manager","System Manager")
        ],
        "project_notification_rules": [
            ("critical_risk",1,0),("risk_review_overdue",1,7),("deliverable_due_soon",1,7),("deliverable_overdue",1,0),("change_pending_implementation",1,7),("progress_update_overdue",1,7),("closure_action_overdue",1,7)
        ],
    }
    if settings.meta.has_field("project_health_weights") and not settings.project_health_weights:
        for metric, weight in defaults["project_health_weights"]: settings.append("project_health_weights", {"metric":metric,"weight":weight,"enabled":1})
    if settings.meta.has_field("project_readiness_gates") and not settings.project_readiness_gates:
        for key, label, blocking in defaults["project_readiness_gates"]: settings.append("project_readiness_gates", {"gate_key":key,"gate_label":label,"enabled":1,"blocking":blocking})
    if settings.meta.has_field("project_change_allowed_fields") and not settings.project_change_allowed_fields:
        for dt, field in defaults["project_change_allowed_fields"]: settings.append("project_change_allowed_fields", {"target_doctype":dt,"field_name":field,"enabled":1})
    if settings.meta.has_field("project_workflow_role_mappings") and not settings.project_workflow_role_mappings:
        for dt, owner, reviewer, approver in defaults["project_workflow_role_mappings"]: settings.append("project_workflow_role_mappings", {"process_doctype":dt,"enabled":1,"draft_owner_role":owner,"reviewer_role":reviewer,"approver_role":approver})
    if settings.meta.has_field("project_notification_rules") and not settings.project_notification_rules:
        for key, enabled, days in defaults["project_notification_rules"]: settings.append("project_notification_rules", {"notification_key":key,"enabled":enabled,"due_soon_days":days})
    settings.save(ignore_permissions=True)

def provision_project_management():
    _ensure_workplan_task_type()
    _ensure_project_issue_custom_fields()
    for old in ("project_cycle_integration_section","project_cycle_integration_column"):
        name=f"Projects Settings-{old}"
        if frappe.db.exists("Custom Field",name): frappe.delete_doc("Custom Field",name,ignore_permissions=True,force=True)
    create_custom_fields({"Projects Settings":SETTINGS_FIELDS},update=True)
    _ensure_configurable_policy_defaults()
    settings=frappe.get_single("Projects Settings")
    if not int(settings.get("custom_project_cycle_defaults_initialized") or 0):
        for name,value in DEFAULTS.items(): settings.set(name,value)
        settings.custom_project_cycle_defaults_initialized=1
        settings.save(ignore_permissions=True)
    frappe.clear_cache(doctype="Projects Settings")
