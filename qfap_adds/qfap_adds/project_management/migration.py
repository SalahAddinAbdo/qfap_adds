from __future__ import annotations

import frappe


PROJECT_MANAGEMENT_DOCTYPES = (
    "Project Core Team Assignment",
    "Project Funding Source",
    "Project Sector",
    "Project Geographic Location",
    "Project Implementation Partner",
    "Project Report Schedules",
    "Project Result",
    "Project Workplan Activity",
)


def prepare_standard_project_doctypes() -> None:
    """Adopt matching UI-created DocTypes before Frappe syncs app files.

    Existing tables and records are preserved. The application files become
    the authoritative schema after the DocType is marked as standard and moved
    to the Project Management module.
    """
    if not frappe.db.exists("Module Def", "Project Management"):
        module = frappe.new_doc("Module Def")
        module.module_name = "Project Management"
        module.app_name = "qfap_adds"
        module.insert(ignore_permissions=True)

    for doctype in PROJECT_MANAGEMENT_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue

        values = frappe.db.get_value(
            "DocType", doctype, ["custom", "module"], as_dict=True
        )
        updates = {}
        if int(values.custom or 0):
            updates["custom"] = 0
        if values.module != "Project Management":
            updates["module"] = "Project Management"

        if updates:
            frappe.db.set_value(
                "DocType", doctype, updates, update_modified=False
            )

    frappe.clear_cache()
