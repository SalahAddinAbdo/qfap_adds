from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def apply_current_employee_signature(doctype, document_name, mapping_key):
    if not frappe.has_permission(doctype, "write", document_name):
        frappe.throw(_("You do not have permission to sign this document."), frappe.PermissionError)
    target = frappe.get_doc(doctype, document_name)
    responsible = target.get("custom_current_responsible_user")
    if responsible and responsible != frappe.session.user and "Workflow Admin" not in frappe.get_roles():
        frappe.throw(_("This document is currently assigned to {0}.").format(responsible))
    config = _get_configuration(doctype, mapping_key)
    signature = _get_signature(frappe.session.user)
    prefix = "custom_" + _safe_key(mapping_key)
    signature_field = config.employee_signature_field or prefix + "_employee_signature"
    designation_field = config.designation_field or prefix + "_designation"
    date_field = config.signature_date_field or prefix + "_signature_date"
    image_field = config.signature_image_field or prefix + "_signature_image"
    existing = target.get(signature_field)
    if existing and not config.allow_signature_replacement:
        return {"already_signed": True, "signed": False}
    target.set(signature_field, signature.name)
    if target.meta.has_field(prefix + "_employee_name"):
        target.set(prefix + "_employee_name", signature.full_name)
    target.set(designation_field, signature.designation)
    target.set(date_field, now_datetime())
    target.set(image_field, signature.signature1)
    target.flags.ignore_validate_update_after_submit = True
    target.save(ignore_permissions=False)
    target.add_comment("Info", _("Signed electronically by {0}").format(signature.full_name))
    return {"signed": True, "already_signed": False, "signature": signature.name}


def _safe_key(value):
    import re
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")[:60]


def _get_configuration(doctype, mapping_key):
    configs = frappe.get_all("Employee Signature Configuration", filters={"document_type": doctype, "enabled": 1}, pluck="name")
    for name in configs:
        doc = frappe.get_doc("Employee Signature Configuration", name)
        for row in doc.signature_mappings or []:
            if row.mapping_key == mapping_key:
                return row
    frappe.throw(_("No active signature configuration was found for this Mapping Key."))


def _get_signature(user):
    name = frappe.db.get_value("Employee Signature", {"user_id": user, "disabled": 0, "is_default": 1}, "name")
    if not name:
        name = frappe.db.get_value("Employee Signature", {"user_id": user, "disabled": 0}, "name")
    if not name:
        frappe.throw(_("No active Employee Signature is configured for the current user."))
    return frappe.get_doc("Employee Signature", name)
