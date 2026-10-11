from __future__ import annotations

import frappe


WORKFLOW_ADMIN_ROLE = "Workflow Admin"


def after_install():
    ensure_workflow_admin_role()
    provision_active_workflows()


def after_migrate():
    ensure_workflow_admin_role()
    provision_active_workflows()


def ensure_workflow_admin_role():
    """Create the Workflow Admin role only when it does not already exist."""
    if frappe.db.exists("Role", WORKFLOW_ADMIN_ROLE):
        return

    role = frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": WORKFLOW_ADMIN_ROLE,
            "desk_access": 1,
            "disabled": 0,
        }
    )
    role.insert(ignore_permissions=True)


def provision_active_workflows():
    if not frappe.db.exists("DocType", "Workflow"):
        return

    from qfap_adds.qfap_adds.workflow.provisioning import (
        ensure_current_responsible_user,
    )

    workflow_names = frappe.get_all(
        "Workflow",
        filters={"is_active": 1},
        pluck="name",
    )

    for workflow_name in workflow_names:
        workflow = frappe.get_doc("Workflow", workflow_name)
        ensure_current_responsible_user(workflow)
