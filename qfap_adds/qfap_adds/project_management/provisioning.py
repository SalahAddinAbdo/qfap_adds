from __future__ import annotations

import frappe
from frappe import _

from qfap_adds.project_management.custom_fields import (
    PROJECT_MANAGEMENT_CUSTOM_FIELDS,
    PROJECT_MANAGEMENT_DEFAULTS,
)

OWNER_MODULE = "Project Management"
MANAGED_PROPERTIES = (
    "label", "fieldtype", "options", "insert_after", "reqd", "read_only",
    "hidden", "depends_on", "mandatory_depends_on", "read_only_depends_on",
    "default", "no_copy", "unique", "description", "in_list_view",
    "in_standard_filter",
)


def _field_has_values(doctype, fieldname):
    meta = frappe.get_meta(doctype)
    if meta.issingle:
        value = frappe.db.get_single_value(doctype, fieldname)
        return value not in (None, "", 0, "0")
    table = frappe.qb.DocType(doctype)
    return bool(
        frappe.qb.from_(table)
        .select(table.name)
        .where(table[fieldname].isnotnull())
        .where(table[fieldname] != "")
        .limit(1)
        .run()
    )


def _assert_compatible(custom_field, definition):
    expected_type = definition.get("fieldtype") or "Data"
    expected_options = definition.get("options") or ""
    actual_type = custom_field.fieldtype or "Data"
    actual_options = custom_field.options or ""
    incompatible = actual_type != expected_type
    if expected_type in ("Link", "Table", "Table MultiSelect"):
        incompatible = incompatible or actual_options != expected_options
    if incompatible and _field_has_values(custom_field.dt, custom_field.fieldname):
        frappe.throw(
            _("Field {0}.{1} contains data but conflicts with the application definition. Expected {2} {3}; found {4} {5}.").format(
                frappe.bold(custom_field.dt), frappe.bold(custom_field.fieldname),
                expected_type, expected_options, actual_type, actual_options,
            )
        )


def _sync_field(doctype, definition):
    fieldname = definition["fieldname"]
    name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname}, "name")
    if name:
        doc = frappe.get_doc("Custom Field", name)
        _assert_compatible(doc, definition)
    else:
        standard = next((field for field in frappe.get_meta(doctype).fields if field.fieldname == fieldname and not field.is_custom_field), None)
        if standard:
            expected_type = definition.get("fieldtype") or "Data"
            expected_options = definition.get("options") or ""
            if standard.fieldtype != expected_type or (expected_type in ("Link", "Table", "Table MultiSelect") and (standard.options or "") != expected_options):
                frappe.throw(_("Standard field {0}.{1} conflicts with the application definition.").format(frappe.bold(doctype), frappe.bold(fieldname)))
            return
        doc = frappe.new_doc("Custom Field")
        doc.dt = doctype
        doc.fieldname = fieldname

    for property_name in MANAGED_PROPERTIES:
        if property_name in definition:
            doc.set(property_name, definition.get(property_name))
    doc.is_system_generated = 1
    doc.module = OWNER_MODULE
    doc.save(ignore_permissions=True)


def _remove_obsolete_layout_fields():
    for fieldname in ("project_cycle_integration_section", "project_cycle_integration_column"):
        name = frappe.db.get_value("Custom Field", {"dt":"Projects Settings", "fieldname":fieldname}, "name")
        if name:
            frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def _initialize_settings_once():
    settings = frappe.get_single("Projects Settings")
    if int(settings.get("custom_project_cycle_defaults_initialized") or 0):
        return
    for fieldname, value in PROJECT_MANAGEMENT_DEFAULTS.items():
        settings.set(fieldname, value)
    settings.custom_project_cycle_defaults_initialized = 1
    settings.save(ignore_permissions=True)


def provision_project_management():
    _remove_obsolete_layout_fields()
    for doctype, definitions in PROJECT_MANAGEMENT_CUSTOM_FIELDS.items():
        if not frappe.db.exists("DocType", doctype):
            frappe.throw(_("Required DocType {0} is not installed.").format(frappe.bold(doctype)))
        for definition in definitions:
            _sync_field(doctype, definition)
        frappe.clear_cache(doctype=doctype)
    _initialize_settings_once()
