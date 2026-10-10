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
    seen_keys = set()
    for row in doc.signature_mappings or []:
        key = (row.mapping_key or "").strip()
        if not key:
            frappe.throw(_("Mapping Key is required in every signature mapping row."))
        if key in seen_keys:
            frappe.throw(_("Duplicate signature Mapping Key: {0}").format(key))
        seen_keys.add(key)


def _safe_key(value):
    value = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower()).strip("_")
    if not value:
        frappe.throw(_("Signature Mapping Key cannot be empty."))
    return value[:60]


def provision_signature_fields(doc):
    fields = []
    section_name = "custom_qfap_signatures_section"
    if not frappe.get_meta(doc.document_type).has_field(section_name):
        fields.append({"fieldname": section_name, "label": "Approval Signatures", "fieldtype": "Section Break", "insert_after": _last_field(doc.document_type)})
    insert_after = section_name
    for row in doc.signature_mappings or []:
        key = _safe_key(row.mapping_key)
        defaults = {
            "employee_signature_field": f"custom_{key}_employee_signature",
            "designation_field": f"custom_{key}_designation",
            "signature_date_field": f"custom_{key}_signature_date",
            "signature_image_field": f"custom_{key}_signature_image",
        }
        for attr, fieldname in defaults.items():
            if not row.get(attr):
                row.db_set(attr, fieldname, update_modified=False)
                row.set(attr, fieldname)
        specs = [
            (row.employee_signature_field, "Employee Signature", "Link", "Employee Signature"),
            (f"custom_{key}_employee_name", "Employee Name", "Data", ""),
            (row.designation_field, "Designation", "Data", ""),
            (row.signature_date_field, "Signature Date", "Datetime", ""),
            (row.signature_image_field, "Signature Image", "Attach Image", ""),
        ]
        for fieldname, label, fieldtype, options in specs:
            if not frappe.get_meta(doc.document_type).has_field(fieldname):
                fields.append({"fieldname": fieldname, "label": f"{row.signature_role_description or row.mapping_key} - {label}",
                    "fieldtype": fieldtype, "options": options, "insert_after": insert_after,
                    "read_only": 1, "allow_on_submit": 1, "no_copy": 1, "print_hide": 1})
            insert_after = fieldname
    if fields:
        create_custom_fields({doc.document_type: fields}, update=True)
        frappe.clear_cache(doctype=doc.document_type)


def _last_field(doctype):
    fields = [df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldname]
    return fields[-1] if fields else ""
