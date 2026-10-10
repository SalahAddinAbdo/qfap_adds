from __future__ import annotations

import frappe
from frappe import _


def validate_responsible_user(doc, method=None):
    if doc.is_new() or not doc.meta.has_field("custom_current_responsible_user"):
        return
    responsible = doc.get("custom_current_responsible_user")
    if not responsible or responsible == frappe.session.user:
        return
    if "Workflow Admin" in frappe.get_roles(frappe.session.user) or "System Manager" in frappe.get_roles(frappe.session.user):
        return
    if not doc.has_value_changed("custom_current_responsible_user"):
        frappe.throw(_("Only the current responsible user can modify this document."), frappe.PermissionError)
