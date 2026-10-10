from __future__ import annotations
import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
RESPONSIBLE_FIELD="custom_current_responsible_user"
DISPLAY_FIELD="custom_current_responsible_user_field"

def validate_workflow_configuration(doc, method=None):
    if doc.meta.has_field(DISPLAY_FIELD): doc.set(DISPLAY_FIELD, RESPONSIBLE_FIELD)
    if not doc.document_type: return
    keys=_mapping_keys(doc.document_type)
    for row in doc.transitions or []:
        if row.custom_assignment_required:
            row.custom_target_user_field = RESPONSIBLE_FIELD
            if not row.custom_target_role:
                frappe.throw(_("Target Role is required in transition row {0} when Assignment Required is enabled.").format(row.idx))
            if not row.custom_workflow_prompt:
                frappe.throw(_("Workflow Prompt is required in transition row {0} when Assignment Required is enabled.").format(row.idx))
        if row.custom_apply_employee_signature:
            if not row.custom_employee_signature_mapping_key:
                frappe.throw(_("Employee Signature Mapping is required in transition row {0}.").format(row.idx))
            if row.custom_employee_signature_mapping_key not in keys:
                frappe.throw(_("Signature Mapping in transition row {0} is not enabled for {1}.").format(row.idx,doc.document_type))

def ensure_current_responsible_user(doc, method=None):
    if not doc.is_active or not doc.document_type: return
    if doc.meta.has_field(DISPLAY_FIELD): frappe.db.set_value("Workflow",doc.name,DISPLAY_FIELD,RESPONSIBLE_FIELD,update_modified=False)
    meta=frappe.get_meta(doc.document_type)
    if not meta.has_field(RESPONSIBLE_FIELD):
        create_custom_fields({doc.document_type:[{"fieldname":RESPONSIBLE_FIELD,"label":"Current Responsible User","fieldtype":"Link","options":"User","insert_after":doc.workflow_state_field,"read_only":1,"print_hide":1,"allow_on_submit":1,"no_copy":1,"in_standard_filter":1}]},update=True)
    name=frappe.db.get_value("Custom Field",{"dt":doc.document_type,"fieldname":RESPONSIBLE_FIELD},"name")
    if name:
        field=frappe.get_doc("Custom Field",name); field.update({"hidden":0,"read_only":1,"options":"User","allow_on_submit":1,"no_copy":1,"in_standard_filter":1}); field.save(ignore_permissions=True)
    frappe.clear_cache(doctype=doc.document_type)

def _mapping_keys(doctype):
    result=set()
    for name in frappe.get_all("Employee Signature Configuration",filters={"document_type":doctype,"enabled":1},pluck="name"):
        for row in frappe.get_doc("Employee Signature Configuration",name).signature_mappings or []:
            if row.enabled and row.mapping_key: result.add(row.mapping_key)
    return result
