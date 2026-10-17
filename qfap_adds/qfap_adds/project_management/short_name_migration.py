from __future__ import annotations

import frappe
from frappe import _


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
    """Rename app-owned DocTypes safely before schema synchronization.

    Production sites normally run with developer mode disabled. Frappe blocks
    renaming standard DocTypes in that mode. These DocTypes originated as UI
    custom DocTypes and are being adopted by the app, so each existing legacy
    DocType is temporarily marked custom only for the rename operation, then
    restored immediately as a standard DocType owned by QFap Adds.
    """
    for old_name, new_name in RENAMES.items():
        old_exists = bool(frappe.db.exists("DocType", old_name))
        new_exists = bool(frappe.db.exists("DocType", new_name))

        if not old_exists:
            continue

        if new_exists:
            frappe.throw(
                _(
                    "Cannot rename DocType {0} to {1} because both DocTypes "
                    "already exist. No automatic merge was attempted."
                ).format(frappe.bold(old_name), frappe.bold(new_name))
            )

        original = frappe.db.get_value(
            "DocType", old_name, ["custom", "module"], as_dict=True
        ) or frappe._dict()

        # Bypass the developer-mode guard only for this controlled rename.
        frappe.db.set_value(
            "DocType", old_name, "custom", 1, update_modified=False
        )
        frappe.clear_cache(doctype=old_name)

        try:
            frappe.rename_doc("DocType", old_name, new_name, force=True)
        except Exception:
            # Keep metadata consistent if Frappe catches the exception without
            # rolling back immediately. The migrate transaction will still fail.
            if frappe.db.exists("DocType", old_name):
                frappe.db.set_value(
                    "DocType",
                    old_name,
                    {
                        "custom": int(original.custom or 0),
                        "module": original.module or "QFap Adds",
                    },
                    update_modified=False,
                )
            raise

        frappe.db.set_value(
            "DocType",
            new_name,
            {"custom": 0, "module": "QFap Adds"},
            update_modified=False,
        )
        frappe.clear_cache(doctype=new_name)

    frappe.clear_cache()
