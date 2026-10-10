from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today


@frappe.whitelist()
def apply_current_employee_signature(doctype, document_name, mapping_key):
    if not frappe.has_permission(doctype, "write", document_name):
        frappe.throw(_("You do not have permission to sign this document."), frappe.PermissionError)
    target = frappe.get_doc(doctype, document_name)
    responsible = target.get("custom_current_responsible_user")
    roles = set(frappe.get_roles(frappe.session.user))
    if responsible and responsible != frappe.session.user and not {"Workflow Admin", "System Manager"}.intersection(roles):
        frappe.throw(_("This document is currently assigned to {0}.").format(responsible))

    config, mapping = _get_mapping(doctype, mapping_key)
    if mapping.signature_role not in roles and frappe.session.user != "Administrator":
        frappe.throw(_("The current user does not have the required signature role: {0}").format(mapping.signature_role), frappe.PermissionError)
    signature = _get_signature(frappe.session.user)
    fields = _mapping_fields(mapping)
    _validate_target_fields(target, fields)

    existing = target.get(fields["signature"])
    if existing and not mapping.allow_signature_replacement:
        return {"already_signed": True, "signed": False}

    target.set(fields["signature"], signature.name)
    target.set(fields["employee_name"], signature.full_name)
    target.set(fields["designation"], signature.designation)
    target.set(fields["date"], today())
    target.set(fields["image"], signature.signature1)
    target.flags.ignore_validate_update_after_submit = True
    target.save(ignore_permissions=False)
    target.add_comment("Info", _("Signed electronically by {0} as {1}").format(signature.full_name, mapping.signature_role))
    return {
        "signed": True,
        "already_signed": False,
        "signature": signature.name,
        "mapping_key": mapping.mapping_key,
        "signature_role": mapping.signature_role,
    }


def _get_mapping(doctype, mapping_key):
    configs = frappe.get_all("Employee Signature Configuration", filters={"document_type": doctype, "enabled": 1}, pluck="name")
    for name in configs:
        config = frappe.get_doc("Employee Signature Configuration", name)
        for row in config.signature_mappings or []:
            if row.enabled and row.mapping_key == mapping_key:
                return config, row
    frappe.throw(_("No active signature configuration was found for this Mapping Key."))


def _mapping_fields(row):
    fields = {
        "signature": row.employee_signature_field,
        "employee_name": row.employee_name_field,
        "designation": row.designation_field,
        "date": row.signature_date_field,
        "image": row.signature_image_field,
    }
    if not all(fields.values()):
        frappe.throw(_("The signature field mapping is incomplete. Save the Signature Configuration again."))
    return fields


def _validate_target_fields(target, fields):
    for label, fieldname in fields.items():
        if not target.meta.has_field(fieldname):
            frappe.throw(_("Configured {0} field does not exist: {1}").format(label, fieldname))


def _get_signature(user):
    name = frappe.db.get_value("Employee Signature", {"user_id": user, "disabled": 0, "is_default": 1}, "name")
    if not name:
        name = frappe.db.get_value("Employee Signature", {"user_id": user, "disabled": 0}, "name")
    if not name:
        frappe.throw(_("No active Employee Signature is configured for the current user."))
    return frappe.get_doc("Employee Signature", name)
 
