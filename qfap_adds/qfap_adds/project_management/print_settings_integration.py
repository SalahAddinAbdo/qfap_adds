from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

FIELDS = {"Print Settings": [
    {
        "fieldname": "qorg_print_section",
        "label": "Q Org Print Configuration",
        "fieldtype": "Section Break",
        "insert_after": "print_style",
    },
    {
        "fieldname": "qorg_rules",
        "label": "Managed Print Format Rules",
        "fieldtype": "Table",
        "options": "QFAP Print Format Rule",
        "insert_after": "qorg_print_section",
        "description": "Create and manage Q Universal formats. Open a row to configure Audit Information and Attachments.",
    },
    {
        "fieldname": "qorg_actions_section",
        "label": "Apply Managed Formats",
        "fieldtype": "Section Break",
        "insert_after": "qorg_rules",
    },
    {
        "fieldname": "qorg_apply_formats",
        "label": "Apply Managed Print Formats",
        "fieldtype": "Button",
        "insert_after": "qorg_actions_section",
    },
    {
        "fieldname": "qorg_sync_section",
        "label": "Synchronization Status",
        "fieldtype": "Section Break",
        "insert_after": "qorg_apply_formats",
    },
    {
        "fieldname": "qorg_last_sync_on",
        "label": "Last Sync On",
        "fieldtype": "Datetime",
        "read_only": 1,
        "insert_after": "qorg_sync_section",
    },
    {
        "fieldname": "qorg_sync_column",
        "fieldtype": "Column Break",
        "insert_after": "qorg_last_sync_on",
    },
    {
        "fieldname": "qorg_last_sync_summary",
        "label": "Last Sync Summary",
        "fieldtype": "Small Text",
        "read_only": 1,
        "insert_after": "qorg_sync_column",
    },
    {
        "fieldname": "qorg_managed_once",
        "label": "Managed Once",
        "fieldtype": "Check",
        "hidden": 1,
        "read_only": 1,
        "default": "0",
        "insert_after": "qorg_last_sync_summary",
    },
]}

OBSOLETE_FIELDS = (
    "qorg_sync_column",
)


def provision_print_settings():
    create_custom_fields(FIELDS, update=True)
    _migrate_legacy_values()
    _configure_rule_fields()


def _migrate_legacy_values():
    if not frappe.db.exists("DocType", "QFAP Print Format Settings"):
        return
    old = frappe.get_single("QFAP Print Format Settings")
    new = frappe.get_single("Print Settings")
    if not new.get("qorg_rules") and old.get("rules"):
        for row in old.rules:
            values = _clean_child(row)
            values["print_profile"] = "Q Universal"
            new.append("qorg_rules", values)
    new.qorg_last_sync_on = old.get("last_sync_on")
    new.qorg_last_sync_summary = old.get("last_sync_summary")
    new.qorg_managed_once = old.get("managed_once")
    new.flags.ignore_validate = True
    new.save(ignore_permissions=True)


def _clean_child(row):
    return {
        key: value
        for key, value in row.as_dict().items()
        if key not in ("name", "parent", "parenttype", "parentfield", "doctype", "idx")
    }


def _configure_rule_fields():
    if not frappe.db.exists("DocType", "QFAP Print Format Rule"):
        return
    properties = {
        "print_profile": {
            "options": "Q Universal",
            "default": "Q Universal",
            "read_only": "1",
            "in_list_view": "1",
            "columns": "2",
        },
        "document_type": {"in_list_view": "1", "columns": "3"},
        "enabled": {"in_list_view": "1", "columns": "1"},
        "set_as_default": {"label": "Default", "in_list_view": "1", "columns": "1"},
        "include_letter_head": {"label": "Letter Head", "in_list_view": "1", "columns": "1"},
        "include_workflow_status": {"label": "Workflow", "in_list_view": "1", "columns": "1"},
        "include_signatures": {"label": "Signatures", "in_list_view": "1", "columns": "1"},
        "include_audit_information": {"label": "Audit Information", "in_list_view": "0"},
        "include_attachments": {"label": "Attachments", "in_list_view": "0"},
    }
    for fieldname, field_properties in properties.items():
        for property_name, value in field_properties.items():
            _set_property("QFAP Print Format Rule", fieldname, property_name, value)
    frappe.clear_cache(doctype="QFAP Print Format Rule")
    frappe.clear_cache(doctype="Print Settings")


def _set_property(doctype, fieldname, property_name, value):
    name = doctype + "-" + fieldname + "-" + property_name
    property_type = "Int" if property_name in ("read_only", "in_list_view", "columns") else "Text"
    values = {
        "doctype_or_field": "DocField",
        "doc_type": doctype,
        "field_name": fieldname,
        "property": property_name,
        "property_type": property_type,
        "value": str(value),
    }
    if frappe.db.exists("Property Setter", name):
        doc = frappe.get_doc("Property Setter", name)
        for key, item in values.items():
            doc.set(key, item)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Property Setter", "name": name, **values}).insert(ignore_permissions=True)


def validate_print_settings(doc, method=None):
    seen = set()
    for row in doc.get("qorg_rules") or []:
        if not row.get("document_type"):
            frappe.throw(_("Document Type is required in row {0}.").format(row.idx))
        if row.document_type in seen:
            frappe.throw(_("Document Type {0} is duplicated.").format(row.document_type))
        seen.add(row.document_type)
        row.print_profile = "Q Universal"


@frappe.whitelist()
def apply_print_formats():
    from qfap_adds.printing.provisioning import apply_print_format_settings
    return apply_print_format_settings()
