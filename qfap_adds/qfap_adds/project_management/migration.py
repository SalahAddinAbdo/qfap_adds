from __future__ import annotations
import frappe
PROJECT_CYCLE_DOCTYPES = (
    'Project Notification Rule',
    'Project Workflow Role Mapping',
    'Project Change Allowed Field',
    'Project Readiness Gate',
    'Project Health Weight','Project Beneficiary Plan', 'Project Beneficiary Breakdown', 'Project Closure', 'Project Closure Outstanding Action', 'Project Closure Checklist Item', 'Project Change Request', 'Project Result', 'Project Indicator', 'Indicator Target Plan', 'Project Workplan Activity', 'Project Progress Update', 'Project Risk', 'Project Compliance Deliverable', 'Project Deliverable Attachment Requirement', 'Project Core Team Assignment', 'Project Change Affected Item', 'Indicator Result Entry', 'Activity Progress Entry', 'Project Geographic Location', 'Project Sector', 'Project Implementation Partner', 'Project Funding Source', 'Project Report Schedules')
def prepare_standard_project_doctypes():
    for doctype in PROJECT_CYCLE_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        values = frappe.db.get_value("DocType", doctype, ["custom", "module"], as_dict=True)
        updates = {}
        if int(values.custom or 0):
            updates["custom"] = 0
        if values.module != "QFap Adds":
            updates["module"] = "QFap Adds"
        if updates:
            frappe.db.set_value("DocType", doctype, updates, update_modified=False)
    frappe.clear_cache()
