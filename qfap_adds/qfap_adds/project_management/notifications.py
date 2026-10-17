from __future__ import annotations
import frappe
DEFAULTS=(
("Project Risk - Critical","Project Risk","doc.risk_level == 'Critical' and doc.status not in ['Closed','Inactive']","Critical project risk: {{ doc.name }}"),
("Project Risk Review - Overdue","Project Risk","doc.review_monitoring_status in ['Overdue','Critical']","Risk review overdue: {{ doc.name }}"),
("Project Deliverable - Due Soon","Project Compliance Deliverable","doc.monitoring_status == 'Due Soon'","Project deliverable due soon: {{ doc.name }}"),
("Project Deliverable - Overdue","Project Compliance Deliverable","doc.monitoring_status in ['Overdue','Critical']","Overdue project deliverable: {{ doc.name }}"),
("Project Change - Approved Not Implemented","Project Change Request","doc.status == 'Approved' and not doc.change_applied","Approved change pending implementation: {{ doc.name }}"),
("Project Progress Update - Rejected","Project Progress Update","doc.status == 'Rejected'","Project progress update rejected: {{ doc.name }}"),
("Project Closure - Ready","Project Closure","doc.overall_closure_status == 'Ready for Closure' and not doc.project_closed","Project ready for closure: {{ doc.project }}"),
)
def provision_project_notifications():
    for name,doctype,condition,subject in DEFAULTS:
        if frappe.db.exists("Notification",name): continue
        doc=frappe.new_doc("Notification"); doc.name=name; doc.subject=subject; doc.document_type=doctype; doc.event="Value Change"; doc.condition=condition; doc.enabled=0
        if doc.meta.has_field("message"): doc.message=subject
        doc.insert(ignore_permissions=True)
