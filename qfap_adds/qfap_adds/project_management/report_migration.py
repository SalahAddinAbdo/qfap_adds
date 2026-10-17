from __future__ import annotations
import frappe

RENAMES = {
    "Project Progress and Performance": "Project Progress",
    "Project Budget Performance": "Project Budget",
    "Indicator Performance Tracking Table": "Indicator Performance",
    "Project Risk and Issue Management": "Project Risks and Issues",
    "Project Beneficiary Reach and Disaggregation": "Beneficiary Reach",
    "Project Compliance and Deliverables Assurance": "Compliance Assurance",
    "Project Change Request and Amendment Control": "Change Control",
    "Project Closure Readiness and Assurance": "Closure Readiness",
    "Project Data Quality and Cycle Readiness": "Project Data Quality",
}

def cleanup_replaced_project_reports():
    for old, new in RENAMES.items():
        if frappe.db.exists("Report", new) and frappe.db.exists("Report", old):
            frappe.delete_doc("Report", old, ignore_permissions=True, force=True)
    frappe.clear_cache()
