from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_current_responsible_user(doc, method=None):
    if not doc.is_active or not doc.document_type or not frappe.db.exists("DocType", doc.document_type):
        return
    fieldname = "custom_current_responsible_user"
    if frappe.get_meta(doc.document_type).has_field(fieldname):
        return
    fields = [{"fieldname": "custom_qfap_workflow_control", "label": "Workflow Control", "fieldtype": "Section Break", "insert_after": _last_field(doc.document_type)},
        {"fieldname": fieldname, "label": "Current Responsible User", "fieldtype": "Link", "options": "User",
         "insert_after": "custom_qfap_workflow_control", "read_only": 1, "print_hide": 1, "allow_on_submit": 1, "no_copy": 1}]
    create_custom_fields({doc.document_type: fields}, update=True)
    frappe.clear_cache(doctype=doc.document_type)


def _last_field(doctype):
    values=[df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldname]
    return values[-1] if values else ""
