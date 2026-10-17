from __future__ import annotations

import frappe


RENAMES = {
    "Project Deliverable Attachment Requirement": "Deliverable Requirement",
    "Project Closure Outstanding Action": "Closure Outstanding Action",
    "Project Closure Checklist Item": "Closure Checklist Item",
    "Project Change Affected Item": "Change Affected Item",
    "Project Beneficiary Breakdown": "Beneficiary Breakdown",
    "Project Implementation Partner": "Project Partner",
    "Project Workflow Role Mapping": "Workflow Role Mapping",
}


def prepare_short_project_doctype_names():
    """Rename legacy project-cycle DocTypes before schema synchronization.

    This function is idempotent:
    - It renames only when the old DocType exists and the new one does not.
    - It skips completed renames on later migrate runs.
    - It stops with a clear error if both names exist, so data is never merged
      or discarded automatically.
    """
    for old_name, new_name in RENAMES.items():
        old_exists = bool(frappe.db.exists("DocType", old_name))
        new_exists = bool(frappe.db.exists("DocType", new_name))

        if not old_exists:
            continue

        if new_exists:
            frappe.throw(
                "Cannot rename DocType {0} to {1} because both DocTypes exist. "
                "Resolve the duplicate definitions before running migrate again.".format(
                    frappe.bold(old_name), frappe.bold(new_name)
                )
            )

        # Frappe 16's frappe.rename_doc wrapper does not accept
        # ignore_permissions. Migration runs with administrator privileges.
        frappe.rename_doc("DocType", old_name, new_name, force=True)

    frappe.clear_cache()
