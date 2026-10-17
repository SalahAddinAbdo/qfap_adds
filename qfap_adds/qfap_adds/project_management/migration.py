from __future__ import annotations

import frappe


PROJECT_CYCLE_DOCTYPES = (
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
    """Adopt matching UI-created DocTypes before standard schema sync.

    The existing database tables and records are preserved. Matching custom
    DocTypes are converted to app-owned standard DocTypes under QFap Adds, and
    the individual JSON files then become the authoritative schema.
    """
    for doctype in PROJECT_CYCLE_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue

        values = frappe.db.get_value(
            "DocType", doctype, ["custom", "module"], as_dict=True
        )
        updates = {}
        if int(values.custom or 0):
            updates["custom"] = 0
        if values.module != "QFap Adds":
            updates["module"] = "QFap Adds"

        if updates:
            frappe.db.set_value(
                "DocType", doctype, updates, update_modified=False
            )

    frappe.clear_cache()
