from __future__ import annotations
import frappe
from qfap_adds.qfap_adds.project_management.services.project_reconciliation import reconcile_project
from frappe.utils import date_diff, nowdate

def run_daily_project_monitoring():
    _monitor("Project Compliance Deliverable","due_date",("Approved","Cancelled"))
    _monitor("Project Risk","next_review_date",("Closed","Inactive"),"review_monitoring_status","review_monitoring_days","review_monitoring_message")

def _monitor(doctype,date_field,closed,status_field="monitoring_status",days_field="monitoring_days",message_field="monitoring_message"):
    if not frappe.db.exists("DocType",doctype): return
    meta=frappe.get_meta(doctype)
    if not all(meta.has_field(f) for f in (date_field,status_field,days_field,message_field)): return
    for row in frappe.get_all(doctype,filters={date_field:["is","set"],"status":["not in",list(closed)]},fields=["name",date_field,status_field]):
        days=date_diff(row.get(date_field),nowdate()); status="Overdue" if days<0 else ("Due Soon" if days<=7 else "Not Due"); message=f"Due in {days} day(s)" if days>=0 else f"Overdue by {abs(days)} day(s)"
        if row.get(status_field)!=status: frappe.db.set_value(doctype,row.name,{status_field:status,days_field:days,message_field:message},update_modified=False)


def reconcile_monitored_projects():
    projects = set()
    for doctype in ("Project Compliance Deliverable", "Project Progress Update", "Project Risk"):
        if frappe.db.exists("DocType", doctype):
            projects.update(frappe.get_all(doctype, pluck="project", limit_page_length=0))
    for project in projects:
        if project:
            reconcile_project(project)
