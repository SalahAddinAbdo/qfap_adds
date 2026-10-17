from __future__ import annotations
import frappe

RENAMES = {
    'Project Deliverable Attachment Requirement': 'Deliverable Requirement',
    'Project Closure Outstanding Action': 'Closure Outstanding Action',
    'Project Closure Checklist Item': 'Closure Checklist Item',
    'Project Change Affected Item': 'Change Affected Item',
    'Project Beneficiary Breakdown': 'Beneficiary Breakdown',
    'Project Implementation Partner': 'Project Partner',
    'Project Workflow Role Mapping': 'Workflow Role Mapping',
 }

def prepare_short_project_doctype_names():
    for old, new in RENAMES.items():
        if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
            frappe.rename_doc("DocType", old, new, force=True, ignore_permissions=True)
    frappe.clear_cache()
