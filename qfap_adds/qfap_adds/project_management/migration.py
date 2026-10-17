from __future__ import annotations

import frappe

STANDARD_PROJECT_DOCTYPES = (
    "Project Core Team Assignment",
    "Project Funding Source",
    "Project Sector",
    "Project Geographic Location",
    "Project Implementation Partner",
    "Project Report Schedules",
    "Project Result",
    "Project Workplan Activity",
)

STANDARDIZED_FIELDS = {
    "Project Workplan Activity": ("linked_workplan_task",),
}


def prepare_standard_project_doctypes():
    """Convert UI-created models before Frappe synchronizes standard JSON."""
    for doctype in STANDARD_PROJECT_DOCTYPES:
        if frappe.db.exists("DocType", doctype):
            frappe.db.set_value(
                "DocType", doctype,
                {"custom": 0, "module": "QFap Adds"},
                update_modified=False,
            )

    for doctype, fieldnames in STANDARDIZED_FIELDS.items():
        for fieldname in fieldnames:
            name = frappe.db.get_value(
                "Custom Field", {"dt": doctype, "fieldname": fieldname}, "name"
            )
            if name:
                # Remove conflicting metadata only; the SQL column and values remain.
                frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

    frappe.clear_cache()
