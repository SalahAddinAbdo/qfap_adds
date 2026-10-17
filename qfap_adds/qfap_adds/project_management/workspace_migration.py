from __future__ import annotations

import frappe


OLD_WORKSPACES = ("Project Cycle Management",)
NEW_WORKSPACE = "QFap Management Hub"


def prepare_qfap_management_hub():
    """Remove obsolete app-owned workspace records before standard sync.

    The new workspace is synchronized from
    qfap_adds/qfap_adds/workspace/qfap_management_hub.
    """
    for old_name in OLD_WORKSPACES:
        if old_name != NEW_WORKSPACE and frappe.db.exists("Workspace", old_name):
            frappe.delete_doc(
                "Workspace",
                old_name,
                ignore_permissions=True,
                force=True,
            )
    frappe.clear_cache()
