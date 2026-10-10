from __future__ import annotations

import frappe


def after_install():
    provision_active_workflows()


def after_migrate():
    provision_active_workflows()


def provision_active_workflows():
    if not frappe.db.exists("DocType", "Workflow"):
        return
    from qfap_adds.qfap_adds.workflow.provisioning import ensure_current_responsible_user
    for name in frappe.get_all("Workflow", filters={"is_active": 1}, pluck="name"):
        ensure_current_responsible_user(frappe.get_doc("Workflow", name))
