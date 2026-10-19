from __future__ import annotations
import frappe
from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_project
from frappe import _
from frappe.utils import date_diff, nowdate
from qfap_adds.qfap_adds.project_management.api import validate_project_team_employee

def validate_issue(doc, method=None):
    project = doc.get("project") or doc.get("custom_project")
    if not project:
        return
    owner = doc.get("custom_issue_owner") or doc.get("custom_responsible_employee")
    if owner:
        department = validate_project_team_employee(project, owner, "Issue Owner")
        if doc.meta.has_field("custom_responsible_department"):
            doc.custom_responsible_department = department
    due_date = doc.get("resolution_by") or doc.get("custom_target_resolution_date")
    if due_date and doc.status not in ("Resolved", "Closed"):
        days = date_diff(due_date, nowdate())
        if doc.meta.has_field("custom_resolution_monitoring_days"): doc.custom_resolution_monitoring_days = days
        if doc.meta.has_field("custom_resolution_monitoring_status"): doc.custom_resolution_monitoring_status = "Overdue" if days < 0 else ("Due Soon" if days <= 7 else "Not Due")
        if doc.meta.has_field("custom_resolution_monitoring_message"): doc.custom_resolution_monitoring_message = f"Due in {days} day(s)" if days >= 0 else f"Overdue by {abs(days)} day(s)"

def update_linked_risk(doc, method=None):
    risk = doc.get("custom_project_risk")
    if not risk or not frappe.db.exists("Project Risk", risk):
        return
    if doc.status in ("Resolved", "Closed"):
        frappe.db.set_value("Project Risk", risk, {"status": "Closed", "closure_date": nowdate()}, update_modified=False)
        project = frappe.db.get_value("Project Risk", risk, "project")
        if project:
            reconcile_project(project)
