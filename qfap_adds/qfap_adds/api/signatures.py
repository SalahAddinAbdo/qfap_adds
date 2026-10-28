from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today


@frappe.whitelist()
def get_signature_dialog_context(doctype, document_name, mapping_key):
    if not frappe.has_permission(doctype, "read", document_name):
        frappe.throw(
            _("You do not have permission to read this document."),
            frappe.PermissionError,
        )

    target = frappe.get_doc(doctype, document_name)
    _config, mapping = _get_mapping(doctype, mapping_key)
    include_notes = bool(mapping.get("include_signature_notes"))
    notes_field = mapping.get("signature_notes_field") or ""

    if include_notes and notes_field and not target.meta.has_field(notes_field):
        frappe.throw(
            _("Configured Signature Notes field does not exist: {0}").format(
                notes_field
            )
        )

    return {
        "include_signature_notes": include_notes,
        "signature_notes": target.get(notes_field) or ""
        if include_notes and notes_field
        else "",
    }


@frappe.whitelist()
def apply_current_employee_signature(
    doctype,
    document_name,
    mapping_key,
    signature_notes=None,
):
    """Apply and save a signature outside an atomic workflow handoff."""
    if not frappe.has_permission(doctype, "write", document_name):
        frappe.throw(
            _("You do not have permission to sign this document."),
            frappe.PermissionError,
        )

    target = frappe.get_doc(doctype, document_name)
    _validate_responsible_user(target, frappe.session.user)
    result = apply_signature_values(
        target,
        mapping_key=mapping_key,
        signature_notes=signature_notes,
        user=frappe.session.user,
    )

    if result.get("changed"):
        target.flags.ignore_validate_update_after_submit = True
        target.save(ignore_permissions=False)

    if result.get("comment"):
        target.add_comment("Info", result["comment"])

    return {key: value for key, value in result.items() if key != "comment"}


def apply_signature_values(
    target,
    mapping_key,
    signature_notes=None,
    user=None,
):
    """Set signature values on an in-memory document without saving it."""
    user = user or frappe.session.user
    _config, mapping = _get_mapping(target.doctype, mapping_key)
    _validate_signature_role(mapping, user)

    signature = _get_signature(user)
    fields = _mapping_fields(mapping)
    _validate_target_fields(target, fields)

    notes_enabled = bool(mapping.get("include_signature_notes"))
    notes_value = str(signature_notes or "").strip()
    existing = target.get(fields["signature"])

    if existing and not mapping.allow_signature_replacement:
        notes_updated = False
        if notes_enabled and fields.get("notes"):
            old_notes = str(target.get(fields["notes"]) or "")
            if old_notes != notes_value:
                target.set(fields["notes"], notes_value)
                notes_updated = True
        if notes_updated:
            target.flags.ignore_validate_update_after_submit = True
        return {
            "signed": True,
            "already_signed": True,
            "changed": notes_updated,
            "signature_notes_updated": notes_updated,
            "signature_notes": notes_value if notes_enabled else "",
        }

    target.set(fields["signature"], signature.name)
    target.set(fields["employee_name"], signature.full_name)
    target.set(fields["designation"], signature.designation)
    target.set(fields["date"], today())
    if notes_enabled and fields.get("notes"):
        target.set(fields["notes"], notes_value)
    target.set(fields["image"], signature.signature1)
    target.flags.ignore_validate_update_after_submit = True

    signature_role = mapping.signature_role or ""
    return {
        "signed": True,
        "already_signed": False,
        "changed": True,
        "signature": signature.name,
        "mapping_key": mapping.mapping_key,
        "signature_role": signature_role,
        "signature_notes": notes_value if notes_enabled else "",
        "comment": _("Signed electronically by {0} as {1}").format(
            signature.full_name,
            signature_role,
        ),
    }


def _validate_responsible_user(target, user):
    if not target.meta.has_field("custom_current_responsible_user"):
        return
    responsible = str(target.get("custom_current_responsible_user") or "").strip()
    roles = set(frappe.get_roles(user))
    can_override = user == "Administrator" or bool(
        {"Workflow Admin", "System Manager"}.intersection(roles)
    )
    if responsible and responsible != user and not can_override:
        frappe.throw(
            _("Only the current responsible user can sign this document."),
            frappe.PermissionError,
        )


def _validate_signature_role(mapping, user):
    required_role = str(mapping.signature_role or "").strip()
    if not required_role:
        frappe.throw(_("The signature mapping does not define a Signature Role."))

    roles = set(frappe.get_roles(user))
    can_override = user == "Administrator" or bool(
        {"Workflow Admin", "System Manager"}.intersection(roles)
    )
    if required_role not in roles and not can_override:
        frappe.throw(
            _("The current user does not have the required signature role: {0}").format(
                required_role
            ),
            frappe.PermissionError,
        )


def _get_mapping(doctype, mapping_key):
    configs = frappe.get_all(
        "Employee Signature Configuration",
        filters={"document_type": doctype, "enabled": 1},
        pluck="name",
    )
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
        "notes": row.signature_notes_field
        if row.get("include_signature_notes")
        else "",
        "image": row.signature_image_field,
    }
    required = [
        fields["signature"],
        fields["employee_name"],
        fields["designation"],
        fields["date"],
        fields["image"],
    ]
    if not all(required):
        frappe.throw(
            _(
                "The signature field mapping is incomplete. "
                "Save the Signature Configuration again."
            )
        )
    if row.get("include_signature_notes") and not fields["notes"]:
        frappe.throw(_("Signature Notes is enabled, but its mapped field is missing."))
    return fields


def _validate_target_fields(target, fields):
    for label, fieldname in fields.items():
        if not fieldname:
            continue
        if not target.meta.has_field(fieldname):
            frappe.throw(
                _("Configured {0} field does not exist: {1}").format(
                    label,
                    fieldname,
                )
            )


def _get_signature(user):
    name = frappe.db.get_value(
        "Employee Signature",
        {"user_id": user, "disabled": 0, "is_default": 1},
        "name",
    )
    if not name:
        name = frappe.db.get_value(
            "Employee Signature",
            {"user_id": user, "disabled": 0},
            "name",
        )
    if not name:
        frappe.throw(_("No active Employee Signature is configured for the current user."))
    return frappe.get_doc("Employee Signature", name)
