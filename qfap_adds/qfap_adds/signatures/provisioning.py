from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def validate_configuration(doc):
    if not doc.document_type:
        frappe.throw(_("Document Type is required."))
    if not frappe.db.exists("DocType", doc.document_type):
        frappe.throw(_("Target Document Type does not exist."))
    if doc.enabled and not doc.signature_mappings:
        frappe.throw(_("At least one Signature Mapping is required when the configuration is enabled."))

    seen_roles = set()
    seen_keys = set()
    for row in doc.signature_mappings or []:
        if not row.signature_role:
            frappe.throw(_("Signature Role is required in row {0}.").format(row.idx))
        key = _role_key(row.signature_role)
        row.mapping_key = key
        if row.signature_role in seen_roles:
            frappe.throw(_("Signature Role is repeated: {0}").format(row.signature_role))
        if key in seen_keys:
            frappe.throw(_("Duplicate signature Mapping Key: {0}").format(key))
        seen_roles.add(row.signature_role)
        seen_keys.add(key)

        if not row.auto_create_fields:
            required = {
                "Employee Signature Field": row.employee_signature_field,
                "Employee Name Field": row.employee_name_field,
                "Designation Field": row.designation_field,
                "Signature Date Field": row.signature_date_field,
                "Signature Image Field": row.signature_image_field,
            }
            missing = [label for label, value in required.items() if not value]
            if missing:
                frappe.throw(_("Missing manual field mapping in row {0}: {1}").format(row.idx, ", ".join(missing)))
            _validate_manual_fields(doc.document_type, row)


def provision_signature_fields(doc):
    for row in doc.signature_mappings or []:
        row.mapping_key = _role_key(row.signature_role)
        if row.auto_create_fields:
            _provision_row(doc.document_type, row)
        else:
            _apply_visibility(doc.document_type, row, bool(row.hide_generated_fields))
    frappe.clear_cache(doctype=doc.document_type)


def _provision_row(doctype, row):
    key = _role_key(row.signature_role)
    prefix = "custom_" + key
    names = {
        "section": prefix + "_signature_section",
        "signature": prefix + "_employee_signature",
        "employee_name": prefix + "_employee_name",
        "column_1": prefix + "_column_1",
        "designation": prefix + "_designation",
        "date": prefix + "_signature_date",
        "column_2": prefix + "_column_2",
        "image": prefix + "_signature_image",
    }
    label = row.signature_role_description or row.signature_role
    hidden = 1 if row.hide_generated_fields else 0
    meta = frappe.get_meta(doctype)
    insert_after = _last_field(doctype)
    specs = [
        {"fieldname": names["section"], "label": label, "fieldtype": "Section Break", "insert_after": insert_after,
         "collapsible": 1, "hidden": hidden},
        {"fieldname": names["signature"], "label": "Employee Signature", "fieldtype": "Link", "options": "Employee Signature",
         "insert_after": names["section"], "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "print_hide": 1, "hidden": hidden},
        {"fieldname": names["employee_name"], "label": "Employee Name", "fieldtype": "Data",
         "insert_after": names["signature"], "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "hidden": hidden},
        {"fieldname": names["column_1"], "fieldtype": "Column Break", "insert_after": names["employee_name"], "hidden": hidden},
        {"fieldname": names["designation"], "label": "Designation", "fieldtype": "Link", "options": "Designation",
         "insert_after": names["column_1"], "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "hidden": hidden},
        {"fieldname": names["date"], "label": "Signature Date", "fieldtype": "Date",
         "insert_after": names["designation"], "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "hidden": hidden},
        {"fieldname": names["column_2"], "fieldtype": "Column Break", "insert_after": names["date"], "hidden": hidden},
        {"fieldname": names["image"], "label": "Signature Image", "fieldtype": "Attach Image",
         "insert_after": names["column_2"], "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "hidden": hidden},
    ]
    missing = [field for field in specs if not meta.has_field(field["fieldname"])]
    if missing:
        create_custom_fields({doctype: missing}, update=True)
        frappe.clear_cache(doctype=doctype)
    _sync_generated_fields(doctype, specs)

    row.employee_signature_field = names["signature"]
    row.employee_name_field = names["employee_name"]
    row.designation_field = names["designation"]
    row.signature_date_field = names["date"]
    row.signature_image_field = names["image"]
    _save_row_mapping(row)
    _apply_visibility(doctype, row, bool(row.hide_generated_fields), names)


def _save_row_mapping(row):
    values = {
        "mapping_key": row.mapping_key,
        "employee_signature_field": row.employee_signature_field,
        "employee_name_field": row.employee_name_field,
        "designation_field": row.designation_field,
        "signature_date_field": row.signature_date_field,
        "signature_image_field": row.signature_image_field,
    }
    frappe.db.set_value(row.doctype, row.name, values, update_modified=False)


def _apply_visibility(doctype, row, hidden, names=None):
    fieldnames = []
    if names:
        fieldnames = list(names.values())
    else:
        fieldnames = [
            row.employee_signature_field,
            row.employee_name_field,
            row.designation_field,
            row.signature_date_field,
            row.signature_image_field,
        ]
    for fieldname in [name for name in fieldnames if name]:
        custom_field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")
        if custom_field:
            frappe.db.set_value("Custom Field", custom_field, "hidden", 1 if hidden else 0, update_modified=False)


def _validate_manual_fields(doctype, row):
    meta = frappe.get_meta(doctype)
    expected = {
        row.employee_signature_field: ("Link", "Employee Signature"),
        row.employee_name_field: ("Data", None),
        row.designation_field: (("Data", "Link"), None),
        row.signature_date_field: (("Date", "Datetime"), None),
        row.signature_image_field: (("Attach", "Attach Image"), None),
    }
    for fieldname, (fieldtypes, options) in expected.items():
        df = meta.get_field(fieldname)
        if not df:
            frappe.throw(_("Field {0} does not exist in {1}.").format(fieldname, doctype))
        allowed = fieldtypes if isinstance(fieldtypes, tuple) else (fieldtypes,)
        if df.fieldtype not in allowed:
            frappe.throw(_("Field {0} has an incompatible field type.").format(fieldname))
        if options and df.options != options:
            frappe.throw(_("Field {0} must link to {1}.").format(fieldname, options))


def _role_key(role):
    key = re.sub(r"[^a-z0-9_]+", "_", (role or "").strip().lower()).strip("_")
    if not key:
        frappe.throw(_("Signature Role cannot generate a valid Mapping Key."))
    return key[:48]


def _last_field(doctype):
    fields = [df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldname]
    return fields[-1] if fields else ""
