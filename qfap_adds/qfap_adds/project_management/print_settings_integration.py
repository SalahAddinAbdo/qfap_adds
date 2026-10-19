from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# Print Settings is a standard Frappe Single DocType. Q Org adds only owned
# Custom Fields and never edits the standard DocType JSON.
CUSTOM_FIELDS = {
    "Print Settings": [
        {
            "fieldname": "qorg_managed_formats_section",
            "label": "Q Org Print Configuration",
            "fieldtype": "Section Break",
            "insert_after": "print_style",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_rules",
            "label": "Managed Print Format Rules",
            "fieldtype": "Table",
            "options": "QFAP Print Format Rule",
            "insert_after": "qorg_managed_formats_section",
            "description": "Create and manage Q Universal formats. Open a row to configure Audit Information and Attachments.",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_management_section",
            "label": "Managed Format Actions and Status",
            "fieldtype": "Section Break",
            "insert_after": "qorg_rules",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_apply_formats",
            "label": "Apply Managed Print Formats",
            "fieldtype": "Button",
            "insert_after": "qorg_management_section",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_status_column",
            "fieldtype": "Column Break",
            "insert_after": "qorg_apply_formats",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_last_sync_on",
            "label": "Last Sync On",
            "fieldtype": "Datetime",
            "read_only": 1,
            "insert_after": "qorg_status_column",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_last_sync_summary",
            "label": "Last Sync Summary",
            "fieldtype": "Small Text",
            "read_only": 1,
            "insert_after": "qorg_last_sync_on",
            "is_system_generated": 1,
        },
        {
            "fieldname": "qorg_managed_once",
            "label": "Managed Once",
            "fieldtype": "Check",
            "hidden": 1,
            "read_only": 1,
            "default": "0",
            "insert_after": "qorg_last_sync_summary",
            "is_system_generated": 1,
        },
    ]
}

FIELD_CHAIN = (
    ("qorg_managed_formats_section", "print_style"),
    ("qorg_rules", "qorg_managed_formats_section"),
    ("qorg_management_section", "qorg_rules"),
    ("qorg_apply_formats", "qorg_management_section"),
    ("qorg_status_column", "qorg_apply_formats"),
    ("qorg_last_sync_on", "qorg_status_column"),
    ("qorg_last_sync_summary", "qorg_last_sync_on"),
    ("qorg_managed_once", "qorg_last_sync_summary"),
)

OBSOLETE_LAYOUT_FIELDS = (
    "qorg_print_section",
    "qorg_actions_section",
    "qorg_sync_section",
    "qorg_sync_column",
)


def provision_print_settings():
    """Provision Q Org fields on the standard Print Settings DocType safely."""
    _remove_obsolete_layout_fields()
    create_custom_fields(CUSTOM_FIELDS, update=True)
    _force_owned_field_definitions()
    _configure_rule_fields()
    frappe.clear_cache(doctype="Print Settings")
    frappe.clear_cache(doctype="QFAP Print Format Rule")


def _remove_obsolete_layout_fields():
    for fieldname in OBSOLETE_LAYOUT_FIELDS:
        name = "Print Settings-" + fieldname
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc(
                "Custom Field", name, ignore_permissions=True, force=True
            )


def _force_owned_field_definitions():
    """Correct existing site metadata left by earlier layout versions."""
    by_name = {
        row["fieldname"]: row
        for row in CUSTOM_FIELDS["Print Settings"]
    }
    for fieldname, insert_after in FIELD_CHAIN:
        name = "Print Settings-" + fieldname
        definition = by_name[fieldname]
        if not frappe.db.exists("Custom Field", name):
            continue
        values = {
            "label": definition.get("label") or "",
            "fieldtype": definition["fieldtype"],
            "insert_after": insert_after,
            "options": definition.get("options") or "",
            "description": definition.get("description") or "",
            "read_only": int(definition.get("read_only") or 0),
            "hidden": int(definition.get("hidden") or 0),
            "default": definition.get("default") or "",
            "is_system_generated": 1,
            "module": "QFap Adds",
        }
        frappe.db.set_value(
            "Custom Field", name, values, update_modified=False
        )


def _configure_rule_fields():
    if not frappe.db.exists("DocType", "QFAP Print Format Rule"):
        frappe.throw(_("QFAP Print Format Rule is not installed."))

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
        "set_as_default": {
            "label": "Default", "in_list_view": "1", "columns": "1"
        },
        "include_letter_head": {
            "label": "Letter Head", "in_list_view": "1", "columns": "1"
        },
        "include_workflow_status": {
            "label": "Workflow", "in_list_view": "1", "columns": "1"
        },
        "include_signatures": {
            "label": "Signatures", "in_list_view": "1", "columns": "1"
        },
        "include_audit_information": {
            "label": "Audit Information", "in_list_view": "0"
        },
        "include_attachments": {
            "label": "Attachments", "in_list_view": "0"
        },
    }
    for fieldname, field_properties in properties.items():
        for property_name, value in field_properties.items():
            _set_property(
                "QFAP Print Format Rule", fieldname, property_name, value
            )


def _set_property(doctype, fieldname, property_name, value):
    name = doctype + "-" + fieldname + "-" + property_name
    property_type = (
        "Int"
        if property_name in ("read_only", "in_list_view", "columns")
        else "Text"
    )
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
        frappe.get_doc(
            {"doctype": "Property Setter", "name": name, **values}
        ).insert(ignore_permissions=True)


def validate_print_settings(doc, method=None):
    seen = set()
    for row in doc.get("qorg_rules") or []:
        if not row.get("document_type"):
            frappe.throw(
                _("Document Type is required in row {0}.").format(row.idx)
            )
        if row.document_type in seen:
            frappe.throw(
                _("Document Type {0} is duplicated.").format(
                    row.document_type
                )
            )
        seen.add(row.document_type)
        row.print_profile = "Q Universal"


@frappe.whitelist()
def apply_print_formats():
    from qfap_adds.printing.provisioning import apply_print_format_settings

    return apply_print_format_settings()
